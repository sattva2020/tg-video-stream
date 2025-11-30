# Data Model: Авторизация через Telegram

**Feature**: 013-telegram-login  
**Date**: 2025-11-30

## 1. Изменения в существующих сущностях

### 1.1 User (расширение)

**Файл**: `backend/src/models/user.py`

| Атрибут | Тип | Nullable | Unique | Index | Описание |
|---------|-----|----------|--------|-------|----------|
| `telegram_id` | BigInteger | Yes | Yes | Yes | Уникальный ID пользователя в Telegram |
| `telegram_username` | String(255) | Yes | No | No | Username в Telegram (без @) |

**SQL миграция**:
```sql
ALTER TABLE users ADD COLUMN telegram_id BIGINT UNIQUE;
ALTER TABLE users ADD COLUMN telegram_username VARCHAR(255);
CREATE UNIQUE INDEX ix_users_telegram_id ON users(telegram_id);
```

### 1.2 Обновлённая модель User

```python
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # OAuth providers
    google_id = Column(String, unique=True, index=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)  # NEW
    telegram_username = Column(String(255), nullable=True)  # NEW
    
    # Common fields
    email = Column(String, unique=True, index=True, nullable=True)  # nullable для Telegram-only
    full_name = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    
    # Access control
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## 2. Новые Pydantic схемы

### 2.1 TelegramAuthRequest

```python
from pydantic import BaseModel, Field

class TelegramAuthRequest(BaseModel):
    """Данные от Telegram Login Widget"""
    id: int = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="Имя пользователя")
    last_name: str | None = Field(None, description="Фамилия пользователя")
    username: str | None = Field(None, description="Username в Telegram")
    photo_url: str | None = Field(None, description="URL аватара")
    auth_date: int = Field(..., description="Unix timestamp авторизации")
    hash: str = Field(..., description="Подпись для верификации")
```

### 2.2 TelegramAuthResponse

```python
class TelegramAuthResponse(BaseModel):
    """Ответ после успешной авторизации"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False
```

### 2.3 TelegramLinkRequest

```python
class TelegramLinkRequest(BaseModel):
    """Запрос на связывание Telegram с существующим аккаунтом"""
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str
```

### 2.4 TelegramUnlinkResponse

```python
class TelegramUnlinkResponse(BaseModel):
    """Ответ после отвязки Telegram"""
    success: bool
    message: str
```

## 3. Ограничения и валидация

### 3.1 Бизнес-правила

| Правило | Описание |
|---------|----------|
| BR-001 | `telegram_id` должен быть уникальным в системе |
| BR-002 | Один Telegram аккаунт может быть привязан только к одному User |
| BR-003 | Отвязка Telegram разрешена только если есть `google_id` ИЛИ (`email` + `hashed_password`) |
| BR-004 | `email` может быть NULL для пользователей, зарегистрированных только через Telegram |
| BR-005 | Новые пользователи через Telegram получают статус `pending` |

### 3.2 Валидация auth_date

```python
MAX_AUTH_AGE_SECONDS = 300  # 5 минут

def validate_auth_date(auth_date: int) -> bool:
    """Проверяет, что auth_date не старше MAX_AUTH_AGE_SECONDS"""
    return time.time() - auth_date <= MAX_AUTH_AGE_SECONDS
```

## 4. Индексы

| Таблица | Индекс | Колонки | Уникальный |
|---------|--------|---------|------------|
| users | ix_users_telegram_id | telegram_id | Yes |

## 5. Диаграмма связей (ER)

```
┌─────────────────────────────────────────────────────────────┐
│                           User                               │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (PK)                                               │
│ google_id: String (unique, nullable) ──────────┐            │
│ telegram_id: BigInt (unique, nullable) ────────┤ Auth       │
│ telegram_username: String (nullable)           │ Providers  │
│ email: String (unique, nullable) ──────────────┤            │
│ hashed_password: String (nullable) ────────────┘            │
│ full_name: String (nullable)                                │
│ profile_picture_url: String (nullable)                      │
│ role: Enum (user, admin)                                    │
│ status: Enum (pending, approved, rejected)                  │
│ email_verified: Boolean                                     │
│ created_at: DateTime                                        │
│ updated_at: DateTime                                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. Миграция данных

### 6.1 Стратегия миграции
- Добавление колонок `telegram_id` и `telegram_username` не требует миграции данных
- Все существующие пользователи будут иметь `telegram_id = NULL`
- Они смогут привязать Telegram позже через настройки аккаунта

### 6.2 Alembic миграция

```python
"""add telegram auth fields

Revision ID: xyz123
Revises: previous_revision
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa

revision = 'xyz123'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('telegram_username', sa.String(255), nullable=True))
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)

def downgrade():
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_column('users', 'telegram_username')
    op.drop_column('users', 'telegram_id')
```
