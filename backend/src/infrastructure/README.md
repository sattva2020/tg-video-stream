# Infrastructure Layer

**Architecture Layer**: Infrastructure (External Systems Integration)  
**Dependencies**: Domain ✅, Application ✅, Frameworks ❌  
**Purpose**: Реализация технических деталей (БД, внешние API, файловая система)

## 📋 Содержание

- **repositories/**: Реализация IRepository портов (SQLAlchemy, Redis)
- **gateways/**: Реализация внешних сервисов (Telegram API, Email)
- **persistence/**: ORM models, migrations, database connection

## 🔌 Adapter Pattern (FR-009)

Infrastructure **реализует порты** из Application layer:

```python
# backend/src/infrastructure/repositories/sqlalchemy_user_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.ports.i_user_repository import IUserRepository
from backend.src.domain.entities.user import User
from backend.src.domain.value_objects.user_id import UserId
from backend.src.domain.errors import EntityNotFoundError
from backend.src.shared.kernel.result import Result

class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_id(self, user_id: UserId) -> Result[User, str]:
        # ORM query
        orm_user = await self._session.get(UserORM, str(user_id.value))
        if not orm_user:
            return Result.failure(f"User {user_id.value} not found")
        
        # ORM → Domain Entity mapping
        domain_user = self._to_domain(orm_user)
        return Result.success(domain_user)
    
    async def save(self, user: User) -> Result[None, str]:
        orm_user = self._to_orm(user)  # Domain → ORM mapping
        self._session.add(orm_user)
        try:
            await self._session.commit()
            return Result.success(None)
        except Exception as e:
            await self._session.rollback()
            return Result.failure(str(e))
```

## 🗺️ ORM Mapping (FR-010)

**ORM Models** (persistence layer) отделены от **Domain Entities**:

### ORM Model
```python
# backend/src/infrastructure/persistence/models/user_orm.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserORM(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
```

### Mapping Functions
```python
def _to_domain(self, orm: UserORM) -> User:
    """ORM → Domain Entity."""
    return User(
        id=UserId(orm.id),
        email=Email(orm.email),
        created_at=orm.created_at
    )

def _to_orm(self, entity: User) -> UserORM:
    """Domain Entity → ORM."""
    return UserORM(
        id=str(entity.id.value),
        email=entity.email.value,
        created_at=entity.created_at
    )
```

**Performance** (NFR-003): Mapping overhead < 1ms per object.

## 🚫 Запрещённые Зависимости (FR-005)

Infrastructure **НЕ ДОЛЖЕН** импортировать:
```python
# ❌ ЗАПРЕЩЕНО
from backend.src.frameworks import ...  # API routes, CLI commands

# ✅ РАЗРЕШЕНО
from backend.src.domain import ...
from backend.src.application.ports import ...
from sqlalchemy import ...
from redis import ...
from httpx import ...  # Для внешних API
```

**Проверка**: `import-linter --config backend/pyproject.toml`

## 🧪 Testing (FR-015)

- **Coverage**: ≥70% для infrastructure layer
- **Contract Tests**: Проверка соответствия портам
- **Integration Tests**: С реальной БД (testcontainers)

```bash
# Contract tests (репозиторий реализует IRepository)
pytest backend/tests/contract/infrastructure/ -v

# Integration tests (с PostgreSQL testcontainer)
pytest backend/tests/integration/infrastructure/ -v
```

### Contract Test Example
```python
import pytest
from backend.src.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from backend.src.application.ports.i_user_repository import IUserRepository

def test_repository_implements_port():
    """Проверка: SqlAlchemyUserRepository реализует IUserRepository."""
    assert isinstance(SqlAlchemyUserRepository, type)
    # Protocol checking в runtime
    repo = SqlAlchemyUserRepository(session=None)  # type: ignore
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "save")
```

## 📦 External Services (Gateways)

Gateways инкапсулируют **внешние API**:

```python
# backend/src/infrastructure/gateways/telegram_gateway.py
from backend.src.application.ports.i_telegram_gateway import ITelegramGateway
from backend.src.shared.kernel.result import Result

class TelegramGateway(ITelegramGateway):
    def __init__(self, api_client: TelegramClient):
        self._client = api_client
    
    async def send_message(self, chat_id: str, text: str) -> Result[None, str]:
        try:
            await self._client.send_message(chat_id, text)
            return Result.success(None)
        except TelegramAPIError as e:
            # External exception → Result для Domain compatibility
            return Result.failure(f"Telegram API error: {e}")
```

## 🔐 Secrets Management (NFR-009)

Secrets изолированы в Infrastructure, **НЕ в Domain**:

```python
# backend/src/infrastructure/config.py
from pydantic import BaseSettings

class DatabaseConfig(BaseSettings):
    db_host: str
    db_password: str  # Secret из env variables
    
    class Config:
        env_file = ".env"
```

## 📚 Связанные Документы

- [Application Layer README](../application/README.md)
- [ORM Mapping Strategy](../../specs/025-clean-architecture-rules/research.md#td3-orm-mapping)
- [Frameworks Layer README](../frameworks/README.md)
