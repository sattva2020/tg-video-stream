#!/bin/bash
# Тестирование добавления Telegram аккаунта с 2FA
# Использование: ./scripts/test-telegram-2fa.sh

set -e

echo "🧪 Тестирование Telegram авторизации с двухфакторной аутентификацией"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверяем, что backend работает
echo "1️⃣ Проверяем доступность backend..."
if curl -s -o /dev/null -w "%{http_code}" https://sattva-streamer.top/health | grep -q "200"; then
    echo "✅ Backend доступен"
else
    echo "❌ Backend недоступен! Проверьте: docker compose ps"
    exit 1
fi

echo ""
echo "2️⃣ Запускаем мониторинг логов в фоне..."
# Создаём временный файл для логов
LOG_FILE=$(mktemp)
echo "📝 Логи сохраняются в: $LOG_FILE"

# Запускаем мониторинг в фоне
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 \
  "cd /opt/sattva-streamer && docker compose logs -f backend" 2>/dev/null | \
  grep -E 'send_code|sign_in|Client|PhoneCode|is_connected|2FA' | \
  tee "$LOG_FILE" &

MONITOR_PID=$!
echo "🔍 Мониторинг запущен (PID: $MONITOR_PID)"

echo ""
echo "3️⃣ Откройте в браузере:"
echo "   👉 https://sattva-streamer.top"
echo ""
echo "4️⃣ Пошаговая инструкция:"
echo "   1. Авторизуйтесь как Admin (если нужно)"
echo "   2. Перейдите в 'Управление каналами'"
echo "   3. Нажмите 'Подключить аккаунт'"
echo "   4. Введите номер телефона (с кодом страны, например +380673229820)"
echo "   5. Введите код из Telegram"
echo "   6. Если появится запрос 2FA пароля - введите пароль"
echo ""
echo "5️⃣ Ожидаемые логи при успехе:"
echo "   ✅ [send_code] is_connected=True"
echo "   ✅ [sign_in] is_connected=True"
echo "   ✅ [sign_in] 2FA required"
echo "   ✅ [sign_in] Extended client TTL (600s)"
echo "   ✅ [sign_in] Reconnected! is_connected=True"
echo "   ✅ [sign_in] 2FA passed! user_id=..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏸️  Мониторинг логов запущен. Нажмите Ctrl+C для остановки."
echo ""

# Ждём сигнала остановки
trap "kill $MONITOR_PID 2>/dev/null; echo ''; echo '✅ Мониторинг остановлен'; echo '📄 Полные логи: $LOG_FILE'; exit 0" INT TERM

# Ждём завершения мониторинга
wait $MONITOR_PID
