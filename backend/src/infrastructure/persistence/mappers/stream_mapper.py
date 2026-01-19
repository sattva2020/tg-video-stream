"""
StreamMapper - маппинг между Stream Entity и Stream ORM Model (T054).

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Преобразование между доменными сущностями и ORM моделями
**Dependencies**: 
- Domain: Stream Entity, StreamId, ChatId, UserId Value Objects, StreamStatus Enum
- ORM: models.Stream (SQLAlchemy model)

**Pattern**: Mapper Pattern (Entity ↔ ORM)
- to_entity(): ORM Model → Domain Entity
- to_orm(): Domain Entity → ORM Model
- update_orm(): Обновление существующего ORM объекта из Entity

**Key Mappings**:
- Stream.id (UUID) ↔ StreamId.value (UUID)
- Stream.status (SQLAlchemy Enum) ↔ StreamEntity.status (Python Enum)
- Stream.owner_id (UUID FK) ↔ UserId.value (UUID)
- Stream.chat_id (BigInteger) ↔ ChatId.value (int)
- Timestamps: created_at, started_at, stopped_at (nullable)

**Usage**:
```python
# ORM → Entity
stream_entity = StreamMapper.to_entity(orm_stream)

# Entity → новая ORM модель
orm_stream = StreamMapper.to_orm(stream_entity)

# Entity → обновление существующей ORM модели
StreamMapper.update_orm(orm_stream, stream_entity)
```

**Contract Tests**: См. tests/integration/persistence/test_stream_mapper.py (T065)
"""

import uuid
from typing import Optional
from datetime import datetime

from src.domain.entities.stream import Stream as StreamEntity, StreamStatus as DomainStreamStatus
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId
from src.models.stream import Stream as StreamORM, StreamStatus as ORMStreamStatus


class StreamMapper:
    """Mapper для конвертации между Stream Entity и Stream ORM Model."""

    @staticmethod
    def to_entity(orm_stream: StreamORM) -> StreamEntity:
        """
        Конвертирует ORM модель в доменную сущность.

        Args:
            orm_stream: SQLAlchemy Stream model

        Returns:
            StreamEntity: Доменная сущность stream

        Raises:
            ValueError: Если ORM модель невалидна (отсутствуют обязательные поля)

        **Type Conversions**:
        - id: UUID → StreamId(UUID)
        - owner_id: UUID → UserId(UUID)
        - chat_id: int → ChatId(int)
        - status: ORMStreamStatus(Enum) → DomainStreamStatus(Enum)
        """
        # Валидация обязательных полей
        if not orm_stream.id or not orm_stream.owner_id or not orm_stream.chat_id:
            raise ValueError(f"Stream ORM model has missing required fields: {orm_stream}")

        if not orm_stream.title or not orm_stream.title.strip():
            raise ValueError(f"Stream {orm_stream.id} must have non-empty title")

        # Создаём Value Objects
        stream_id = StreamId(value=orm_stream.id if isinstance(orm_stream.id, uuid.UUID) else uuid.UUID(str(orm_stream.id)))
        owner_id = UserId(value=orm_stream.owner_id if isinstance(orm_stream.owner_id, uuid.UUID) else uuid.UUID(str(orm_stream.owner_id)))  # UUID для UserId
        chat_id = ChatId(value=int(orm_stream.chat_id))  # BigInteger → int

        # Конвертируем ORM Enum → Domain Enum
        # ORM: StreamStatus.IDLE → Domain: DomainStreamStatus.IDLE
        status_mapping = {
            ORMStreamStatus.IDLE: DomainStreamStatus.IDLE,
            ORMStreamStatus.ACTIVE: DomainStreamStatus.ACTIVE,
            ORMStreamStatus.PAUSED: DomainStreamStatus.PAUSED,
            ORMStreamStatus.STOPPED: DomainStreamStatus.STOPPED,
        }
        
        domain_status = status_mapping.get(orm_stream.status)
        if domain_status is None:
            # Fallback для неизвестных статусов (если появятся новые в ORM)
            raise ValueError(f"Unknown ORM stream status: {orm_stream.status}")

        # Создаём Entity напрямую (не через factory, так как загружаем из БД с уже существующими данными)
        stream_entity = StreamEntity(
            id=stream_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=orm_stream.title,
            status=domain_status,
            current_track_index=orm_stream.current_track_index or 0,
            created_at=orm_stream.created_at or datetime.utcnow(),
            started_at=orm_stream.started_at,
            stopped_at=orm_stream.stopped_at,
        )

        return stream_entity

    @staticmethod
    def to_orm(stream_entity: StreamEntity, existing_orm: Optional[StreamORM] = None) -> StreamORM:
        """
        Конвертирует доменную сущность в ORM модель.

        Args:
            stream_entity: Domain Stream Entity
            existing_orm: Опциональная существующая ORM модель для обновления

        Returns:
            StreamORM: SQLAlchemy Stream model (новая или обновлённая)

        Note:
            Если existing_orm передан, обновляет его поля вместо создания нового.

        **Type Conversions**:
        - StreamId.value (UUID) → id (UUID)
        - UserId.value (UUID) → owner_id (UUID)
        - ChatId.value (int) → chat_id (BigInteger)
        - DomainStreamStatus → ORMStreamStatus
        """
        if existing_orm:
            # Обновляем существующую модель
            StreamMapper.update_orm(existing_orm, stream_entity)
            return existing_orm

        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainStreamStatus.IDLE: ORMStreamStatus.IDLE,
            DomainStreamStatus.ACTIVE: ORMStreamStatus.ACTIVE,
            DomainStreamStatus.PAUSED: ORMStreamStatus.PAUSED,
            DomainStreamStatus.STOPPED: ORMStreamStatus.STOPPED,
        }
        
        orm_status = status_mapping.get(stream_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain stream status: {stream_entity.status}")

        # Создаём новую ORM модель
        orm_stream = StreamORM(
            id=stream_entity.id.value,  # UUID → UUID (прямое присваивание)
            owner_id=stream_entity.owner_id.value,  # UUID → UUID (прямое присваивание)
            chat_id=stream_entity.chat_id.value,  # int → BigInteger
            title=stream_entity.title,
            status=orm_status,
            current_track_index=stream_entity.current_track_index,
            created_at=stream_entity.created_at,
            started_at=stream_entity.started_at,
            stopped_at=stream_entity.stopped_at,
        )

        return orm_stream

    @staticmethod
    def update_orm(orm_stream: StreamORM, stream_entity: StreamEntity) -> None:
        """
        Обновляет существующую ORM модель из доменной сущности.

        Args:
            orm_stream: Существующая SQLAlchemy Stream model
            stream_entity: Domain Stream Entity с новыми данными

        Note:
            Не обновляет immutable поля: id, owner_id, chat_id, created_at.
            Обновляет только изменяемые поля: title, status, current_track_index, timestamps.

        **Updated Fields**:
        - title (может измениться через переименование)
        - status (lifecycle transitions: IDLE → ACTIVE → PAUSED → STOPPED)
        - current_track_index (увеличивается при next_track())
        - started_at (устанавливается при start())
        - stopped_at (устанавливается при stop())
        """
        # Immutable поля не трогаем: id, owner_id, chat_id, created_at

        # Обновляем изменяемые поля
        orm_stream.title = stream_entity.title

        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainStreamStatus.IDLE: ORMStreamStatus.IDLE,
            DomainStreamStatus.ACTIVE: ORMStreamStatus.ACTIVE,
            DomainStreamStatus.PAUSED: ORMStreamStatus.PAUSED,
            DomainStreamStatus.STOPPED: ORMStreamStatus.STOPPED,
        }
        
        orm_status = status_mapping.get(stream_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain stream status: {stream_entity.status}")
        
        orm_stream.status = orm_status
        orm_stream.current_track_index = stream_entity.current_track_index
        orm_stream.started_at = stream_entity.started_at
        orm_stream.stopped_at = stream_entity.stopped_at

    @staticmethod
    def to_entity_list(orm_streams: list[StreamORM]) -> list[StreamEntity]:
        """
        Конвертирует список ORM моделей в список доменных сущностей.

        Args:
            orm_streams: Список SQLAlchemy Stream models

        Returns:
            List[StreamEntity]: Список доменных сущностей

        Note:
            Пропускает невалидные записи (например, без title или с некорректным status).
            В production рекомендуется логировать пропущенные записи.
        """
        entities = []
        for orm_stream in orm_streams:
            try:
                entities.append(StreamMapper.to_entity(orm_stream))
            except (ValueError, Exception) as e:
                # Логируем и пропускаем невалидные записи
                # TODO: Добавить логирование через logger
                print(f"Skipping invalid stream {orm_stream.id}: {e}")
                continue
        
        return entities
