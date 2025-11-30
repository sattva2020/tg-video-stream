#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# Remote Deployment Master Script
# Полное развёртывание Telegram Video Streamer на удаленном сервере
# Usage: bash deploy_full.sh
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

SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $SSH_KEY"

# Test connection
if ! ssh $SSH_OPTS -p $REMOTE_PORT "$REMOTE_USER@$REMOTE_HOST" "hostname" >/dev/null 2>&1; then
  log_err "Не удалось подключиться к $REMOTE_HOST"
  exit 1
fi
log_ok "Подключение к $REMOTE_HOST успешно"

# Verify prerequisites
log_info "Проверка предусловий на удаленном сервере..."

PREREQ_SCRIPT='
  errors=""
  
  # Python
  if ! command -v python3 >/dev/null 2>&1; then
    errors="$errors python3"
  fi
  
  # pip
  if ! python3 -m pip --version >/dev/null 2>&1; then
    errors="$errors pip"
  fi
  
  # systemd
  if ! command -v systemctl >/dev/null 2>&1; then
    errors="$errors systemctl"
  fi
  
  # venv support
  if ! python3 -m venv --help >/dev/null 2>&1; then
    errors="$errors venv"
  fi
  
  if [ -n "$errors" ]; then
    echo "MISSING:$errors"
    exit 1
  fi
  echo "OK"
'

PREREQ_CHECK=$(ssh $SSH_OPTS -p $REMOTE_PORT "$REMOTE_USER@$REMOTE_HOST" bash -s <<EOF
$PREREQ_SCRIPT
EOF
2>&1)

if [ "$PREREQ_CHECK" != "OK" ]; then
  log_err "Ошибка проверки предусловий:"
  echo "  $PREREQ_CHECK"
  exit 1
fi
log_ok "Все предусловия проверены (python3, pip, systemd, venv)"

##############################################################################
# PHASE 3: Create deployment user
##############################################################################

log_section "PHASE 3: Подготовка учетной записи tgstream"

CREATE_USER=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOFUSER'
if id -u tgstream >/dev/null 2>&1; then
  echo "EXISTS"
else
  echo "CREATING"
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
scp $SSH_OPTS "$ARTIFACT" "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Артефакт передан: /tmp/$ARTIFACT"

# Transfer remote_deploy.sh
log_info "Передача скрипта развёртывания..."
scp $SSH_OPTS scripts/remote_deploy.sh "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
chmod +x /tmp/remote_deploy.sh
log_ok "Скрипт remote_deploy.sh передан"

# Transfer yt-dlp-update.sh
log_info "Передача скрипта обновления yt-dlp..."
scp $SSH_OPTS scripts/yt-dlp-update.sh "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Скрипт yt-dlp-update.sh передан"

# Transfer systemd units
log_info "Передача systemd units..."
scp $SSH_OPTS specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
scp $SSH_OPTS specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.service "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
scp $SSH_OPTS specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.timer "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
log_ok "Все systemd units передачи"

##############################################################################
# PHASE 5: Execute remote deployment
##############################################################################

log_section "PHASE 5: Выполнение удаленного развёртывания"

DEPLOY_RESULT=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOFDEPLOY'
set -euo pipefail

# Execute remote_deploy.sh
echo "→ Распаковка и установка приложения..."
cd /tmp
bash ./remote_deploy.sh

# Install yt-dlp-update script in /usr/local/bin
echo "→ Установка скрипта обновления yt-dlp..."
cp /tmp/yt-dlp-update.sh /usr/local/bin/yt-dlp-update
chmod 755 /usr/local/bin/yt-dlp-update

# Install systemd units
echo "→ Установка systemd units..."
cp /tmp/tg_video_streamer.service /etc/systemd/system/
cp /tmp/yt-dlp-update.service /etc/systemd/system/
cp /tmp/yt-dlp-update.timer /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo "✓ Все компоненты установлены"
EOFDEPLOY
2>&1 | tee /tmp/deploy_log.txt)

if grep -q "✓ Все компоненты установлены" /tmp/deploy_log.txt; then
  log_ok "Удаленное развёртывание успешно"
else
  log_err "Ошибка при удаленном развёртывании"
  cat /tmp/deploy_log.txt
  exit 1
fi

##############################################################################
# PHASE 6: Enable and start services
##############################################################################

log_section "PHASE 6: Активация сервисов"

ENABLE_RESULT=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOFCHECK'
# Enable services
systemctl enable tg_video_streamer.service >/dev/null 2>&1
systemctl enable yt-dlp-update.timer >/dev/null 2>&1

# Start main service
systemctl start tg_video_streamer.service
sleep 2

# Check status
if systemctl is-active --quiet tg_video_streamer; then
  echo "ACTIVE"
else
  echo "FAILED"
fi
EOFCHECK
2>&1)

if [ "$ENABLE_RESULT" = "ACTIVE" ]; then
  log_ok "Сервис tg_video_streamer запущен и активен"
else
  log_err "Сервис не запущен. Проверяем логи..."
  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "journalctl -u tg_video_streamer -n 20" || true
  exit 1
fi

##############################################################################
# PHASE 7: Verification
##############################################################################

log_section "PHASE 7: Финальная проверка"

VERIFY=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" bash -s <<'EOFVERIFY'
echo "Service status:"
systemctl status tg_video_streamer --no-pager || true

echo ""
echo "Timer status:"
systemctl list-timers yt-dlp-update --no-pager || true

echo ""
echo "Recent logs:"
journalctl -u tg_video_streamer -n 10 --no-pager || true
EOFVERIFY
2>&1)

echo "$VERIFY"

##############################################################################
# COMPLETION
##############################################################################

log_section "РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО ✓"

echo ""
log_ok "Telegram Video Streamer успешно развёрнут на $REMOTE_HOST"
echo ""
echo -e "${YELLOW}Постоянные ссылки и команды:${NC}"
echo "  Release path:     /opt/tg_video_streamer/releases/<version>"
echo "  Current symlink:  /opt/tg_video_streamer/current"
echo "  Config file:      /opt/tg_video_streamer/current/.env"
echo "  Logs:             journalctl -u tg_video_streamer"
echo "  yt-dlp updates:   /var/log/yt-dlp-update.log"
echo ""
echo -e "${YELLOW}Полезные команды:${NC}"
echo "  systemctl status tg_video_streamer              # Статус сервиса"
echo "  journalctl -u tg_video_streamer -f              # Реал-тайм логи"
echo "  systemctl restart tg_video_streamer             # Перезапуск"
echo "  systemctl list-timers yt-dlp-update             # Расписание обновлений"
echo ""
