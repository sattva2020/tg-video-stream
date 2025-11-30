# Research: Авторизация через Telegram Login Widget

**Feature**: 013-telegram-login  
**Date**: 2025-11-30  
**Status**: Complete

## 1. Telegram Login Widget — Обзор

### 1.1 Что это?
Telegram Login Widget — официальный способ аутентификации пользователей через Telegram. Пользователь подтверждает вход через приложение Telegram, и данные профиля передаются на сайт.

### 1.2 Официальная документация
- [Telegram Login Widget](https://core.telegram.org/widgets/login)
- [Проверка авторизации](https://core.telegram.org/widgets/login#checking-authorization)

### 1.3 Данные, получаемые от Telegram
```json
{
  "id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "photo_url": "https://t.me/i/userpic/320/...",
  "auth_date": 1732960800,
  "hash": "abc123..."
}
```

**Важно**: 
- `username` опционален (может быть null)
- `last_name` опционален
- `photo_url` опционален
- `auth_date` — Unix timestamp момента авторизации

## 2. Безопасность — Верификация подписи

### 2.1 Алгоритм проверки (согласно документации)
1. Собрать все поля (кроме `hash`) в формате `key=value`, отсортировать по ключу, соединить через `\n`
2. Вычислить SHA256 от Bot Token
3. Вычислить HMAC-SHA256 от data-check-string используя SHA256(bot_token) как ключ
4. Сравнить с полученным `hash`

### 2.2 Пример реализации на Python
```python
import hashlib
import hmac
import time

def verify_telegram_auth(data: dict, bot_token: str, max_age: int = 300) -> bool:
    """
    Верифицирует данные от Telegram Login Widget.
    
    Args:
        data: Данные от Telegram (включая hash)
        bot_token: Bot Token для проверки подписи
        max_age: Максимальный возраст auth_date в секундах (по умолчанию 5 минут)
    
    Returns:
        True если данные валидны, иначе False
    """
    # Проверка auth_date
    auth_date = int(data.get('auth_date', 0))
    if time.time() - auth_date > max_age:
        return False
    
    # Получаем hash и удаляем его из данных для проверки
    received_hash = data.get('hash')
    if not received_hash:
        return False
    
    # Формируем data-check-string
    check_data = {k: v for k, v in data.items() if k != 'hash'}
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(check_data.items()))
    
    # Вычисляем секретный ключ
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Вычисляем HMAC
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, received_hash)
```

### 2.3 Решение: auth_date проверка
- **Выбрано**: 5 минут (300 секунд)
- **Обоснование**: Баланс между безопасностью (защита от replay-атак) и UX (достаточно времени для обработки)
- **Альтернативы отклонены**: 
  - 1 час — слишком рискованно для replay-атак
  - 24 часа — неприемлемо с точки зрения безопасности

## 3. Интеграция с существующей архитектурой

### 3.1 Модель User — Расширение
Текущая модель `User` в `backend/src/models/user.py`:
- `google_id` — уже существует (nullable)
- Нужно добавить: `telegram_id`, `telegram_username`

### 3.2 Совместимость с существующими методами входа
| Метод | Поле идентификации | Статус |
|-------|-------------------|--------|
| Google OAuth | `google_id` | Существует |
| Email/Password | `email` + `hashed_password` | Существует |
| Telegram | `telegram_id` | **Добавить** |

### 3.3 Конфликты аккаунтов
- Если `telegram_id` уже привязан → использовать существующий аккаунт
- Если email совпадает с существующим → предложить связать аккаунты
- Если `telegram_id` не найден и email не совпадает → создать новый аккаунт

## 4. Фронтенд — Telegram Login Widget

### 4.1 Варианты интеграции
1. **Iframe Widget** — готовый виджет от Telegram
2. **JavaScript callback** — кастомная кнопка с обработчиком

### 4.2 Решение: JavaScript callback (popup mode)
```html
<script async src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="YOUR_BOT_NAME"
        data-size="large"
        data-auth-url="/auth/telegram/callback"
        data-request-access="write">
</script>
```

Или программно через React:
```tsx
// TelegramLoginButton.tsx
useEffect(() => {
  const script = document.createElement('script');
  script.src = 'https://telegram.org/js/telegram-widget.js?22';
  script.setAttribute('data-telegram-login', 'BOT_NAME');
  script.setAttribute('data-size', 'large');
  script.setAttribute('data-onauth', 'onTelegramAuth(user)');
  script.async = true;
  ref.current?.appendChild(script);
}, []);
```

### 4.3 Решение: Popup mode
- **Выбрано**: Popup (всплывающее окно)
- **Обоснование**: Пользователь остаётся на странице, лучший UX
- **Альтернатива отклонена**: Redirect — теряется состояние страницы

## 5. Rate Limiting и защита от атак

### 5.1 Выбранная стратегия
1. **Rate limiting по IP**: максимум 5 попыток/час
2. **CAPTCHA**: показывать после 3 попыток за 10 минут

### 5.2 Реализация
- Использовать `slowapi` для FastAPI
- Redis для хранения счётчиков (или in-memory для простоты)
- hCaptcha или Google reCAPTCHA v3

### 5.3 Логирование
Все подозрительные попытки логировать с:
- IP адрес
- User-Agent
- Timestamp
- Причина блокировки

## 6. Переменные окружения

### 6.1 Новые переменные для template.env
```env
# Telegram Login Widget
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_AUTH_MAX_AGE=300

# Rate limiting
TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR=5
TELEGRAM_AUTH_CAPTCHA_THRESHOLD=3
```

## 7. API Endpoints

### 7.1 Новые эндпоинты
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/auth/telegram` | Обработка данных от Telegram Login Widget |
| POST | `/api/auth/telegram/link` | Связывание Telegram с существующим аккаунтом |
| DELETE | `/api/auth/telegram/unlink` | Отвязка Telegram от аккаунта |

### 7.2 Схема запроса `/api/auth/telegram`
```json
{
  "id": 123456789,
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "photo_url": "https://...",
  "auth_date": 1732960800,
  "hash": "abc123..."
}
```

### 7.3 Схема ответа (успех)
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "full_name": "John Doe",
    "email": null,
    "telegram_username": "johndoe",
    "status": "pending"
  }
}
```

## 8. Миграция базы данных

### 8.1 Alembic миграция
```python
# Добавить поля telegram_id и telegram_username в таблицу users
op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
op.add_column('users', sa.Column('telegram_username', sa.String(), nullable=True))
op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)
```

## 9. Тестирование

### 9.1 Unit тесты
- Верификация подписи Telegram (валидная/невалидная)
- Проверка auth_date (свежий/устаревший)
- Создание нового пользователя
- Вход существующего пользователя
- Связывание аккаунтов
- Отвязка аккаунтов

### 9.2 Integration тесты
- Полный flow авторизации через API
- Rate limiting
- CAPTCHA trigger

### 9.3 E2E тесты (Playwright)
- Клик по кнопке "Войти через Telegram"
- Проверка редиректа после успешного входа
- Отображение ошибок

## 10. Выводы

### 10.1 Решения принятые
1. Telegram Login Widget с popup mode
2. Верификация подписи на бэкенде
3. auth_date проверка: 5 минут
4. Роль "pending" для новых пользователей
5. Rate limiting + CAPTCHA для защиты
6. Множественные сессии разрешены
7. Отвязка только при наличии альтернативного входа

### 10.2 Зависимости
- Telegram Bot Token (нужно создать бота через @BotFather)
- Настройка домена в боте для Login Widget
- slowapi для rate limiting
- hCaptcha/reCAPTCHA для защиты от ботов
