#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# Unified Deployment Script
# Автоматическое определение окружения и единый процесс развёртывания
# Поддерживает: Docker и bare-metal (systemd) развёртывание
#
# Usage:
#   bash scripts/deploy-unified.sh [OPTIONS]
#
# Options:
#   --validate           Проверить конфигурацию без развёртывания
#   --docker             Принудительно использовать Docker
#   --bare-metal         Принудительно использовать bare-metal (systemd)
#   --remote HOST        Развернуть на удаленном сервере
#   --full               Полное развёртывание с зависимостями
#   --help, -h           Показать справку
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Deployment mode
DEPLOY_MODE=""
REMOTE_HOST=""
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"

# Flags
VALIDATE_ONLY=false
FORCE_MODE=false

##############################################################################
# Logging Functions
##############################################################################

log_section() {
  echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_ok() {
  echo -e "${GREEN}✓ $1${NC}"
}

log_err() {
  echo -e "${RED}✗ $1${NC}"
}

log_info() {
  echo -e "${YELLOW}→ $1${NC}"
}

##############################################################################
# Environment Detection
##############################################################################

detect_environment() {
  log_section "Обнаружение окружения"

  # Check if Docker is available
  if command -v docker >/dev/null 2>&1; then
    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
      log_ok "Docker обнаружен и запущен"

      # Check for docker-compose
      if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
        log_ok "Docker Compose v2 доступен"
      elif docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
        log_ok "Docker Compose standalone доступен"
      else
        log_err "Docker Compose не найден"
        return 1
      fi

      if [ "$FORCE_MODE" = false ]; then
        DEPLOY_MODE="docker"
        log_info "Автоматический выбор: Docker развёртывание"
      fi
      return 0
    else
      log_info "Docker найден, но демон не запущен"
    fi
  else
    log_info "Docker не установлен"
  fi

  # Check for bare-metal prerequisites
  if command -v python3 >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
    log_ok "Пререквизиты bare-metal найдены (python3, systemd)"

    if [ "$FORCE_MODE" = false ]; then
      DEPLOY_MODE="bare-metal"
      log_info "Автоматический выбор: Bare-metal развёртывание"
    fi
    return 0
  else
    log_err "Пререквизиты bare-metal не найдены (требуются python3, systemd)"
    return 1
  fi

  return 1
}

##############################################################################
# Validation Functions
##############################################################################

validate_configuration() {
  log_section "Валидация конфигурации"

  local errors=0

  # Check docker-compose.yml exists (for Docker mode)
  if [ "$DEPLOY_MODE" = "docker" ] || [ -z "$DEPLOY_MODE" ]; then
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
      log_ok "docker-compose.yml найден"
    else
      log_err "docker-compose.yml не найден"
      errors=$((errors + 1))
    fi
  fi

  # Check preflight script exists
  if [ -f "$SCRIPT_DIR/preflight-env.sh" ]; then
    log_ok "Скрипт preflight-env.sh найден"
  else
    log_err "Скрипт preflight-env.sh не найден"
    errors=$((errors + 1))
  fi

  # Check for systemd units (for bare-metal mode)
  if [ "$DEPLOY_MODE" = "bare-metal" ] || [ -z "$DEPLOY_MODE" ]; then
    if compgen -G "$PROJECT_ROOT/config/systemd/*.service" >/dev/null; then
      log_ok "Systemd service файлы найдены"
    else
      log_info "Systemd service файлы не найдены (опционально для Docker)"
    fi
  fi

  # Run preflight validation
  log_info "Запуск pre-flight проверки..."
  if bash "$SCRIPT_DIR/preflight-env.sh" >/dev/null 2>&1; then
    log_ok "Pre-flight проверка пройдена"
  else
    log_err "Pre-flight проверка не пройдена"
    log_info "Запустите 'bash scripts/preflight-env.sh' для деталей"
    errors=$((errors + 1))
  fi

  if [ $errors -eq 0 ]; then
    log_ok "Конфигурация валидна"
    log_ok "Deployment configuration valid"
    return 0
  else
    log_err "Обнаружено $errors ошибок в конфигурации"
    return 1
  fi
}

validate_docker() {
  log_section "Валидация Docker окружения"

  bash "$SCRIPT_DIR/preflight-env.sh" --check-docker
}

validate_bare_metal() {
  log_section "Валидация bare-metal окружения"

  bash "$SCRIPT_DIR/preflight-env.sh" --check-deps

  # Additional checks for systemd
  if command -v systemctl >/dev/null 2>&1; then
    log_ok "systemd доступен"
  else
    log_err "systemd не найден"
    return 1
  fi

  return 0
}

##############################################################################
# Docker Deployment
##############################################################################

deploy_docker() {
  log_section "Docker развёртывание"

  cd "$PROJECT_ROOT"

  # Validate Docker environment first
  if ! validate_docker; then
    log_err "Валидация Docker окружения не пройдена"
    return 1
  fi

  # Decrypt secrets if needed
  if [ -f "$PROJECT_ROOT/.env.enc" ]; then
    log_info "Расшифровка секретов..."
    if [ -f "$SCRIPT_DIR/decrypt-secrets.sh" ]; then
      if bash "$SCRIPT_DIR/decrypt-secrets.sh" --force 2>/dev/null; then
        log_ok "Секреты расшифрованы"
      else
        log_err "Ошибка расшифровки секретов"
        return 1
      fi
    else
      log_err "Скрипт decrypt-secrets.sh не найден"
      return 1
    fi
  fi

  # Build and start services
  log_info "Сборка и запуск Docker сервисов..."
  if $COMPOSE_CMD up -d --build; then
    log_ok "Docker сервисы запущены"
  else
    log_err "Ошибка запуска Docker сервисов"
    return 1
  fi

  # Wait for services to be healthy
  log_info "Ожидание готовности сервисов..."
  sleep 10

  # Show status
  log_info "Статус сервисов:"
  $COMPOSE_CMD ps

  log_ok "Docker развёртывание завершено"
}

##############################################################################
# Bare-Metal Deployment
##############################################################################

deploy_bare_metal() {
  log_section "Bare-metal развёртывание"

  cd "$PROJECT_ROOT"

  # Validate bare-metal environment first
  if ! validate_bare_metal; then
    log_err "Валидация bare-metal окружения не пройдена"
    return 1
  fi

  # Decrypt secrets if needed
  if [ -f "$PROJECT_ROOT/.env.enc" ]; then
    log_info "Расшифровка секретов..."
    if [ -f "$SCRIPT_DIR/decrypt-secrets.sh" ]; then
      if bash "$SCRIPT_DIR/decrypt-secrets.sh" --force 2>/dev/null; then
        log_ok "Секреты расшифрованы"
      else
        log_err "Ошибка расшифровки секретов"
        return 1
      fi
    else
      log_err "Скрипт decrypt-secrets.sh не найден"
      return 1
    fi
  fi

  # Check for deployment script or create services manually
  if [ -f "$SCRIPT_DIR/deploy_full.sh" ]; then
    log_info "Использование существующего скрипта развёртывания..."
    log_info "Для bare-metal развёртывания используйте:"
    log_info "  bash scripts/deploy_full.sh"
    return 1
  fi

  # Manual deployment steps
  log_info "Установка Python зависимостей..."
  if [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
    cd "$PROJECT_ROOT/backend"
    if [ ! -d venv ]; then
      python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
    log_ok "Зависимости установлены"
  fi

  log_info "Bare-metal развёртывание завершено"
  log_info "Вручную настройте systemd сервисы из config/systemd/"
}

##############################################################################
# Remote Deployment
##############################################################################

deploy_remote() {
  log_section "Удалённое развёртывание"

  local remote_host="$1"

  # Check SSH connectivity
  if [ ! -f "$SSH_KEY" ]; then
    log_err "SSH ключ не найден: $SSH_KEY"
    log_info "Установите переменную SSH_KEY или используйте ключ по умолчанию"
    return 1
  fi

  SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $SSH_KEY"

  log_info "Проверка подключения к $REMOTE_USER@$remote_host..."
  if ! ssh $SSH_OPTS -p $REMOTE_PORT "$REMOTE_USER@$remote_host" "hostname" >/dev/null 2>&1; then
    log_err "Не удалось подключиться к $remote_host"
    return 1
  fi
  log_ok "Подключение к $remote_host успешно"

  # Transfer deployment package
  log_info "Подготовка пакета развёртывания..."
  local archive_name="telegram-deploy-$(date +%Y%m%d-%H%M%S).tar.gz"

  cd "$PROJECT_ROOT"
  tar czf "/tmp/$archive_name" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='data' \
    --exclude='*.log' \
    . 2>/dev/null || true

  if [ ! -f "/tmp/$archive_name" ]; then
    log_err "Ошибка создания архива"
    return 1
  fi

  log_info "Передача архива на сервер..."
  scp $SSH_OPTS "/tmp/$archive_name" "$REMOTE_USER@$remote_host:/tmp/" >/dev/null 2>&1
  log_ok "Архив передан"

  # Execute remote deployment
  log_info "Выполнение удалённого развёртывания..."
  ssh $SSH_OPTS -p $REMOTE_PORT "$REMOTE_USER@$remote_host" bash -s <<EOF
set -euo pipefail

# Extract archive
cd /tmp
tar xzf $archive_name

# Detect environment and deploy
cd telegram-*
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "→ Обнаружен Docker, запуск развёртывания..."
  docker compose up -d --build
else
  echo "→ Docker не найден, требуется ручное развёртывание"
  exit 1
fi

echo "✓ Развёртывание завершено"
EOF

  if [ $? -eq 0 ]; then
    log_ok "Удалённое развёртывание завершено"
    rm -f "/tmp/$archive_name"
  else
    log_err "Ошибка удалённого развёртывания"
    rm -f "/tmp/$archive_name"
    return 1
  fi
}

##############################################################################
# Help
##############################################################################

show_help() {
  cat <<EOF
Unified Deployment Script - Автоматическое определение окружения и развёртывание

Usage:
  bash scripts/deploy-unified.sh [OPTIONS]

Options:
  --validate           Проверить конфигурацию без развёртывания
  --docker             Принудительно использовать Docker
  --bare-metal         Принудительно использовать bare-metal (systemd)
  --remote HOST        Развернуть на удаленном сервере
  --full               Полное развёртывание с зависимостями
  --help, -h           Показать эту справку

Examples:
  # Автоматическое определение и развёртывание
  bash scripts/deploy-unified.sh

  # Проверка конфигурации
  bash scripts/deploy-unified.sh --validate

  # Принудительное Docker развёртывание
  bash scripts/deploy-unified.sh --docker

  # Удалённое развёртывание
  bash scripts/deploy-unified.sh --remote 192.168.1.100

Environment Variables:
  REMOTE_USER         Пользователь SSH (по умолчанию: root)
  REMOTE_PORT         Порт SSH (по умолчанию: 22)
  SSH_KEY             Путь к SSH ключу (по умолчанию: ~/.ssh/id_rsa)

EOF
}

##############################################################################
# Main
##############################################################################

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --validate)
        VALIDATE_ONLY=true
        shift
        ;;
      --docker)
        DEPLOY_MODE="docker"
        FORCE_MODE=true
        shift
        ;;
      --bare-metal)
        DEPLOY_MODE="bare-metal"
        FORCE_MODE=true
        shift
        ;;
      --remote)
        REMOTE_HOST="$2"
        shift 2
        ;;
      --full)
        # Full deployment mode (future enhancement)
        shift
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      *)
        log_err "Неизвестный параметр: $1"
        show_help
        exit 1
        ;;
    esac
  done

  # Validate only mode
  if [ "$VALIDATE_ONLY" = true ]; then
    detect_environment
    validate_configuration
    exit $?
  fi

  # Remote deployment mode
  if [ -n "$REMOTE_HOST" ]; then
    deploy_remote "$REMOTE_HOST"
    exit $?
  fi

  # Auto-detect environment if not forced
  if [ -z "$DEPLOY_MODE" ]; then
    if ! detect_environment; then
      log_err "Не удалось определить окружение"
      log_info "Используйте --docker или --bare-metal для принудительного выбора режима"
      exit 1
    fi
  fi

  # Validate configuration
  if ! validate_configuration; then
    log_err "Валидация конфигурации не пройдена"
    exit 1
  fi

  # Execute deployment based on mode
  case "$DEPLOY_MODE" in
    docker)
      deploy_docker
      ;;
    bare-metal)
      deploy_bare_metal
      ;;
    *)
      log_err "Неизвестный режим развёртывания: $DEPLOY_MODE"
      exit 1
      ;;
  esac

  log_section "РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО ✓"
}

main "$@"
