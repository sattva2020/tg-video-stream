#!/bin/bash
# Скрипт для тестирования Telegram алертов
# Автор: Jarvis (DevOps Senior)
# Дата: 27 декабря 2025

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Telegram Alerts Testing Script           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Загрузка переменных из .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓${NC} Loaded .env file"
else
    echo -e "${RED}✗${NC} .env file not found!"
    exit 1
fi

# Проверка переменных
echo ""
echo -e "${YELLOW}Checking configuration...${NC}"

if [ -z "$ALERTMANAGER_TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}✗${NC} ALERTMANAGER_TELEGRAM_BOT_TOKEN is not set in .env"
    echo "   Please add: ALERTMANAGER_TELEGRAM_BOT_TOKEN=your_bot_token"
    exit 1
else
    echo -e "${GREEN}✓${NC} Bot token is configured"
fi

if [ -z "$ALERTMANAGER_TELEGRAM_CHAT_ID" ]; then
    echo -e "${RED}✗${NC} ALERTMANAGER_TELEGRAM_CHAT_ID is not set in .env"
    echo "   Please add: ALERTMANAGER_TELEGRAM_CHAT_ID=your_chat_id"
    exit 1
else
    echo -e "${GREEN}✓${NC} Chat ID is configured: $ALERTMANAGER_TELEGRAM_CHAT_ID"
fi

# Функция для отправки тестового сообщения
send_test_message() {
    local message="$1"
    
    echo ""
    echo -e "${YELLOW}Sending test message via Telegram API...${NC}"
    
    response=$(curl -s -X POST \
        "https://api.telegram.org/bot${ALERTMANAGER_TELEGRAM_BOT_TOKEN}/sendMessage" \
        -H 'Content-Type: application/json' \
        -d "{
            \"chat_id\": \"${ALERTMANAGER_TELEGRAM_CHAT_ID}\",
            \"text\": \"${message}\",
            \"parse_mode\": \"HTML\"
        }")
    
    if echo "$response" | grep -q '"ok":true'; then
        echo -e "${GREEN}✓${NC} Test message sent successfully!"
        echo -e "  Response: $(echo "$response" | jq -r '.result.message_id // empty')"
        return 0
    else
        echo -e "${RED}✗${NC} Failed to send test message"
        echo "  Error: $(echo "$response" | jq -r '.description // empty')"
        return 1
    fi
}

# Функция для отправки тестового алерта через Alertmanager
send_test_alert() {
    local severity="$1"
    local alertname="$2"
    local summary="$3"
    local description="$4"
    
    echo ""
    echo -e "${YELLOW}Sending test alert to Alertmanager...${NC}"
    echo -e "  Severity: ${severity}"
    echo -e "  Alert: ${alertname}"
    
    response=$(curl -s -X POST http://localhost:19093/api/v1/alerts \
        -H 'Content-Type: application/json' \
        -d "[{
            \"labels\": {
                \"alertname\": \"${alertname}\",
                \"severity\": \"${severity}\",
                \"instance\": \"test\",
                \"job\": \"test\"
            },
            \"annotations\": {
                \"summary\": \"${summary}\",
                \"description\": \"${description}\"
            },
            \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",
            \"endsAt\": \"$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%S.000Z)\"
        }]")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Test alert sent to Alertmanager"
        echo -e "  ${BLUE}Check your Telegram in 30 seconds${NC} (group_wait time)"
        return 0
    else
        echo -e "${RED}✗${NC} Failed to send alert to Alertmanager"
        echo "  Error: $response"
        return 1
    fi
}

# Проверка доступности Alertmanager
check_alertmanager() {
    echo ""
    echo -e "${YELLOW}Checking Alertmanager status...${NC}"
    
    if curl -s http://localhost:19093/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Alertmanager is running"
        
        # Проверка конфигурации
        status=$(curl -s http://localhost:19093/api/v1/status)
        if echo "$status" | grep -q "telegram"; then
            echo -e "${GREEN}✓${NC} Telegram receiver is configured"
        else
            echo -e "${YELLOW}⚠${NC} Telegram receiver not found in Alertmanager config"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} Alertmanager is not accessible on port 19093"
        echo "  Run: docker compose -f docker-compose.monitoring.yml up -d alertmanager"
        return 1
    fi
}

# Меню выбора теста
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Select test type:${NC}"
echo ""
echo "  1) Test Telegram API directly (simple message)"
echo "  2) Test Alertmanager integration (warning alert)"
echo "  3) Test Alertmanager integration (critical alert)"
echo "  4) Run all tests"
echo "  5) Exit"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        send_test_message "🔔 <b>Test Alert</b>\n\nThis is a test message from Prometheus monitoring system.\n\n✅ If you see this, Telegram integration is working!"
        ;;
    2)
        check_alertmanager
        if [ $? -eq 0 ]; then
            send_test_alert \
                "warning" \
                "TestWarningAlert" \
                "Test warning alert" \
                "This is a test warning alert to verify Alertmanager → Telegram integration"
        fi
        ;;
    3)
        check_alertmanager
        if [ $? -eq 0 ]; then
            send_test_alert \
                "critical" \
                "TestCriticalAlert" \
                "Test critical alert" \
                "This is a test CRITICAL alert to verify Alertmanager → Telegram integration"
        fi
        ;;
    4)
        echo -e "${BLUE}Running all tests...${NC}"
        send_test_message "🧪 <b>Test #1: Direct Telegram API</b>\n\nIf you see this, direct API works!"
        
        check_alertmanager
        if [ $? -eq 0 ]; then
            sleep 2
            send_test_alert \
                "warning" \
                "TestWarningAlert" \
                "Test #2: Warning alert via Alertmanager" \
                "Testing Alertmanager routing to Telegram"
            
            sleep 2
            send_test_alert \
                "critical" \
                "TestCriticalAlert" \
                "Test #3: Critical alert via Alertmanager" \
                "Testing critical severity routing"
        fi
        ;;
    5)
        echo -e "${BLUE}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Test completed!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Check your Telegram for alerts"
echo "  2. View Alertmanager UI: http://localhost:19093"
echo "  3. Check logs: docker logs sattva-alertmanager"
echo ""
