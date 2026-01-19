# Domain Layer

**Architecture Layer**: Domain (Core Business Logic)  
**Dependencies**: NONE ❌ (Pure Python, no frameworks)  
**Purpose**: Изолированная бизнес-логика, независимая от технологий

## 📋 Содержание

- **entities/**: Доменные сущности с identity (User, Stream, Playlist)
- **value_objects/**: Immutable значения (Email, Duration, StreamId)
- **services/**: Доменные сервисы (бизнес-логика, не принадлежащая одной Entity)
- **errors/**: Доменные исключения (ValidationError, BusinessRuleViolationError)
- **events/**: Domain события (UserCreatedEvent, StreamStartedEvent)

## 🚫 Запрещённые Зависимости (FR-007)

Domain layer **НЕ ДОЛЖЕН** импортировать:
```python
# ❌ ЗАПРЕЩЕНО
from fastapi import ...
from sqlalchemy import ...
from celery import ...
from pydantic import BaseModel  # Используй только для Frameworks layer

# ✅ РАЗРЕШЕНО
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from backend.src.shared.kernel import Entity, ValueObject, Result
```

**Проверка**: `import-linter --config backend/pyproject.toml` (SC-005, FR-016)

## 🎯 Design Principles (FR-006)

1. **Encapsulation**: Вся бизнес-логика инкапсулирована в методах
2. **Invariants**: Конструкторы гарантируют валидное состояние
3. **Immutability**: Value Objects неизменяемы (frozen dataclasses)
4. **Pure Functions**: Методы не зависят от внешних состояний

## 📖 Примеры Использования

### Entity Example
```python
from backend.src.shared.kernel.entity import Entity
from backend.src.domain.value_objects.user_id import UserId
from backend.src.domain.value_objects.email import Email

class User(Entity[UserId]):
    def __init__(self, id: UserId, email: Email):
        super().__init__(id)
        self.email = email
    
    def change_email(self, new_email: Email) -> None:
        # Бизнес-правило: валидация в Value Object
        self.email = new_email
```

### Value Object Example
```python
from dataclasses import dataclass
from backend.src.shared.kernel.value_object import ValueObject
from backend.src.domain.errors import ValidationError

@dataclass(frozen=True)
class Email(ValueObject):
    value: str
    
    def __post_init__(self):
        if "@" not in self.value:
            raise ValidationError(f"Invalid email: {self.value}")
```

### Domain Service Example
```python
from backend.src.domain.entities.stream import Stream
from backend.src.domain.value_objects.duration import Duration

class StreamScheduler:
    """Domain Service: координирует несколько Entities."""
    
    @staticmethod
    def calculate_next_stream_time(stream: Stream, duration: Duration) -> datetime:
        # Бизнес-логика, не принадлежащая одной Entity
        return stream.last_broadcast_at + duration.to_timedelta()
```

## ✅ Testing (FR-013, SC-003)

- **Coverage**: ≥90% для domain layer
- **Isolation**: Тесты БЕЗ БД, моков, external dependencies
- **Speed**: Domain tests должны выполняться < 5s (NFR-002)

```bash
# Запуск domain тестов
pytest backend/tests/unit/domain/ -v --cov=backend.src.domain --cov-report=term
```

## 📚 Связанные Документы

- [Clean Architecture Rules](../../specs/025-clean-architecture-rules/spec.md)
- [Application Layer README](../application/README.md)
- [Quickstart Guide](../../specs/025-clean-architecture-rules/quickstart.md)
