#!/bin/bash
# Скрипт для мониторинга 2FA авторизации на VPS

echo "🔍 Мониторинг Telegram 2FA авторизации..."
echo "==========================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SSH_KEY="~/.ssh/id_rsa_n8n"
VPS_HOST="root@37.53.91.144"
BACKEND_CONTAINER="sattva-streamer-backend-1"

echo -e "${BLUE}📡 Проверка статуса backend...${NC}"
ssh -i $SSH_KEY $VPS_HOST "docker ps --filter 'name=backend' --format 'table {{.Names}}\t{{.Status}}'"
echo ""

echo -e "${BLUE}📋 Последние 50 строк логов (фильтр: sign_in):${NC}"
echo "-------------------------------------------"
ssh -i $SSH_KEY $VPS_HOST "docker logs $BACKEND_CONTAINER --tail 50 2>&1 | grep -E '(sign_in|2FA|Password|PhoneCode|check_password)' || echo 'Нет логов sign_in'"
echo ""

echo -e "${YELLOW}💡 Ожидаемые логи при успешной 2FA авторизации:${NC}"
echo "1️⃣  [sign_in] Calling sign_in...              # Первый вызов с кодом"
echo "2️⃣  [sign_in] 2FA required                    # SessionPasswordNeeded"
echo "3️⃣  [sign_in] Extended client TTL (600s)      # Продление сессии"
echo "4️⃣  [sign_in] Reconnected for 2FA!            # Переподключение"
echo "5️⃣  [sign_in] Password provided, skipping...  # ✅ Пропуск sign_in"
echo "6️⃣  [sign_in] 2FA passed! user_id=...        # ✅ Успех!"
echo ""

echo -e "${RED}❌ СТАРЫЕ логи (до исправления):${NC}"
echo "[sign_in] Calling sign_in...                 # ← Повторный вызов"
echo "[sign_in] PhoneCodeExpired error             # ← Код истёк"
echo ""

echo -e "${GREEN}✅ НОВЫЕ логи (после исправления V4):${NC}"
echo "[sign_in] Password provided, skipping...     # ← Пропуск sign_in"
echo "[sign_in] 2FA passed! user_id=123456789      # ← Успех!"
echo ""

echo "==========================================="
echo -e "${BLUE}🔄 Мониторинг в реальном времени (Ctrl+C для выхода):${NC}"
ssh -i $SSH_KEY $VPS_HOST "docker logs -f $BACKEND_CONTAINER 2>&1 | grep --line-buffered -E '(sign_in|2FA|Password|PhoneCode|check_password)'"
