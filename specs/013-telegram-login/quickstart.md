# Quickstart: Telegram Login Integration

## Обзор

Данный документ описывает шаги для быстрого старта интеграции Telegram Login Widget.

## Предварительные требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Telegram аккаунт для создания бота

---

## Шаг 1: Создание Telegram Bot

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота (например: `Sattva Auth Bot`)
4. Введите username бота (например: `sattva_auth_bot`)
5. Сохраните полученный **Bot Token**

```
Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

## Шаг 2: Настройка домена для Login Widget

1. В чате с @BotFather отправьте `/setdomain`
2. Выберите вашего бота
3. Укажите домен вашего приложения:
   - Production: `sattva.example.com`
   - Development: `localhost` (работает только в Telegram Desktop)

> ⚠️ **Важно**: Telegram Login Widget НЕ работает с `localhost` в мобильном приложении.
> Для разработки используйте ngrok или аналогичный туннель.

## Шаг 3: Переменные окружения

Добавьте в `template.env`:

```env
# Telegram Bot для Login Widget
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username

# Настройки безопасности
TELEGRAM_AUTH_MAX_AGE=300
TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR=5
TELEGRAM_AUTH_CAPTCHA_THRESHOLD=3
```

## Шаг 4: Миграция базы данных

```bash
cd backend
alembic revision --autogenerate -m "add telegram auth fields"
alembic upgrade head
```

## Шаг 5: Проверка интеграции

### Backend проверка:

```bash
# Запуск тестов
cd backend
pytest tests/test_telegram_auth.py -v
```

### Frontend проверка:

1. Запустите dev-сервер: `npm run dev`
2. Откройте страницу логина
3. Кнопка "Войти через Telegram" должна отображаться
4. При клике — открывается popup с авторизацией Telegram

---

## Тестирование в development

### Вариант 1: Через ngrok (рекомендуется)

```bash
# Установите ngrok
ngrok http 3000

# Используйте полученный URL (например: https://abc123.ngrok.io)
# Добавьте его в настройки бота через @BotFather
```

### Вариант 2: Telegram Desktop

Telegram Desktop поддерживает `localhost`, но мобильные приложения — нет.

---

## Проверка подписи (серверная валидация)

```python
import hashlib
import hmac

def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Верифицирует подпись данных от Telegram Login Widget."""
    check_hash = data.pop('hash', None)
    if not check_hash:
        return False
    
    # Сортируем и формируем строку
    data_check_string = '\n'.join(
        f'{key}={data[key]}' 
        for key in sorted(data.keys())
    )
    
    # Создаём секретный ключ
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Вычисляем HMAC-SHA256
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_hash, check_hash)
```

---

## Структура файлов после реализации

```
backend/
├── src/
│   ├── api/
│   │   └── auth/
│   │       └── telegram.py      # Endpoints для Telegram auth
│   ├── services/
│   │   └── telegram_auth_service.py  # Бизнес-логика
│   └── schemas/
│       └── telegram_auth.py     # Pydantic schemas

frontend/
├── src/
│   ├── components/
│   │   └── TelegramLoginButton.tsx  # Компонент кнопки
│   └── services/
│       └── telegramAuth.ts      # API клиент
```

---

## Следующие шаги

1. ✅ Создать бота через @BotFather
2. ✅ Настроить домен
3. ✅ Добавить переменные окружения
4. ⏳ Реализовать backend endpoints
5. ⏳ Реализовать frontend компонент
6. ⏳ Добавить тесты
7. ⏳ Провести интеграционное тестирование

---

## Полезные ссылки

- [Telegram Login Widget Documentation](https://core.telegram.org/widgets/login)
- [Bot API: Authorizing Requests](https://core.telegram.org/bots/api#authorizing-requests)
- [BotFather Commands](https://core.telegram.org/bots/features#botfather)
