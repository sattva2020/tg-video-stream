#!/bin/bash

# Скрипт для создания superuser в Glitchtip
# Использование: ./scripts/glitchtip-create-superuser.sh

set -e

ADMIN_EMAIL="${GLITCHTIP_ADMIN_EMAIL:-admin@sattva.tv}"
ADMIN_PASSWORD="${GLITCHTIP_ADMIN_PASSWORD:-admin123}"
ADMIN_NAME="${GLITCHTIP_ADMIN_NAME:-Admin}"

echo "🚀 Создание superuser в Glitchtip..."
echo "Email: $ADMIN_EMAIL"
echo "Name: $ADMIN_NAME"
echo ""

# Создание superuser через Django management command
docker compose -f docker-compose.glitchtip.yml exec -T glitchtip-web python3 manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()

# Проверка существования
if User.objects.filter(email='$ADMIN_EMAIL').exists():
    print('❌ User with email $ADMIN_EMAIL already exists')
else:
    # Создание superuser (в Glitchtip username = email)
    user = User.objects.create_superuser(
        email='$ADMIN_EMAIL',
        password='$ADMIN_PASSWORD'
    )
    user.name = '$ADMIN_NAME'
    user.save()
    print('✅ Superuser created successfully!')
    print('Email: $ADMIN_EMAIL')
    print('Password: $ADMIN_PASSWORD')
    print('Access: http://localhost:8080')
EOF

echo ""
echo "✅ Done!"
echo ""
echo "🌐 Glitchtip UI: http://localhost:8080"
echo "📧 Email: $ADMIN_EMAIL"
echo "🔑 Password: $ADMIN_PASSWORD"
