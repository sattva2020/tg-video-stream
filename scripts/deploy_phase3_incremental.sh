#!/bin/bash

# ============================================================================
# РАЗВЕРТЫВАНИЕ PHASE 3 - ПОШАГОВОЕ РАЗВОРАЧИВАНИЕ
# ============================================================================
# Этот скрипт развертывает код постепенно, копируя только критические файлы

set -e

VPS_HOST="37.53.91.144"
VPS_USER="root"
SSH_KEY="~/.ssh/id_rsa_n8n"
VPS_PATH="/root/telegram"

echo "🚀 НАЧИНАЕМ ПОШАГОВОЕ РАЗВЕРТЫВАНИЕ PHASE 3"
echo ""

# ============================================================================
# ШАГ 1: Отправка критических конфиг-файлов
# ============================================================================
echo "📦 [1/4] Отправка конфиг-файлов..."

CRITICAL_FILES=(
    "docker-compose.yml"
    "pyproject.toml"
    "package.json"
    ".gitignore"
    "README.md"
    "setup.sh"
    "start.sh"
    "requirements.txt"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        scp -i "$SSH_KEY" "$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/" 2>/dev/null || echo "Skipped: $file"
    fi
done

echo "✅ Конфиг-файлы отправлены"

# ============================================================================
# ШАГ 2: Отправка backend (по частям)
# ============================================================================
echo "📦 [2/4] Отправка backend кода..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/backend/src $VPS_PATH/backend/alembic/versions $VPS_PATH/backend/tests" >/dev/null 2>&1

# Копируем важные файлы backend
scp -i "$SSH_KEY" backend/run.py "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/" 2>/dev/null || true
scp -i "$SSH_KEY" backend/alembic.ini "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/" 2>/dev/null || true
scp -i "$SSH_KEY" backend/requirements.txt "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/" 2>/dev/null || true
scp -i "$SSH_KEY" backend/requirements-dev.txt "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/" 2>/dev/null || true

# Копируем исходный код (src/)
scp -i "$SSH_KEY" -r backend/src/models "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/src/services "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/src/schemas "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/src/api "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/src/database "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" backend/src/__init__.py "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/src/" 2>/dev/null || true

# Копируем миграции Alembic (включая Phase 3)
scp -i "$SSH_KEY" backend/alembic/versions/* "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/alembic/versions/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/alembic/env.py "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/alembic/" 2>/dev/null || true
scp -i "$SSH_KEY" -r backend/alembic/script.py.mako "$VPS_USER@$VPS_HOST:$VPS_PATH/backend/alembic/" 2>/dev/null || true

echo "✅ Backend отправлен"

# ============================================================================
# ШАГ 3: Отправка frontend (по частям)
# ============================================================================
echo "📦 [3/4] Отправка frontend кода..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/frontend/src $VPS_PATH/frontend/public" >/dev/null 2>&1

# Копируем конфиги
scp -i "$SSH_KEY" frontend/package.json "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/tsconfig.json "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/vite.config.ts "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/tailwind.config.js "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/index.html "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/nginx.conf "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/" 2>/dev/null || true

# Копируем исходный код (очень выборочно - только главное)
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/frontend/src/pages/admin $VPS_PATH/frontend/src/components/dashboard" >/dev/null 2>&1

scp -i "$SSH_KEY" frontend/src/main.tsx "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" frontend/src/App.tsx "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/src/" 2>/dev/null || true
scp -i "$SSH_KEY" -r frontend/src/pages/admin "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/src/pages/" 2>/dev/null || true
scp -i "$SSH_KEY" -r frontend/src/components/dashboard "$VPS_USER@$VPS_HOST:$VPS_PATH/frontend/src/components/" 2>/dev/null || true

echo "✅ Frontend отправлен"

# ============================================================================
# ШАГ 4: Запуск миграций и контейнеров
# ============================================================================
echo "📦 [4/4] Запуск миграций и контейнеров..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /root/telegram || exit 1
    
    echo "Выполнение миграций..."
    if [ -f "backend/alembic.ini" ]; then
        cd backend
        alembic upgrade head 2>&1 | tail -5
        cd ..
    fi
    
    echo "Запуск Docker контейнеров..."
    if [ -f "docker-compose.yml" ]; then
        docker compose down 2>/dev/null || true
        docker compose up -d 2>&1 | tail -10
        sleep 5
        docker compose ps
    fi
EOF

echo "✅ Миграции и контейнеры запущены"

# ============================================================================
# ФИНАЛ
# ============================================================================
echo ""
echo "🎉 ПОШАГОВОЕ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo ""
echo "✅ Проверьте:"
echo "  - http://37.53.91.144/admin/metrics"
echo "  - Консоль (F12) на предмет ошибок"
echo "  - Вкладки: Quality, Trends, Alerts"
echo ""
