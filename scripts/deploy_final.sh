#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# Remote Deployment Master Script - Fixed Version
# Полное развёртывание Telegram Video Streamer на удаленном сервере
##############################################################################

REMOTE_HOST="37.53.91.144"
REMOTE_USER="root"
REMOTE_PORT="22"
SSH_KEY="$HOME/.ssh/id_rsa_n8n"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
# PHASE 1: Validation
##############################################################################

log_section "PHASE 1: Валидация окружения"

# Check SSH key
if [ ! -f "$SSH_KEY" ]; then
  log_err "SSH ключ не найден: $SSH_KEY"
  exit 1
fi
log_ok "SSH ключ найден"

# Find artifact
ARTIFACT="$(ls -1t telegram-deploy-*.tar.gz 2>/dev/null | head -n1 || true)"
if [ -z "$ARTIFACT" ]; then
  log_err "Артефакт развёртывания не найден (ожидается telegram-deploy-*.tar.gz)"
  exit 1
fi
log_ok "Артефакт найден: $ARTIFACT ($(du -h "$ARTIFACT" | cut -f1))"

# Check deploy scripts exist
for script in scripts/remote_deploy.sh scripts/yt-dlp-update.sh; do
  if [ ! -f "$script" ]; then
    log_err "Скрипт развёртывания не найден: $script"
    exit 1
  fi
done
log_ok "Все локальные скрипты развёртывания найдены"

# Check systemd units exist
for unit in specs/002-prod-broadcast-improvements/deploy/systemd/*.{service,timer}; do
  if [ ! -f "$unit" ]; then
    log_err "Systemd unit не найден: $unit"
    exit 1
  fi
done
log_ok "Все systemd units найдены"

##############################################################################
# PHASE 2: Connect and verify remote
##############################################################################

log_section "PHASE 2: Подключение к удаленному серверу"

# Test connection
if ! ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "hostname" >/dev/null 2>&1; then
  log_err "Не удалось подключиться к $REMOTE_HOST:$REMOTE_PORT"
  exit 1
fi
log_ok "Подключение к $REMOTE_HOST:$REMOTE_PORT успешно"

# Verify prerequisites
log_info "Проверка предусловий на удаленном сервере..."

PREREQ_CHECK=$(ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" << 'EOFPREREQ'
if ! command -v python3 >/dev/null 2>&1; then
  echo "MISSING: python3"
  exit 1
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
  echo "MISSING: pip"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "MISSING: systemctl"
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "MISSING: venv"
  exit 1
fi

echo "OK"
EOFPREREQ
2>&1)

if [ "$PREREQ_CHECK" != "OK" ]; then
  LAST_LINE=$(echo "$PREREQ_CHECK" | tail -1)
  if [ "$LAST_LINE" = "OK" ]; then
    log_ok "Все предусловия проверены (python3, pip, systemd, venv)"
  else
    log_err "Ошибка проверки предусловий: $LAST_LINE"
    exit 1
  fi
else
  log_ok "Все предусловия проверены (python3, pip, systemd, venv)"
fi

##############################################################################
# PHASE 3: Create deployment user
##############################################################################

log_section "PHASE 3: Подготовка учетной записи tgstream"

CREATE_USER=$(ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" << 'EOFUSER'
if id -u tgstream >/dev/null 2>&1; then
  echo "EXISTS"
else
  useradd -r -s /bin/false -d /opt/tg_video_streamer -m tgstream 2>/dev/null || true
  echo "CREATED"
fi
EOFUSER
2>&1)

if echo "$CREATE_USER" | grep -q "EXISTS\|CREATED"; then
  log_ok "Учетная запись tgstream подготовлена"
else
  log_err "Не удалось создать/проверить учетную запись tgstream"
fi

##############################################################################
# PHASE 4: Transfer artifacts
##############################################################################

log_section "PHASE 4: Передача артефактов на сервер"

# Transfer deployment archive
log_info "Передача артефакта развёртывания..."
scp -i "$SSH_KEY" -P "$REMOTE_PORT" "$ARTIFACT" "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Артефакт передан: /tmp/$ARTIFACT"

# Transfer remote_deploy.sh
log_info "Передача скрипта развёртывания..."
scp -i "$SSH_KEY" -P "$REMOTE_PORT" scripts/remote_deploy.sh "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Скрипт remote_deploy.sh передан"

# Transfer yt-dlp-update.sh
log_info "Передача скрипта обновления yt-dlp..."
scp -i "$SSH_KEY" -P "$REMOTE_PORT" scripts/yt-dlp-update.sh "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Скрипт yt-dlp-update.sh передан"

# Transfer systemd units
log_info "Передача systemd units..."
scp -i "$SSH_KEY" -P "$REMOTE_PORT" specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
scp -i "$SSH_KEY" -P "$REMOTE_PORT" specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.service "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
scp -i "$SSH_KEY" -P "$REMOTE_PORT" specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.timer "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Все systemd units передачи"

##############################################################################
# PHASE 5: Execute remote deployment
##############################################################################

log_section "PHASE 5: Выполнение удаленного развёртывания"

ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" << 'EOFDEPLOY'
set -euo pipefail

echo "→ Распаковка и установка приложения..."
cd /tmp
bash ./remote_deploy.sh

echo "→ Установка скрипта обновления yt-dlp..."
cp /tmp/yt-dlp-update.sh /usr/local/bin/yt-dlp-update
chmod 755 /usr/local/bin/yt-dlp-update

echo "→ Установка systemd units..."
cp /tmp/tg_video_streamer.service /etc/systemd/system/
cp /tmp/yt-dlp-update.service /etc/systemd/system/
cp /tmp/yt-dlp-update.timer /etc/systemd/system/

echo "→ Перезагрузка systemd конфигурации..."
systemctl daemon-reload

echo "✓ Все компоненты установлены"
EOFDEPLOY

log_ok "Удаленное развёртывание успешно"

##############################################################################
# PHASE 6: Enable and start services
##############################################################################

log_section "PHASE 6: Активация сервисов"

ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" << 'EOFSTART'
echo "→ Включение сервисов..."
systemctl enable tg_video_streamer.service >/dev/null 2>&1
systemctl enable yt-dlp-update.timer >/dev/null 2>&1

echo "→ Запуск основного сервиса..."
systemctl start tg_video_streamer.service
sleep 2

# Check status
if systemctl is-active --quiet tg_video_streamer; then
  echo "✓ Сервис активен и работает"
else
  echo "✗ Сервис не запущен"
  systemctl status tg_video_streamer || true
  exit 1
fi
EOFSTART

log_ok "Сервис tg_video_streamer запущен и активен"

##############################################################################
# PHASE 7: Verification
##############################################################################

log_section "PHASE 7: Финальная проверка"

echo ""
echo "Service status:"
ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "systemctl status tg_video_streamer --no-pager || true"

echo ""
echo "Timer status:"
ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "systemctl list-timers yt-dlp-update --no-pager || true"

echo ""
echo "Recent logs (last 15 lines):"
ssh -q -i "$SSH_KEY" -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "journalctl -u tg_video_streamer -n 15 --no-pager || true"

##############################################################################
# COMPLETION
##############################################################################

log_section "РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО ✓"

echo ""
log_ok "Telegram Video Streamer успешно развёрнут на $REMOTE_HOST"
echo ""
echo -e "${YELLOW}Ключевые пути на сервере:${NC}"
echo "  Release path:     /opt/tg_video_streamer/releases/<version>"
echo "  Current symlink:  /opt/tg_video_streamer/current"
echo "  Config file:      /opt/tg_video_streamer/current/.env"
echo "  yt-dlp logs:      /var/log/yt-dlp-update.log"
echo ""
echo -e "${YELLOW}Полезные команды для проверки:${NC}"
echo "  ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 systemctl status tg_video_streamer"
echo "  ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 journalctl -u tg_video_streamer -f"
echo "  ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 tail -f /var/log/yt-dlp-update.log"
echo ""
