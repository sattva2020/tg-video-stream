#!/bin/bash
# Скрипт запуска для production на flowbooster.xyz
# Запуск: ./scripts/start-prod.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Запуск production серверов для flowbooster.xyz"
echo "=================================================="

# Активируем виртуальное окружение
source "$PROJECT_DIR/venv/Scripts/activate" 2>/dev/null || source "$PROJECT_DIR/venv/bin/activate"

# Убиваем старые процессы
echo "🔄 Останавливаем старые процессы..."
taskkill //F //IM python.exe 2>/dev/null || true
taskkill //F //IM node.exe 2>/dev/null || true
sleep 2

# Запускаем Backend на 0.0.0.0:8000 (доступен извне)
echo "🔧 Запуск Backend API на порту 8000..."
cd "$PROJECT_DIR/backend"
python -c "
import uvicorn
import sys
sys.path.insert(0, 'src')
from main import app
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
" &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

# Запускаем Frontend на 0.0.0.0:80
echo "🌐 Запуск Frontend на порту 80..."
cd "$PROJECT_DIR/frontend"
npm run dev -- --port 80 --host 0.0.0.0 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Серверы запущены!"
echo "=================================================="
echo "Frontend: http://flowbooster.xyz"
echo "Backend:  http://flowbooster.xyz:8000"
echo "API Docs: http://flowbooster.xyz:8000/docs"
echo ""
echo "Для остановки: taskkill //F //IM python.exe && taskkill //F //IM node.exe"
echo ""

# Ждём завершения
wait
