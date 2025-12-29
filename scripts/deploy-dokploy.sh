#!/usr/bin/env bash
# =============================================================================
# Деплой приложения через Dokploy API
#
# Этот скрипт позволяет триггерить деплой через API без использования UI.
# Полезно для CI/CD интеграции.
#
# Usage:
#   ./scripts/deploy-dokploy.sh                    # Деплой по умолчанию
#   ./scripts/deploy-dokploy.sh --project=NAME     # Деплой конкретного проекта
#   ./scripts/deploy-dokploy.sh --list             # Список проектов
#
# Environment:
#   DOKPLOY_URL       - URL Dokploy (default: http://37.53.91.144:3000)
#   DOKPLOY_API_TOKEN - API токен (обязательно)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Конфигурация
DOKPLOY_URL="${DOKPLOY_URL:-http://37.53.91.144:3000}"
DOKPLOY_API_TOKEN="${DOKPLOY_API_TOKEN:-}"
PROJECT_NAME="${PROJECT_NAME:-sattva-streamer}"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[dokploy-api]${NC} $*"; }
log_ok() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_err() { echo -e "${RED}✗${NC} $*"; }

ACTION="deploy"
TARGET_PROJECT=""

# Parse arguments
for arg in "$@"; do
  case $arg in
    --list) ACTION="list" ;;
    --status) ACTION="status" ;;
    --project=*) TARGET_PROJECT="${arg#*=}" ;;
    --help|-h)
      echo "Usage: $0 [--list] [--status] [--project=NAME]"
      echo ""
      echo "Actions:"
      echo "  (default)  Deploy the project"
      echo "  --list     List all projects and services"
      echo "  --status   Show deployment status"
      echo ""
      echo "Options:"
      echo "  --project=NAME  Target project name (default: sattva-streamer)"
      echo ""
      echo "Environment:"
      echo "  DOKPLOY_URL        Dokploy server URL"
      echo "  DOKPLOY_API_TOKEN  API token (required)"
      exit 0
      ;;
  esac
done

# Проверка API токена
if [ -z "$DOKPLOY_API_TOKEN" ]; then
  log_err "DOKPLOY_API_TOKEN не установлен"
  echo ""
  echo "Получите токен в Dokploy:"
  echo "1. Откройте $DOKPLOY_URL"
  echo "2. Profile → API Tokens → Create"
  echo "3. export DOKPLOY_API_TOKEN='your-token'"
  exit 1
fi

# Проверка подключения
check_connection() {
  log "Проверка подключения к $DOKPLOY_URL..."
  
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    "$DOKPLOY_URL/api/project.all" 2>/dev/null || echo "000")
  
  if [ "$HTTP_CODE" = "200" ]; then
    log_ok "Подключение успешно"
    return 0
  elif [ "$HTTP_CODE" = "401" ]; then
    log_err "Неверный API токен"
    return 1
  else
    log_err "Не удалось подключиться (HTTP $HTTP_CODE)"
    return 1
  fi
}

# Получить список проектов
list_projects() {
  log "Получение списка проектов..."
  
  RESPONSE=$(curl -s -X GET "$DOKPLOY_URL/api/project.all" \
    -H "accept: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN")
  
  echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print()
    print('Проекты:')
    print('=' * 60)
    for project in data:
        print(f\"  📁 {project.get('name', 'unnamed')} (id: {project.get('projectId', 'N/A')})\")
        
        # Applications
        apps = project.get('applications', [])
        for app in apps:
            print(f\"     └─ 📦 App: {app.get('name', 'unnamed')} (id: {app.get('applicationId', 'N/A')})\")
        
        # Compose
        composes = project.get('compose', [])
        for c in composes:
            print(f\"     └─ 🐳 Compose: {c.get('name', 'unnamed')} (id: {c.get('composeId', 'N/A')})\")
        
        # Databases
        for db_type in ['mariadb', 'mongo', 'mysql', 'postgres', 'redis']:
            dbs = project.get(db_type, [])
            for db in dbs:
                print(f\"     └─ 💾 {db_type}: {db.get('name', 'unnamed')}\")
        
        print()
except json.JSONDecodeError as e:
    print(f'Ошибка парсинга JSON: {e}', file=sys.stderr)
    print(f'Response: {sys.stdin.read()[:500]}', file=sys.stderr)
" 2>&1 || echo "$RESPONSE"
}

# Найти compose ID по имени проекта
find_compose_id() {
  local project_name="$1"
  
  RESPONSE=$(curl -s -X GET "$DOKPLOY_URL/api/project.all" \
    -H "accept: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN")
  
  COMPOSE_ID=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    project_name = '$project_name'.lower()
    
    for project in data:
        if project_name in project.get('name', '').lower():
            composes = project.get('compose', [])
            if composes:
                print(composes[0].get('composeId', ''))
                break
except:
    pass
" 2>/dev/null)
  
  echo "$COMPOSE_ID"
}

# Найти application ID по имени проекта
find_app_id() {
  local project_name="$1"
  
  RESPONSE=$(curl -s -X GET "$DOKPLOY_URL/api/project.all" \
    -H "accept: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN")
  
  APP_ID=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    project_name = '$project_name'.lower()
    
    for project in data:
        if project_name in project.get('name', '').lower():
            apps = project.get('applications', [])
            if apps:
                print(apps[0].get('applicationId', ''))
                break
except:
    pass
" 2>/dev/null)
  
  echo "$APP_ID"
}

# Деплой Docker Compose проекта
deploy_compose() {
  local compose_id="$1"
  
  log "Деплой Docker Compose (id: $compose_id)..."
  
  RESPONSE=$(curl -s -X POST "$DOKPLOY_URL/api/compose.deploy" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    -d "{\"composeId\": \"$compose_id\"}")
  
  if echo "$RESPONSE" | grep -q "error\|Error"; then
    log_err "Ошибка деплоя: $RESPONSE"
    return 1
  else
    log_ok "Деплой запущен!"
    echo "$RESPONSE"
  fi
}

# Деплой Application
deploy_app() {
  local app_id="$1"
  
  log "Деплой Application (id: $app_id)..."
  
  RESPONSE=$(curl -s -X POST "$DOKPLOY_URL/api/application.deploy" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    -d "{\"applicationId\": \"$app_id\"}")
  
  if echo "$RESPONSE" | grep -q "error\|Error"; then
    log_err "Ошибка деплоя: $RESPONSE"
    return 1
  else
    log_ok "Деплой запущен!"
    echo "$RESPONSE"
  fi
}

# Main
check_connection || exit 1

case "$ACTION" in
  list)
    list_projects
    ;;
  
  status)
    log "Статус проектов..."
    list_projects
    ;;
  
  deploy)
    PROJECT="${TARGET_PROJECT:-$PROJECT_NAME}"
    log "Поиск проекта: $PROJECT..."
    
    # Сначала ищем compose
    COMPOSE_ID=$(find_compose_id "$PROJECT")
    
    if [ -n "$COMPOSE_ID" ]; then
      log "Найден Docker Compose: $COMPOSE_ID"
      deploy_compose "$COMPOSE_ID"
    else
      # Ищем application
      APP_ID=$(find_app_id "$PROJECT")
      
      if [ -n "$APP_ID" ]; then
        log "Найден Application: $APP_ID"
        deploy_app "$APP_ID"
      else
        log_err "Проект '$PROJECT' не найден"
        echo ""
        echo "Доступные проекты:"
        list_projects
        exit 1
      fi
    fi
    ;;
esac

echo ""
log "Готово! Проверьте статус в Dokploy UI: $DOKPLOY_URL"
