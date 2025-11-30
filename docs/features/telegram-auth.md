# Авторизация через Telegram Login Widget

> **Спецификация**: `specs/013-telegram-login/`
> **Статус**: Реализовано
> **Версия**: 1.0.0

## Обзор

Telegram Login Widget — третий способ авторизации в приложении (наряду с Google OAuth и Email/Password).
Позволяет пользователям входить через официальный Telegram Login Widget без необходимости
запоминать пароли.

## Функциональность

### User Stories

| ID | Описание | Приоритет | Статус |
|----|----------|-----------|--------|
| US1 | Вход через Telegram | P1 | ✅ |
| US2 | Автоматическая регистрация | P1 | ✅ |
| US3 | Выход из системы | P2 | ✅ |
| US4 | Связывание/отвязка Telegram | P2 | ✅ |

### Endpoints API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/auth/telegram-widget` | Авторизация/регистрация через виджет |
| POST | `/api/auth/telegram-widget/link` | Привязка Telegram к существующему аккаунту |
| DELETE | `/api/auth/telegram-widget/unlink` | Отвязка Telegram от аккаунта |

## Архитектура

### Компоненты

```
┌────────────────────┐    ┌──────────────────────┐
│  TelegramLoginButton│───▶│ Telegram Login Widget │
│  (React Component) │    │     (External)        │
└─────────┬──────────┘    └───────────┬───────────┘
          │                           │
          │ callback(auth_data)       │
          ▼                           │
┌─────────────────────┐               │
│  useTelegramAuth    │◀──────────────┘
│  (React Hook)       │
└─────────┬───────────┘
          │ POST /api/auth/telegram-widget
          ▼
┌──────────────────────────────────────┐
│     telegram_widget.py (FastAPI)     │
├──────────────────────────────────────┤
│ 1. Верификация подписи HMAC-SHA256   │
│ 2. Проверка auth_date (replay attack)│
│ 3. Get/Create User                   │
│ 4. Генерация JWT                     │
│ 5. Установка HttpOnly Cookie         │
└──────────────────────────────────────┘
```

### Безопасность

#### Верификация подписи

```python
# 1. Формируем data-check-string
data_check_string = '\n'.join(
    f'{k}={v}' for k, v in sorted(check_data.items())
)

# 2. Вычисляем секретный ключ = SHA256(bot_token)
secret_key = hashlib.sha256(bot_token.encode()).digest()

# 3. Вычисляем HMAC-SHA256
calculated_hash = hmac.new(
    secret_key,
    data_check_string.encode(),
    hashlib.sha256
).hexdigest()

# 4. Сравниваем с полученным hash (timing-safe)
hmac.compare_digest(calculated_hash, received_hash)
```

#### Защита от атак

| Атака | Защита |
|-------|--------|
| Replay Attack | Проверка auth_date ≤ 5 минут |
| Brute Force | Rate Limiting: 5 запросов/час/IP |
| Bot Registration | Cloudflare Turnstile CAPTCHA |
| CSRF | SameSite=Lax cookies |
| Token Theft | HttpOnly + Secure cookies |

### Rate Limiting

```
5 запросов в час на IP адрес

После 3 неудачных попыток за 10 минут → требуется CAPTCHA
```

## Настройка

### Переменные окружения

```env
# Telegram Bot (создать через @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username

# Настройки безопасности
TELEGRAM_AUTH_MAX_AGE=300  # 5 минут
TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR=5
TELEGRAM_AUTH_CAPTCHA_THRESHOLD=3

# Cloudflare Turnstile CAPTCHA
TURNSTILE_SITE_KEY=your_site_key
TURNSTILE_SECRET_KEY=your_secret_key
```

### Настройка Telegram Bot

1. Создать бота через [@BotFather](https://t.me/BotFather)
2. Выполнить команду `/setdomain`
3. Указать домен приложения (например, `app.example.com`)
4. Скопировать токен бота в `TELEGRAM_BOT_TOKEN`
5. Скопировать username бота в `TELEGRAM_BOT_USERNAME`

## Использование

### Frontend

```tsx
import TelegramLoginButton from '@/components/TelegramLoginButton';
import { useTelegramAuth } from '@/hooks/useTelegramAuth';

function LoginPage() {
  const { handleTelegramAuth, isLoading, error } = useTelegramAuth();

  return (
    <TelegramLoginButton
      onAuth={handleTelegramAuth}
      buttonSize="large"
      showUserPhoto={true}
    />
  );
}
```

### Страница настроек (link/unlink)

Страница `/settings` позволяет:
- Привязать Telegram к существующему аккаунту
- Отвязать Telegram (если есть альтернативный способ входа)

## Модель данных

### Расширение User

```python
class User(Base):
    # ... existing fields ...
    
    # Telegram Login Widget
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    telegram_username = Column(String(255), nullable=True)
    
    def has_alternative_auth(self) -> bool:
        """Есть ли альтернативный способ входа (для unlink)."""
        return bool(self.google_id) or bool(self.email and self.hashed_password)
```

### Миграция

```bash
alembic upgrade head
```

## Логирование

Все события Telegram аутентификации логируются через структурированный логгер:

```
event=telegram_login_success | message=... | telegram_id=123 | user_id=uuid | ip_address=1.2.3.4
event=telegram_registration_success | message=... | telegram_id=123 | status=pending
event=telegram_signature_invalid | message=... | telegram_id=123 | ip_address=1.2.3.4
event=telegram_rate_limit_hit | message=... | ip_address=1.2.3.4
```

## Тестирование

### Backend тесты

```bash
cd backend
pytest tests/test_telegram_widget_*.py -v
```

### Frontend тесты

```bash
cd frontend
npm run test -- --grep "Telegram"
```

## Известные ограничения

1. **Telegram-only пользователи**: email = NULL, не могут восстановить пароль
2. **Без email**: нельзя отправить уведомления на почту
3. **Отвязка**: требует альтернативного способа входа

## См. также

- [Спецификация](../../specs/013-telegram-login/spec.md)
- [План реализации](../../specs/013-telegram-login/plan.md)
- [Telegram Login Widget Docs](https://core.telegram.org/widgets/login)
