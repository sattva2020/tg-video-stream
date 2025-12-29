#!/usr/bin/env bash
# =============================================================================
# Установка Dokploy на VPS
#
# Dokploy — self-hosted PaaS альтернатива Vercel/Heroku/Netlify
#
# Usage:
#   ./scripts/setup-dokploy.sh              # Установка на удалённый сервер
#   ./scripts/setup-dokploy.sh --local      # Установка локально (для теста)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Конфигурация
REMOTE_HOST="${DOKPLOY_HOST:-37.53.91.144}"
REMOTE_USER="${DOKPLOY_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa_n8n}"
DOKPLOY_PORT="${DOKPLOY_PORT:-3000}"

LOCAL_INSTALL=false

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[dokploy]${NC} $*"; }
log_ok() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_err() { echo -e "${RED}✗${NC} $*"; }

# Parse arguments
for arg in "$@"; do
  case $arg in
    --local) LOCAL_INSTALL=true ;;
    --host=*) REMOTE_HOST="${arg#*=}" ;;
    --help|-h)
      echo "Usage: $0 [--local] [--host=IP]"
      echo ""
      echo "Options:"
      echo "  --local    Install on local machine (for testing)"
      echo "  --host=IP  Remote server IP (default: 37.53.91.144)"
      exit 0
      ;;
  esac
done

install_dokploy_remote() {
  log "Установка Dokploy на $REMOTE_HOST..."
  
  # Проверка SSH
  if [ ! -f "$SSH_KEY" ]; then
    log_err "SSH ключ не найден: $SSH_KEY"
    exit 1
  fi
  
  SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $SSH_KEY"
  
  # Проверка подключения
  if ! ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "hostname" >/dev/null 2>&1; then
    log_err "Не удалось подключиться к $REMOTE_HOST"
    exit 1
  fi
  log_ok "Подключение к серверу успешно"
  
  # Проверка требований
  log "Проверка требований..."
  
  PREREQ_CHECK=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOF'
    errors=""
    
    # Docker
    if ! command -v docker >/dev/null 2>&1; then
      errors="$errors docker"
    fi
    
    # RAM (минимум 2GB)
    mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    if [ "$mem_kb" -lt 1900000 ]; then
      errors="$errors RAM<2GB"
    fi
    
    # Disk (минимум 10GB свободно)
    disk_available=$(df / | tail -1 | awk '{print $4}')
    if [ "$disk_available" -lt 10000000 ]; then
      errors="$errors Disk<10GB"
    fi
    
    if [ -n "$errors" ]; then
      echo "MISSING:$errors"
    else
      echo "OK"
    fi
EOF
  2>&1)
  
  if [ "$PREREQ_CHECK" != "OK" ]; then
    log_err "Не выполнены требования: $PREREQ_CHECK"
    log "Установка Docker если отсутствует..."
    
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOF'
      if ! command -v docker >/dev/null 2>&1; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
      fi
EOF
  fi
  log_ok "Все требования выполнены"
  
  # Проверка существующей установки
  DOKPLOY_EXISTS=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "docker ps -a --filter name=dokploy -q" 2>&1 || true)
  
  if [ -n "$DOKPLOY_EXISTS" ]; then
    log_warn "Dokploy уже установлен"
    read -p "Переустановить? (y/N): " REINSTALL
    if [ "$REINSTALL" != "y" ] && [ "$REINSTALL" != "Y" ]; then
      log "Установка отменена"
      exit 0
    fi
    
    log "Удаление существующей установки..."
    ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "docker stop dokploy 2>/dev/null || true; docker rm dokploy 2>/dev/null || true"
  fi
  
  # Установка Dokploy
  log "Установка Dokploy..."
  
  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOF'
    set -e
    curl -sSL https://dokploy.com/install.sh | sh
EOF
  
  log_ok "Dokploy установлен!"
  
  # Проверка статуса
  sleep 5
  DOKPLOY_STATUS=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "docker ps --filter name=dokploy --format '{{.Status}}'" 2>&1 || true)
  
  if echo "$DOKPLOY_STATUS" | grep -q "Up"; then
    log_ok "Dokploy запущен и работает"
  else
    log_warn "Dokploy может ещё запускаться..."
  fi
  
  echo ""
  echo "=============================================="
  echo -e "${GREEN}Dokploy успешно установлен!${NC}"
  echo "=============================================="
  echo ""
  echo "Dokploy UI: http://$REMOTE_HOST:$DOKPLOY_PORT"
  echo ""
  echo "Следующие шаги:"
  echo "1. Откройте http://$REMOTE_HOST:$DOKPLOY_PORT"
  echo "2. Создайте admin аккаунт"
  echo "3. Настройте проект (см. docs/deployment/DOKPLOY_DEPLOYMENT.md)"
  echo ""
}

install_dokploy_local() {
  log "Локальная установка Dokploy (для тестирования)..."
  
  # Проверка Docker
  if ! command -v docker >/dev/null 2>&1; then
    log_err "Docker не установлен"
    exit 1
  fi
  
  # Проверка существующей установки
  DOKPLOY_EXISTS=$(docker ps -a --filter name=dokploy -q 2>&1 || true)
  
  if [ -n "$DOKPLOY_EXISTS" ]; then
    log_warn "Dokploy уже установлен локально"
    read -p "Переустановить? (y/N): " REINSTALL
    if [ "$REINSTALL" != "y" ] && [ "$REINSTALL" != "Y" ]; then
      exit 0
    fi
    docker stop dokploy 2>/dev/null || true
    docker rm dokploy 2>/dev/null || true
  fi
  
  # Установка
  curl -sSL https://dokploy.com/install.sh | sh
  
  log_ok "Dokploy установлен локально: http://localhost:$DOKPLOY_PORT"
}

# Main
if [ "$LOCAL_INSTALL" = true ]; then
  install_dokploy_local
else
  install_dokploy_remote
fi
