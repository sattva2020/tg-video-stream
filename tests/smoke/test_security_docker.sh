#!/usr/bin/env bash
# Smoke test: Проверка безопасности Docker конфигурации (US-1)
# Проверяет: отсутствие Docker socket mount, сетевая изоляция, credentials

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
EXIT_CODE=0

echo "=== Security Docker Smoke Test ==="
echo "Compose file: $COMPOSE_FILE"
echo ""

# Проверка 1: Docker socket mount
echo "[1/4] Проверка Docker socket mount..."
if grep -q "docker.sock" "$COMPOSE_FILE"; then
    echo "  ❌ FAIL: Найден монтирование Docker socket в $COMPOSE_FILE"
    echo "  Строки с docker.sock:"
    grep -n "docker.sock" "$COMPOSE_FILE" || true
    EXIT_CODE=1
else
    echo "  ✅ PASS: Docker socket не монтируется"
fi

# Проверка 2: Hardcoded пароли PostgreSQL
echo "[2/4] Проверка hardcoded credentials PostgreSQL..."
if grep -E "POSTGRES_PASSWORD\s*[:=]\s*postgres(\s|$|\")" "$COMPOSE_FILE" >/dev/null 2>&1; then
    echo "  ❌ FAIL: Найден hardcoded пароль 'postgres' в $COMPOSE_FILE"
    grep -n "POSTGRES_PASSWORD" "$COMPOSE_FILE" || true
    EXIT_CODE=1
else
    echo "  ✅ PASS: PostgreSQL использует переменные окружения для пароля"
fi

# Проверка 3: Network isolation
echo "[3/4] Проверка сетевой изоляции..."
if grep -q "networks:" "$COMPOSE_FILE"; then
    if grep -q "internal:\s*true" "$COMPOSE_FILE"; then
        echo "  ✅ PASS: Найдена internal network"
    else
        echo "  ⚠️ WARN: networks определены, но internal network не найдена"
    fi
else
    echo "  ❌ FAIL: Сетевая изоляция не настроена (нет секции networks)"
    EXIT_CODE=1
fi

# Проверка 4: Trivy scan (если доступен)
echo "[4/4] Проверка Trivy security scan..."
if command -v trivy &>/dev/null; then
    echo "  Запуск trivy config..."
    if trivy config "$COMPOSE_FILE" --severity HIGH,CRITICAL --exit-code 1 2>/dev/null; then
        echo "  ✅ PASS: Trivy не нашёл HIGH/CRITICAL уязвимостей"
    else
        echo "  ❌ FAIL: Trivy нашёл уязвимости"
        EXIT_CODE=1
    fi
else
    echo "  ⚠️ SKIP: Trivy не установлен (установите: brew install trivy)"
fi

echo ""
echo "=== Результат ==="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Все проверки пройдены"
else
    echo "❌ Некоторые проверки не пройдены (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
