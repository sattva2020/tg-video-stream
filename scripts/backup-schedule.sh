#!/usr/bin/env bash
set -euo pipefail

# Ensure output is not buffered
export PYTHONUNBUFFERED=1
stdbuf -o0 -e0 true 2>/dev/null || true

##############################################################################
# Automated Backup Scheduling Script
# Настройка автоматического резервного копирования
# Usage: bash backup-schedule.sh [--dry-run] [--schedule-type cron|systemd]
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions (must be defined before argument parsing)
log_section() {
  printf '\n%s\n' "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  printf '%s\n' "$1"
  printf '%s\n' "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

log_ok() {
  printf '%s %s\n' "✓" "$1"
}

log_err() {
  printf '%s %s\n' "✗" "$1"
}

log_info() {
  printf '%s %s\n' "→" "$1"
}

# Default configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"

# Auto-detect schedule type if not specified
if [ -z "${SCHEDULE_TYPE:-}" ]; then
  if command -v systemctl >/dev/null 2>&1; then
    SCHEDULE_TYPE="systemd"
  elif command -v crontab >/dev/null 2>&1; then
    SCHEDULE_TYPE="cron"
  else
    # Default to cron when neither is available (allows dry-run validation)
    SCHEDULE_TYPE="cron"
  fi
fi

BACKUP_TIME="${BACKUP_TIME:-02:00}"  # Default 2 AM
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_BACKUPS="${MAX_BACKUPS:-10}"

# Flags
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --schedule-type)
      SCHEDULE_TYPE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash backup-schedule.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry-run              Validate configuration without applying changes"
      echo "  --schedule-type TYPE   Set schedule type: cron or systemd (default: auto-detect)"
      echo "  --help, -h             Show this help message"
      echo ""
      echo "Environment Variables:"
      echo "  BACKUP_DIR             Backup directory (default: ./backups)"
      echo "  BACKUP_TIME            Backup time HH:MM (default: 02:00)"
      echo "  RETENTION_DAYS         Keep backups for N days (default: 30)"
      echo "  MAX_BACKUPS            Maximum number of backups (default: 10)"
      exit 0
      ;;
    *)
      log_err "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

##############################################################################
# PHASE 1: Validation
##############################################################################

log_section "PHASE 1: Валидация окружения"

# Check if running as root for system-wide changes
if [ "$DRY_RUN" = false ] && [ "$EUID" -eq 0 ]; then
  log_info "Запуск от root (требуется для systemd)"
elif [ "$DRY_RUN" = false ] && [ "$EUID" -ne 0 ] && [ "$SCHEDULE_TYPE" = "systemd" ]; then
  log_err "systemd-таймеры требуют root прав. Используйте sudo или выберите cron"
  exit 1
fi

# Check required tools
REQUIRED_TOOLS=("tar" "gzip")
if command -v pg_dump >/dev/null 2>&1; then
  log_ok "pg_dump найден (PostgreSQL backup доступен)"
else
  log_info "pg_dump не найден (PostgreSQL backup будет пропущен)"
fi

for tool in "${REQUIRED_TOOLS[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    log_err "$tool не найден"
    exit 1
  fi
done
log_ok "Все требуемые инструменты найдены (tar, gzip)"

# Validate backup time format
if [[ ! "$BACKUP_TIME" =~ ^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$ ]]; then
  log_err "Неверный формат времени: $BACKUP_TIME (ожидается HH:MM)"
  exit 1
fi
log_ok "Время резервного копирования: $BACKUP_TIME"

# Validate retention settings
if [[ ! "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || [ "$RETENTION_DAYS" -lt 1 ]; then
  log_err "Неверное значение RETENTION_DAYS: $RETENTION_DAYS"
  exit 1
fi

if [[ ! "$MAX_BACKUPS" =~ ^[0-9]+$ ]] || [ "$MAX_BACKUPS" -lt 1 ]; then
  log_err "Неверное значение MAX_BACKUPS: $MAX_BACKUPS"
  exit 1
fi
log_ok "Настройки удержания: $MAX_BACKUPS бэкапов, $RETENTION_DAYS дней"

# Check/create backup directory
if [ ! -d "$BACKUP_DIR" ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Будет создана директория: $BACKUP_DIR"
  else
    mkdir -p "$BACKUP_DIR"
    log_ok "Создана директория для бэкапов: $BACKUP_DIR"
  fi
else
  log_ok "Директория для бэкапов существует: $BACKUP_DIR"
fi

# Check backup service API endpoint (if backend is running)
if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
  log_ok "Backend API доступен"
  BACKUP_API_AVAILABLE=true
else
  log_info "Backend API недоступен (будет использовано прямое резервирование)"
  BACKUP_API_AVAILABLE=false
fi

##############################################################################
# PHASE 2: Schedule Type Selection
##############################################################################

log_section "PHASE 2: Выбор метода планирования"

if [ "$SCHEDULE_TYPE" = "systemd" ]; then
  log_info "Использование systemd-таймеров"

  # Check systemd availability
  if ! command -v systemctl >/dev/null 2>&1; then
    if [ "$DRY_RUN" = true ]; then
      log_info "[DRY-RUN] systemd не найден, но валидация продолжается"
    else
      log_err "systemd не найден. Используйте --schedule-type cron"
      exit 1
    fi
  else
    log_ok "systemd доступен"
  fi

elif [ "$SCHEDULE_TYPE" = "cron" ]; then
  log_info "Использование cron"

  # Check cron availability
  if ! command -v crontab >/dev/null 2>&1; then
    if [ "$DRY_RUN" = true ]; then
      log_info "[DRY-RUN] cron не найден, но валидация продолжается"
    else
      log_err "cron не найден. Установите cron или используйте --schedule-type systemd"
      exit 1
    fi
  else
    log_ok "cron доступен"
  fi

else
  log_err "Неизвестный тип планирования: $SCHEDULE_TYPE"
  exit 1
fi

##############################################################################
# PHASE 3: Create Backup Script
##############################################################################

log_section "PHASE 3: Создание скрипта резервного копирования"

BACKUP_SCRIPT="$BACKUP_DIR/backup-run.sh"

if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Скрипт будет создан: $BACKUP_SCRIPT"
else
  cat > "$BACKUP_SCRIPT" <<'EOFSCRIPT'
#!/usr/bin/env bash
set -euo pipefail

# Automated Backup Runner
# Created by backup-schedule.sh

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$BACKUP_DIR"))")"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_BACKUPS="${MAX_BACKUPS:-10}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() {
  printf '%s %s\n' "✓" "$1"
}

log_err() {
  printf '%s %s\n' "✗" "$1"
}

log_info() {
  printf '%s %s\n' "→" "$1"
}

# Function to cleanup old backups
cleanup_old_backups() {
  local prefix="$1"
  local backups=($(find "$BACKUP_DIR" -name "${prefix}_*" -type f | sort -r))

  for i in "${!backups[@]}"; do
    local backup="${backups[$i]}"

    # Get file age in days
    local age_days=$(( ($(date +%s) - $(stat -c %Y "$backup")) / 86400 ))

    # Remove if older than retention or exceeds max count
    if [ $i -ge $MAX_BACKUPS ] || [ $age_days -gt $RETENTION_DAYS ]; then
      rm -f "$backup"
      log_info "Удален старый бэкап: $(basename "$backup")"
    fi
  done
}

# Database backup (if pg_dump available)
if command -v pg_dump >/dev/null 2>&1; then
  if [ -n "${DATABASE_URL:-}" ]; then
    log_info "Создание бэкапа базы данных..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$BACKUP_DIR/database_${timestamp}.sql.gz"

    if pg_dump "$DATABASE_URL" 2>/dev/null | gzip > "$backup_file"; then
      size=$(du -h "$backup_file" | cut -f1)
      log_ok "База данных сохранена: $backup_file ($size)"
      cleanup_old_backups "database"
    else
      log_err "Ошибка бэкапа базы данных"
    fi
  fi
fi

# Configuration backup
if [ -d "$PROJECT_ROOT/config" ]; then
  log_info "Создание бэкапа конфигурации..."
  timestamp=$(date +%Y%m%d_%H%M%S)
  backup_file="$BACKUP_DIR/config_${timestamp}.tar.gz"

  if tar -czf "$backup_file" -C "$PROJECT_ROOT" config 2>/dev/null; then
    size=$(du -h "$backup_file" | cut -f1)
    log_ok "Конфигурация сохранена: $backup_file ($size)"
    cleanup_old_backups "config"
  else
    log_err "Ошибка бэкапа конфигурации"
  fi
fi

# Call backup API if available
if curl -sf http://localhost:8000/api/v1/backup/trigger >/dev/null 2>&1; then
  log_info "Вызов API резервного копирования..."
  response=$(curl -s -X POST http://localhost:8000/api/v1/backup/trigger \
    -H "Content-Type: application/json" \
    -d '{"include_database":true,"include_config":true,"include_sessions":true}' 2>/dev/null)

  if echo "$response" | grep -q "backup_id"; then
    log_ok "API бэкап успешно создан"
  fi
fi

log_ok "Резервное копирование завершено"
EOFSCRIPT

  chmod +x "$BACKUP_SCRIPT"
  log_ok "Скрипт создан: $BACKUP_SCRIPT"
fi

##############################################################################
# PHASE 4: Setup Scheduling
##############################################################################

log_section "PHASE 4: Настройка планировщика"

# Parse backup time for cron/systemd
HOUR=$(echo "$BACKUP_TIME" | cut -d: -f1)
MINUTE=$(echo "$BACKUP_TIME" | cut -d: -f2)

if [ "$SCHEDULE_TYPE" = "systemd" ]; then
  # Setup systemd timer
  SYSTEMD_DIR="/etc/systemd/system"
  SERVICE_NAME="automated-backup"
  SERVICE_FILE="$SYSTEMD_DIR/${SERVICE_NAME}.service"
  TIMER_FILE="$SYSTEMD_DIR/${SERVICE_NAME}.timer"

  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] systemd service: $SERVICE_FILE"
    log_info "[DRY-RUN] systemd timer: $TIMER_FILE"
    log_info "[DRY-RUN] Timer schedule: OnCalendar=*-*-* ${HOUR}:${MINUTE}:00"
  else
    # Create service file
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Automated Backup Service
Documentation=https://github.com/yourusername/telegram-video-streamer

[Service]
Type=oneshot
User=root
WorkingDirectory=$PROJECT_ROOT
Environment="BACKUP_DIR=$BACKUP_DIR"
Environment="RETENTION_DAYS=$RETENTION_DAYS"
Environment="MAX_BACKUPS=$MAX_BACKUPS"
ExecStart=$BACKUP_SCRIPT
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Create timer file
    cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Automated Backup Timer
Documentation=https://github.com/yourusername/telegram-video-streamer
Requires=${SERVICE_NAME}.service

[Timer]
# Run daily at specified time
OnCalendar=*-*-* ${HOUR}:${MINUTE}:00

# Randomized delay up to 1 hour to distribute load
RandomizedDelaySec=3600

# Run immediately if timer was missed
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Reload systemd and enable timer
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.timer"
    systemctl start "${SERVICE_NAME}.timer"

    log_ok "systemd-таймер создан и активирован"
    log_info "Проверка статуса: systemctl status ${SERVICE_NAME}.timer"
  fi

elif [ "$SCHEDULE_TYPE" = "cron" ]; then
  # Setup cron job
  CRON_ENTRY="${MINUTE} ${HOUR} * * * $BACKUP_SCRIPT >> ${BACKUP_DIR}/backup.log 2>&1"

  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] cron запись: $CRON_ENTRY"
  else
    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
      log_info "cron запись уже существует"
    else
      # Add to crontab
      (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
      log_ok "cron-задание добавлено"
    fi
    log_info "Проверка расписания: crontab -l"
  fi
fi

##############################################################################
# PHASE 5: Verification
##############################################################################

log_section "PHASE 5: Проверка конфигурации"

VALIDATION_PASSED=true

# Check backup script
if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Скрипт бэкапа будет создан: $BACKUP_SCRIPT"
elif [ -f "$BACKUP_SCRIPT" ]; then
  log_ok "Скрипт бэкапа существует"
  if [ -x "$BACKUP_SCRIPT" ]; then
    log_ok "Скрипт бэкапа исполняемый"
  else
    log_err "Скрипт бэкапа не является исполняемым"
    VALIDATION_PASSED=false
  fi
else
  log_err "Скрипт бэкапа не найден"
  VALIDATION_PASSED=false
fi

# Check backup directory
if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Директория бэкапов будет проверена: $BACKUP_DIR"
elif [ -d "$BACKUP_DIR" ]; then
  if [ -w "$BACKUP_DIR" ]; then
    log_ok "Директория бэкапов доступна для записи"
  else
    log_err "Нет прав на запись в директорию бэкапов"
    VALIDATION_PASSED=false
  fi
else
  log_err "Директория бэкапов не существует"
  VALIDATION_PASSED=false
fi

# Check systemd timer (if applicable)
if [ "$SCHEDULE_TYPE" = "systemd" ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Пропуск проверки systemd-таймера"
  elif command -v systemctl >/dev/null 2>&1; then
    if systemctl list-timers | grep -q "automated-backup.timer"; then
      log_ok "systemd-таймер активен"
    else
      log_err "systemd-таймер не найден в списке активных"
      VALIDATION_PASSED=false
    fi
  fi
fi

# Check cron job (if applicable)
if [ "$SCHEDULE_TYPE" = "cron" ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Пропуск проверки cron-задания"
  elif command -v crontab >/dev/null 2>&1; then
    if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
      log_ok "cron-задание установлено"
    else
      log_err "cron-задание не найдено"
      VALIDATION_PASSED=false
    fi
  fi
fi

if [ "$VALIDATION_PASSED" = true ]; then
  log_ok "Backup schedule validated"
else
  log_err "Валидация не пройдена"
  exit 1
fi

##############################################################################
# COMPLETION
##############################################################################

log_section "НАСТРОЙКА ЗАВЕРШЕNA ✓"

echo ""
log_ok "Автоматическое резервное копирование настроено"
echo ""
printf '%s\n' "Конфигурация:"
echo "  Директория бэкапов:  $BACKUP_DIR"
echo "  Расписание:          ежедневно в $BACKUP_TIME"
echo "  Метод планирования:  $SCHEDULE_TYPE"
echo "  Удержание:           $MAX_BACKUPS бэкапов, $RETENTION_DAYS дней"
echo ""
printf '%s\n' "Полезные команды:"

if [ "$SCHEDULE_TYPE" = "systemd" ]; then
  echo "  systemctl status automated-backup.timer    # Статус таймера"
  echo "  systemctl list-timers automated-backup     # Следующий запуск"
  echo "  journalctl -u automated-backup             # Логи выполнения"
  echo "  systemctl stop automated-backup.timer      # Остановить таймер"
else
  echo "  crontab -l                                  # Просмотр расписания"
  echo "  tail -f $BACKUP_DIR/backup.log              # Логи выполнения"
fi

echo ""
printf '%s\n' "Ручной запуск:"
echo "  bash $BACKUP_SCRIPT"
echo ""
