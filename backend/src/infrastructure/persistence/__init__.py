"""
Persistence Layer - работа с хранилищем данных.

**Architecture Layer**: Infrastructure
**Purpose**: Реализация репозиториев и маппинг Entity ↔ ORM

**Structure**:
- mappers/ - Конвертация Entity ↔ ORM Model (UserMapper, StreamMapper, etc.)
- repositories/ - Реализации IRepository интерфейсов (SqlAlchemyUserRepository, etc.)
- repositories/in_memory/ - In-memory реализации для тестирования

**Dependencies**:
- Domain Layer: Entities, Value Objects, Repository Interfaces (Ports)
- SQLAlchemy: ORM models, Session
"""
