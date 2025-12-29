#!/usr/bin/env bash
# =============================================================================
# Миграция секретов в Dokploy
#
# Этот скрипт генерирует команды для добавления переменных окружения
# из .env.master в Dokploy через API или выводит их для ручного ввода в UI.
#
# Usage:
#   ./scripts/migrate-to-dokploy.sh                 # Вывод для копирования в UI
#   ./scripts/migrate-to-dokploy.sh --api           # Миграция через API
#   ./scripts/migrate-to-dokploy.sh --dry-run       # Показать что будет сделано
#
# Environment:
#   DOKPLOY_URL         - URL Dokploy (default: http://37.53.91.144:3000)
#   DOKPLOY_API_TOKEN   - API токен (для --api режима)
#   DOKPLOY_COMPOSE_ID  - ID compose проекта
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Конфигурация
DOKPLOY_URL="${DOKPLOY_URL:-http://37.53.91.144:3000}"
DOKPLOY_API_TOKEN="${DOKPLOY_API_TOKEN:-}"
DOKPLOY_COMPOSE_ID="${DOKPLOY_COMPOSE_ID:-}"
ENV_MASTER="${PROJECT_ROOT}/.env.master"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[migrate]${NC} $*"; }
log_ok() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_err() { echo -e "${RED}✗${NC} $*"; }

MODE="ui"
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --api) MODE="api" ;;
    --dry-run) DRY_RUN=true ;;
    --help|-h)
      echo "Usage: $0 [--api] [--dry-run]"
      echo ""
      echo "Modes:"
      echo "  (default)  Generate output for copying into Dokploy UI"
      echo "  --api      Migrate variables via Dokploy API"
      echo ""
      echo "Options:"
      echo "  --dry-run  Show what would be done without making changes"
      exit 0
      ;;
  esac
done

# Проверка .env.master
if [ ! -f "$ENV_MASTER" ]; then
  log_err ".env.master не найден: $ENV_MASTER"
  echo ""
  echo "Создайте файл с секретами:"
  echo "  cp .env.example .env.master"
  echo "  # Отредактируйте значения"
  exit 1
fi

# Загрузка переменных
declare -A BACKEND_VARS
declare -A FRONTEND_VARS
declare -A COMMON_VARS

log "Чтение переменных из .env.master..."

while IFS='=' read -r key value || [ -n "$key" ]; do
  # Пропускаем комментарии и пустые строки
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  
  # Убираем кавычки
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  
  if [[ "$key" =~ ^VITE_ ]]; then
    FRONTEND_VARS["$key"]="$value"
  elif [[ "$key" =~ ^POSTGRES_|^DB_|^DATABASE ]]; then
    COMMON_VARS["$key"]="$value"
  elif [[ "$key" =~ ^REDIS_ ]]; then
    COMMON_VARS["$key"]="$value"
  else
    BACKEND_VARS["$key"]="$value"
  fi
done < "$ENV_MASTER"

# Статистика
TOTAL=$((${#BACKEND_VARS[@]} + ${#FRONTEND_VARS[@]} + ${#COMMON_VARS[@]}))
log_ok "Найдено переменных: $TOTAL"
echo "  Backend:  ${#BACKEND_VARS[@]}"
echo "  Frontend: ${#FRONTEND_VARS[@]}"
echo "  Common:   ${#COMMON_VARS[@]}"
echo ""

# Режим UI - генерация текста для копирования
if [ "$MODE" = "ui" ]; then
  echo "============================================================"
  echo -e "${CYAN}Переменные окружения для Dokploy UI${NC}"
  echo "============================================================"
  echo ""
  echo "Откройте Dokploy: $DOKPLOY_URL"
  echo "Перейдите в: Project → Compose → Environment"
  echo ""
  echo "Скопируйте следующий блок:"
  echo ""
  echo "------- НАЧАЛО БЛОКА -------"
  
  # Выводим все переменные в формате KEY=value
  {
    echo "# === BACKEND VARIABLES ==="
    for key in "${!BACKEND_VARS[@]}"; do
      echo "$key=${BACKEND_VARS[$key]}"
    done
    
    echo ""
    echo "# === FRONTEND VARIABLES ==="
    for key in "${!FRONTEND_VARS[@]}"; do
      echo "$key=${FRONTEND_VARS[$key]}"
    done
    
    echo ""
    echo "# === COMMON/DATABASE VARIABLES ==="
    for key in "${!COMMON_VARS[@]}"; do
      echo "$key=${COMMON_VARS[$key]}"
    done
  } | sort
  
  echo "------- КОНЕЦ БЛОКА -------"
  echo ""
  echo -e "${YELLOW}Важно:${NC} После вставки переменных нажмите 'Save' и 'Redeploy'"
  
  exit 0
fi

# Режим API - миграция через API
if [ "$MODE" = "api" ]; then
  if [ -z "$DOKPLOY_API_TOKEN" ]; then
    log_err "DOKPLOY_API_TOKEN не установлен"
    echo "export DOKPLOY_API_TOKEN='your-token'"
    exit 1
  fi
  
  if [ -z "$DOKPLOY_COMPOSE_ID" ]; then
    log "DOKPLOY_COMPOSE_ID не установлен, ищем автоматически..."
    
    # Используем deploy-dokploy.sh для поиска
    RESPONSE=$(curl -s -X GET "$DOKPLOY_URL/api/project.all" \
      -H "accept: application/json" \
      -H "x-api-key: $DOKPLOY_API_TOKEN")
    
    DOKPLOY_COMPOSE_ID=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for project in data:
        composes = project.get('compose', [])
        if composes:
            print(composes[0].get('composeId', ''))
            break
except:
    pass
" 2>/dev/null)
    
    if [ -z "$DOKPLOY_COMPOSE_ID" ]; then
      log_err "Не удалось найти compose проект"
      exit 1
    fi
    
    log_ok "Найден compose ID: $DOKPLOY_COMPOSE_ID"
  fi
  
  # Формируем env блок
  ENV_CONTENT=""
  
  for key in "${!BACKEND_VARS[@]}"; do
    ENV_CONTENT+="$key=${BACKEND_VARS[$key]}\n"
  done
  
  for key in "${!FRONTEND_VARS[@]}"; do
    ENV_CONTENT+="$key=${FRONTEND_VARS[$key]}\n"
  done
  
  for key in "${!COMMON_VARS[@]}"; do
    ENV_CONTENT+="$key=${COMMON_VARS[$key]}\n"
  done
  
  if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Будет отправлено:"
    echo -e "$ENV_CONTENT"
    exit 0
  fi
  
  log "Обновление переменных окружения через API..."
  
  # API endpoint для обновления environment
  # Note: Dokploy использует compose.update для изменения env
  ESCAPED_CONTENT=$(echo -e "$ENV_CONTENT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
  
  RESPONSE=$(curl -s -X POST "$DOKPLOY_URL/api/compose.update" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    -d "{\"composeId\": \"$DOKPLOY_COMPOSE_ID\", \"env\": $ESCAPED_CONTENT}")
  
  if echo "$RESPONSE" | grep -q "error\|Error"; then
    log_err "Ошибка обновления: $RESPONSE"
    exit 1
  else
    log_ok "Переменные окружения обновлены!"
    
    # Предложить редеплой
    echo ""
    read -p "Запустить деплой? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      "$SCRIPT_DIR/deploy-dokploy.sh"
    fi
  fi
fi
