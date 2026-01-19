# Application Layer

**Architecture Layer**: Application (Use Cases & Orchestration)  
**Dependencies**: Domain ✅, Infrastructure/Frameworks ❌  
**Purpose**: Координация бизнес-логики, не содержит бизнес-правил

## 📋 Содержание

- **use_cases/**: Сценарии использования (CreateUserUseCase, StartStreamUseCase)
- **ports/**: Интерфейсы для Infrastructure (IUserRepository, IStreamGateway)
- **dto/**: Data Transfer Objects для границ слоя

## 🔌 Dependency Inversion (FR-005, FR-009)

Application определяет **интерфейсы-порты**, Infrastructure предоставляет **адаптеры**:

```python
# backend/src/application/ports/i_user_repository.py
from typing import Protocol
from backend.src.domain.entities.user import User
from backend.src.domain.value_objects.user_id import UserId
from backend.src.shared.kernel.result import Result

class IUserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> Result[User, str]:
        """Получить User по ID. Возвращает EntityNotFoundError если не найден."""
        ...
    
    async def save(self, user: User) -> Result[None, str]:
        """Сохранить User. Возвращает ConcurrencyError при version conflict."""
        ...
```

**Infrastructure** реализует:
```python
# backend/src/infrastructure/repositories/sqlalchemy_user_repository.py
from backend.src.application.ports.i_user_repository import IUserRepository

class SqlAlchemyUserRepository(IUserRepository):
    # Конкретная реализация для PostgreSQL
    ...
```

## 🎯 Use Case Pattern (FR-008, US3)

Use Cases **оркестрируют** бизнес-логику, но **не содержат** её:

```python
from backend.src.application.ports.i_user_repository import IUserRepository
from backend.src.domain.value_objects.email import Email
from backend.src.domain.value_objects.user_id import UserId
from backend.src.domain.entities.user import User
from backend.src.shared.kernel.result import Result

class CreateUserUseCase:
    def __init__(self, user_repository: IUserRepository):
        self._repository = user_repository  # Dependency Injection
    
    async def execute(self, email_str: str) -> Result[User, str]:
        # 1. Валидация Value Object
        try:
            email = Email(email_str)
        except ValidationError as e:
            return Result.failure(str(e))
        
        # 2. Создание Entity (бизнес-логика в Domain)
        user = User(id=UserId.generate(), email=email)
        
        # 3. Persistence через порт
        save_result = await self._repository.save(user)
        if save_result.is_failure:
            return Result.failure(save_result.error)
        
        return Result.success(user)
```

## 🚫 Запрещённые Зависимости (FR-005)

Application **НЕ ДОЛЖЕН** импортировать:
```python
# ❌ ЗАПРЕЩЕНО
from backend.src.infrastructure import ...
from backend.src.frameworks import ...
from sqlalchemy import ...  # Infrastructure concern
from fastapi import ...     # Framework concern

# ✅ РАЗРЕШЕНО
from backend.src.domain import ...
from backend.src.application.ports import ...  # Свои интерфейсы
from backend.src.shared.kernel import Result, DomainEvent
```

**Проверка**: `import-linter --config backend/pyproject.toml` (SC-005)

## 📦 DTO Usage (US5)

DTO для **входа/выхода** Use Cases (не для domain logic):

```python
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    email: str

@dataclass
class CreateUserResponse:
    user_id: str
    email: str
    created_at: str
```

**Mapping**:
```python
# Use Case → DTO (для Frameworks layer)
def to_response(user: User) -> CreateUserResponse:
    return CreateUserResponse(
        user_id=str(user.id.value),
        email=user.email.value,
        created_at=user.created_at.isoformat()
    )
```

## ✅ Testing (FR-014, SC-004)

- **Coverage**: ≥80% для application layer
- **Mocking**: Используй моки репозиториев (IRepository)
- **Integration**: Тесты Use Cases с fake repositories

```bash
# Unit тесты Use Cases
pytest backend/tests/unit/application/ -v --cov=backend.src.application

# Integration тесты (с моками)
pytest backend/tests/integration/application/ -v
```

### Test Example
```python
import pytest
from backend.src.application.use_cases.create_user import CreateUserUseCase
from tests.fakes.fake_user_repository import FakeUserRepository

@pytest.mark.asyncio
async def test_create_user_success():
    # Arrange
    repository = FakeUserRepository()
    use_case = CreateUserUseCase(repository)
    
    # Act
    result = await use_case.execute("user@example.com")
    
    # Assert
    assert result.is_success
    assert result.value.email.value == "user@example.com"
```

## 📚 Связанные Документы

- [Domain Layer README](../domain/README.md)
- [Infrastructure Layer README](../infrastructure/README.md)
- [Port Interfaces Design](../../specs/025-clean-architecture-rules/contracts/)
