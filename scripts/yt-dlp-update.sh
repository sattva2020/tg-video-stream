#!/usr/bin/env bash
# ==============================================================================
# yt-dlp Auto-Update Script
# ==============================================================================
# Автоматически обновляет yt-dlp и перезапускает стример при необходимости.
# Запускается через systemd timer ежедневно в 04:00 UTC.
#
# Особенности:
#   - Проверяет наличие новой версии перед обновлением
#   - Логирует все действия
#   - Перезапускает стример только если была новая версия
#   - Отправляет уведомление в Telegram при ошибках (опционально)
# ==============================================================================
set -euo pipefail

# ==================== Конфигурация ====================
LOG_FILE="/var/log/yt-dlp-update.log"
STREAMER_DIR="/opt/sattva-streamer/streamer"
VENV_DIR="${STREAMER_DIR}/venv"
STREAMER_SERVICE="sattva-streamer"  # имя systemd сервиса стримера

# Опционально: Telegram уведомления
TELEGRAM_NOTIFY="${TELEGRAM_NOTIFY:-false}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ==================== Функции ====================

log() {
    local level="$1"
    shift
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [$level] $*" | tee -a "$LOG_FILE"
}

send_telegram() {
    if [[ "$TELEGRAM_NOTIFY" == "true" && -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        local message="$1"
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${message}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

get_yt_dlp_version() {
    "${VENV_DIR}/bin/yt-dlp" --version 2>/dev/null || echo "unknown"
}

check_latest_version() {
    # Получаем последнюю версию с PyPI
    curl -s "https://pypi.org/pypi/yt-dlp/json" 2>/dev/null | \
        grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown"
}

# ==================== Основная логика ====================

main() {
    log "INFO" "========== yt-dlp Auto-Update Started =========="

    # Проверяем наличие venv
    if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
        log "ERROR" "Virtual environment not found at ${VENV_DIR}"
        send_telegram "❌ <b>yt-dlp update failed</b>%0AVenv not found at ${VENV_DIR}"
        exit 2
    fi

    # Активируем venv
    # shellcheck source=/dev/null
    source "${VENV_DIR}/bin/activate"

    # Текущая и последняя версии
    CURRENT_VERSION=$(get_yt_dlp_version)
    LATEST_VERSION=$(check_latest_version)

    log "INFO" "Current version: ${CURRENT_VERSION}"
    log "INFO" "Latest version:  ${LATEST_VERSION}"

    # Проверяем нужно ли обновление
    if [[ "$CURRENT_VERSION" == "$LATEST_VERSION" ]]; then
        log "INFO" "yt-dlp is already up to date (${CURRENT_VERSION})"
        exit 0
    fi

    if [[ "$LATEST_VERSION" == "unknown" ]]; then
        log "WARN" "Could not determine latest version, forcing update anyway"
    fi

    # Выполняем обновление
    log "INFO" "Updating yt-dlp..."
    if pip install -U yt-dlp >> "$LOG_FILE" 2>&1; then
        NEW_VERSION=$(get_yt_dlp_version)
        log "INFO" "Successfully updated yt-dlp: ${CURRENT_VERSION} -> ${NEW_VERSION}"

        # Перезапускаем стример если он запущен
        if systemctl is-active --quiet "$STREAMER_SERVICE" 2>/dev/null; then
            log "INFO" "Restarting ${STREAMER_SERVICE}..."
            if systemctl restart "$STREAMER_SERVICE"; then
                log "INFO" "${STREAMER_SERVICE} restarted successfully"
                send_telegram "✅ <b>yt-dlp updated</b>%0A${CURRENT_VERSION} → ${NEW_VERSION}%0AStreamer restarted"
            else
                log "ERROR" "Failed to restart ${STREAMER_SERVICE}"
                send_telegram "⚠️ <b>yt-dlp updated but restart failed</b>%0A${CURRENT_VERSION} → ${NEW_VERSION}"
            fi
        else
            log "INFO" "${STREAMER_SERVICE} is not running, skipping restart"
            send_telegram "✅ <b>yt-dlp updated</b>%0A${CURRENT_VERSION} → ${NEW_VERSION}%0AStreamer was not running"
        fi
    else
        log "ERROR" "Failed to update yt-dlp"
        send_telegram "❌ <b>yt-dlp update failed</b>%0ACheck logs: ${LOG_FILE}"
        exit 1
    fi

    log "INFO" "========== yt-dlp Auto-Update Finished =========="
}

# Запуск
main "$@"
