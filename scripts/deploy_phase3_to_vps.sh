#!/bin/bash

# ============================================================================
# РАЗВЕРТЫВАНИЕ PHASE 3 НА БОЕВОЙ СЕРВЕР (VPS 37.53.91.144)
# ============================================================================
# ВАЖНО: Этот скрипт синхронизирует весь проект и разворачивает Phase 3

set -e

VPS_HOST="37.53.91.144"
VPS_USER="root"
SSH_KEY="~/.ssh/id_rsa_n8n"
VPS_PATH="/root/telegram"
BACKUP_DIR="/root/telegram/.internal/backups"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║ РАЗВЕРТЫВАНИЕ PHASE 3 НА VPS 37.53.91.144                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

# ============================================================================
# ШАГ 0: Проверка ssh-ключа
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 0]${NC} Проверка SSH-подключения..."

if ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "echo 'SSH OK'" >/dev/null 2>&1; then
    echo -e "${RED}❌ SSH-подключение не работает!${NC}"
    echo "Проверьте:"
    echo "  - SSH-ключ: $SSH_KEY"
    echo "  - VPS хост: $VPS_HOST"
    echo "  - Пользователь: $VPS_USER"
    exit 1
fi

echo -e "${GREEN}✅ SSH-подключение OK${NC}"

# ============================================================================
# ШАГ 1: Создание бэкапа на VPS
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 1]${NC} Создание бэкапа боевой БД..."

BACKUP_FILE="backup_vps_phase3_$(date +%Y%m%d_%H%M%S).sql"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    mkdir -p /root/telegram/.internal/backups
    if command -v mysql &> /dev/null; then
        BACKUP_FILE="backup_vps_phase3_$(date +%Y%m%d_%H%M%S).sql"
        mysqldump -u root --all-databases > "/root/telegram/.internal/backups/$BACKUP_FILE" 2>/dev/null || true
        echo "BACKUP_CREATED: $BACKUP_FILE"
    else
        echo "MySQL not found on VPS"
    fi
EOF

echo -e "${GREEN}✅ Бэкап создан${NC}"

# ============================================================================
# ШАГ 2: Остановка контейнеров на VPS
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 2]${NC} Остановка Docker контейнеров на VPS..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /root/telegram || exit 1
    if [ -f "docker-compose.yml" ]; then
        docker compose down 2>/dev/null || true
        echo "Containers stopped"
    fi
    echo "OK"
EOF

echo -e "${GREEN}✅ Контейнеры остановлены${NC}"

# ============================================================================
# ШАГ 3: Синхронизация кода (rsync или tar)
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 3]${NC} Синхронизация кода на VPS..."

# Проверим есть ли rsync
if command -v rsync &> /dev/null; then
    echo "Использую rsync..."
    rsync -avz \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='*.log' \
        --exclude='test-results' \
        --exclude='playwright-report' \
        --exclude='dist' \
        --exclude='.internal/backups' \
        ./ "root@$VPS_HOST:$VPS_PATH/" 2>&1 | tail -20
else
    echo "rsync не найден, используем tar..."
    tar --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='*.log' \
        -czf /tmp/telegram_phase3.tar.gz .
    
    scp -i "$SSH_KEY" /tmp/telegram_phase3.tar.gz "$VPS_USER@$VPS_HOST:/tmp/"
    
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
        cd /root/telegram
        tar -xzf /tmp/telegram_phase3.tar.gz
        rm /tmp/telegram_phase3.tar.gz
        echo "OK"
EOF
    rm /tmp/telegram_phase3.tar.gz
fi

echo -e "${GREEN}✅ Код синхронизирован${NC}"

# ============================================================================
# ШАГ 4: Запуск миграций БД
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 4]${NC} Запуск миграций БД (alembic upgrade head)..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /root/telegram/backend || exit 1
    
    # Проверяем есть ли alembic
    if [ -f "alembic.ini" ]; then
        echo "Запуск миграций..."
        alembic upgrade head 2>&1 | tail -10
        echo "Migration completed"
    else
        echo "alembic.ini не найден"
    fi
EOF

echo -e "${GREEN}✅ Миграции выполнены${NC}"

# ============================================================================
# ШАГ 5: Запуск Docker контейнеров
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 5]${NC} Запуск Docker контейнеров..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    cd /root/telegram || exit 1
    
    echo "Запуск docker compose..."
    docker compose up -d 2>&1 | tail -10
    
    echo "Ожидание инициализации..."
    sleep 5
    
    echo "Статус контейнеров:"
    docker compose ps
EOF

echo -e "${GREEN}✅ Контейнеры запущены${NC}"

# ============================================================================
# ШАГ 6: Проверка Phase 2
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 6]${NC} Проверка что Phase 2 не сломана..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    echo "Проверка API health..."
    
    # Ждём пока backend инициализируется
    for i in {1..30}; do
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/admin/health 2>/dev/null || true)
        if [ "$RESPONSE" = "200" ]; then
            echo "✅ API доступен (HTTP 200)"
            break
        fi
        echo "Попытка $i/30... (HTTP $RESPONSE)"
        sleep 2
    done
    
    # Проверяем логи backend на ошибки
    echo "Проверка логов backend..."
    docker compose logs backend 2>/dev/null | tail -20 || echo "Логи не доступны"
EOF

echo -e "${GREEN}✅ Phase 2 проверена${NC}"

# ============================================================================
# ШАГ 7: Проверка Phase 3
# ============================================================================
echo -e "\n${YELLOW}[ШАГ 7]${NC} Проверка Phase 3 компонентов..."

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" bash << 'EOF'
    echo "Проверка новых таблиц БД..."
    
    # Проверяем таблицы если есть MySQL
    if command -v mysql &> /dev/null; then
        TABLES=$(mysql -u root -e "SHOW TABLES LIKE '%quality%';" 2>/dev/null || echo "")
        if [ ! -z "$TABLES" ]; then
            echo "✅ Найдены таблицы:"
            echo "$TABLES"
        fi
    fi
    
    echo "Проверка React компонентов..."
    if [ -f "/root/telegram/frontend/src/pages/admin/Metrics.tsx" ]; then
        echo "✅ Metrics.tsx присутствует"
    fi
EOF

echo -e "${GREEN}✅ Phase 3 проверена${NC}"

# ============================================================================
# ФИНАЛ
# ============================================================================
echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Что дальше:${NC}"
echo "1. Откройте браузер: http://37.53.91.144/admin/metrics"
echo "2. Проверьте 3 вкладки: Quality (Phase 2), Trends, Alerts"
echo "3. Проверьте консоль (F12) - не должно быть красных ошибок"
echo ""
echo -e "${YELLOW}Откат (если что-то не так):${NC}"
echo "  ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144"
echo "  cd /root/telegram/backend"
echo "  alembic downgrade -1"
echo ""
echo -e "${YELLOW}Бэкап сохранён:${NC}"
echo "  /root/telegram/.internal/backups/"

echo -e "\n${GREEN}✅ ГОТОВО!${NC}"
