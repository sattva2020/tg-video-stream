#!/bin/bash
# Скрипт для запуска тестов на VPS
# Используется для integration tests с реальной PostgreSQL БД

set -e

echo "🧪 Запуск тестов на VPS..."

# Переход в директорию проекта
cd /root || exit 1

# Проверка наличия docker-compose
if ! docker compose version &>/dev/null; then
    echo "❌ docker compose не найден"
    exit 1
fi

# Запуск тестов в backend контейнере
echo "📦 Запуск тестов в backend контейнере..."

docker compose exec -T backend bash << 'EOF'
# Загрузить .env.test
if [ -f ".env.test" ]; then
    export $(grep -v '^#' .env.test | xargs)
else
    echo "⚠️  .env.test не найден, используется default env"
fi

# Запуск pytest
cd /app
python -m pytest tests/test_audio/test_endpoints.py -v --tb=short -x

echo "✅ Тесты завершены"
EOF

echo "✅ Все тесты прошли успешно!"
