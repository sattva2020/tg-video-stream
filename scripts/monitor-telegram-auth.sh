#!/bin/bash
# Скрипт мониторинга Telegram авторизации на VPS
# Показывает логи send_code, sign_in, connection status

echo "🔍 Мониторинг Telegram авторизации на VPS..."
echo "📋 Фильтруем: send_code, sign_in, Client disconnected, PhoneCodeExpired"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 \
  "cd /opt/sattva-streamer && docker compose logs -f --tail=50 backend" | \
  grep -E --color=always 'send_code|sign_in|Client|PhoneCode|is_connected|phone_code_hash'
