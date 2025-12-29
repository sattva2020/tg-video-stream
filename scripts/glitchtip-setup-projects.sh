#!/bin/bash

# Скрипт для создания организации и проектов в Glitchtip
# Использование: ./scripts/glitchtip-setup-projects.sh

set -e

GLITCHTIP_URL="http://localhost:8080"
ADMIN_EMAIL="${GLITCHTIP_ADMIN_EMAIL:-admin@sattva.tv}"
ADMIN_PASSWORD="${GLITCHTIP_ADMIN_PASSWORD:-admin123}"

ORG_NAME="Sattva TV"
BACKEND_PROJECT="sattva-tv-backend"
FRONTEND_PROJECT="sattva-tv-frontend"

echo "🚀 Настройка проектов в Glitchtip..."
echo ""

# Функция для получения auth token
get_auth_token() {
    echo "📝 Получение auth token..."
    
    # Логин и получение session cookie
    LOGIN_RESPONSE=$(curl -s -c /tmp/glitchtip-cookies.txt -X POST \
        "${GLITCHTIP_URL}/rest-auth/login/" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${ADMIN_EMAIL}\", \"password\": \"${ADMIN_PASSWORD}\"}")
    
    # Извлечение токена из ответа
    AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"key":"[^"]*' | sed 's/"key":"//')
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo "❌ Ошибка: не удалось получить auth token"
        echo "Response: $LOGIN_RESPONSE"
        exit 1
    fi
    
    echo "✅ Auth token получен"
    echo "$AUTH_TOKEN"
}

# Функция для создания организации
create_organization() {
    local ORG_SLUG=$(echo "$ORG_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    
    echo "🏢 Создание организации: $ORG_NAME (slug: $ORG_SLUG)..."
    
    ORG_RESPONSE=$(curl -s -b /tmp/glitchtip-cookies.txt -X POST \
        "${GLITCHTIP_URL}/api/0/organizations/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "{\"name\": \"${ORG_NAME}\", \"slug\": \"${ORG_SLUG}\"}")
    
    # Проверка на ошибку "already exists"
    if echo "$ORG_RESPONSE" | grep -q "slug.*already exists"; then
        echo "ℹ️  Организация уже существует, используем существующую"
        
        # Получение списка организаций
        ORGS_LIST=$(curl -s -b /tmp/glitchtip-cookies.txt \
            "${GLITCHTIP_URL}/api/0/organizations/" \
            -H "Authorization: Bearer ${AUTH_TOKEN}")
        
        ORG_SLUG=$(echo "$ORGS_LIST" | grep -o "\"slug\":\"[^\"]*" | head -1 | sed 's/"slug":"//')
    fi
    
    echo "✅ Организация готова: $ORG_SLUG"
    echo "$ORG_SLUG"
}

# Функция для создания проекта
create_project() {
    local ORG_SLUG=$1
    local PROJECT_NAME=$2
    local PROJECT_SLUG=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')
    local PLATFORM=$3
    
    echo "📦 Создание проекта: $PROJECT_NAME (platform: $PLATFORM)..."
    
    PROJECT_RESPONSE=$(curl -s -b /tmp/glitchtip-cookies.txt -X POST \
        "${GLITCHTIP_URL}/api/0/teams/${ORG_SLUG}/${ORG_SLUG}/projects/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "{\"name\": \"${PROJECT_NAME}\", \"slug\": \"${PROJECT_SLUG}\", \"platform\": \"${PLATFORM}\"}")
    
    if echo "$PROJECT_RESPONSE" | grep -q "slug.*already exists"; then
        echo "ℹ️  Проект уже существует"
    else
        echo "✅ Проект создан"
    fi
    
    # Получение DSN
    sleep 2
    DSN_RESPONSE=$(curl -s -b /tmp/glitchtip-cookies.txt \
        "${GLITCHTIP_URL}/api/0/projects/${ORG_SLUG}/${PROJECT_SLUG}/keys/" \
        -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    DSN=$(echo "$DSN_RESPONSE" | grep -o '"dsn":{"public":"[^"]*' | sed 's/"dsn":{"public":"//')
    
    if [ -z "$DSN" ]; then
        echo "⚠️  DSN не найден, попробуйте вручную через UI"
    else
        echo "🔑 DSN: $DSN"
    fi
    
    echo "$DSN"
}

# Основная логика
echo "1️⃣  Аутентификация..."
AUTH_TOKEN=$(get_auth_token)

echo ""
echo "2️⃣  Организация..."
ORG_SLUG=$(create_organization)

echo ""
echo "3️⃣  Backend проект..."
BACKEND_DSN=$(create_project "$ORG_SLUG" "$BACKEND_PROJECT" "python-fastapi")

echo ""
echo "4️⃣  Frontend проект..."
FRONTEND_DSN=$(create_project "$ORG_SLUG" "$FRONTEND_PROJECT" "react")

echo ""
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
echo "✅ Настройка завершена!"
echo ""
echo "🌐 Glitchtip UI: $GLITCHTIP_URL"
echo "📧 Email: $ADMIN_EMAIL"
echo "🔑 Password: $ADMIN_PASSWORD"
echo ""
echo "📦 Backend Project: $BACKEND_PROJECT"
echo "   DSN: $BACKEND_DSN"
echo ""
echo "📦 Frontend Project: $FRONTEND_PROJECT"
echo "   DSN: $FRONTEND_DSN"
echo ""
echo "📝 Добавьте DSN в .env файлы:"
echo "   Backend: SENTRY_DSN=$BACKEND_DSN"
echo "   Frontend: VITE_SENTRY_DSN=$FRONTEND_DSN"
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="

# Сохранение DSN в файл для автоматизации
cat > /tmp/glitchtip-dsn.env << EOF
# Glitchtip DSN (generated: $(date))
SENTRY_DSN=$BACKEND_DSN
VITE_SENTRY_DSN=$FRONTEND_DSN
EOF

echo ""
echo "💾 DSN сохранены в: /tmp/glitchtip-dsn.env"
