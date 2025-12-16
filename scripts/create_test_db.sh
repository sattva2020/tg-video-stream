#!/bin/bash
# Скрипт для создания тестовой базы данных на VPS
# Запускать на VPS сервере

set -e

echo "🔧 Создание тестовой базы данных для integration tests..."

# Переменные
DB_NAME="sattva_test_db"
DB_USER="sattva_test"
DB_PASSWORD="test_password_change_me"  # ВАЖНО: Изменить на безопасный пароль!

# Проверка прав sudo
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Запустите скрипт с sudo"
    exit 1
fi

# Создание пользователя БД
echo "📝 Создание пользователя БД '$DB_USER'..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "Пользователь уже существует"

# Создание базы данных
echo "📝 Создание базы данных '$DB_NAME'..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "База данных уже существует"

# Выдача прав
echo "🔑 Настройка прав доступа..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

# Применение миграций (если они есть)
echo "🔄 Применение миграций..."
cd /root/telegram || exit 1
source venv/bin/activate
cd backend

# Экспорт переменной для Alembic
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"

# Запуск миграций
alembic upgrade head || echo "⚠️  Миграции не применены (возможно их нет)"

echo "✅ Тестовая база данных создана успешно!"
echo ""
echo "📋 Параметры подключения:"
echo "  Host: 10.99.99.6 (internal)"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "⚠️  ВАЖНО: Обновите .env.test с правильным паролем!"
