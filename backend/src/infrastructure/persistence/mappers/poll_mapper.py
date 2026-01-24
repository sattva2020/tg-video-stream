"""
PollMapper - маппинг между Poll Entity и Poll ORM Model.

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Преобразование между доменными сущностями и ORM моделями
**Dependencies**:
- Domain: Poll Entity, PollOption, PollStatus Enum, ChatId, UserId Value Objects
- ORM: models.Poll, models.PollOption (SQLAlchemy models)

**Pattern**: Mapper Pattern (Entity ↔ ORM)
- to_entity(): ORM Model → Domain Entity
- to_orm(): Domain Entity → ORM Model
- update_orm(): Обновление существующего ORM объекта из Entity

**Key Mappings**:
- Poll.id (UUID) ↔ str
- Poll.stream_id (UUID) ↔ str
- Poll.owner_id (UUID FK) ↔ UserId.value (UUID)
- Poll.chat_id (BigInteger) ↔ ChatId.value (int)
- Poll.status (SQLAlchemy Enum) ↔ PollEntity.status (Python Enum)
- PollOptions: ORM relationship → List[PollOption]

**Usage**:
```python
# ORM → Entity
poll_entity = PollMapper.to_entity(orm_poll)

# Entity → новая ORM модель
orm_poll = PollMapper.to_orm(poll_entity)

# Entity → обновление существующей ORM модели
PollMapper.update_orm(orm_poll, poll_entity)
```
"""

import uuid
from typing import Optional
from datetime import datetime

from src.domain.entities.poll import Poll as PollEntity, PollOption, PollStatus as DomainPollStatus
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId
from src.models.poll import Poll as PollORM, PollStatus as ORMPollStatus, PollOption as PollOptionORM


class PollMapper:
    """Mapper для конвертации между Poll Entity и Poll ORM Model."""

    @staticmethod
    def to_entity(orm_poll: PollORM) -> PollEntity:
        """
        Конвертирует ORM модель в доменную сущность.

        Args:
            orm_poll: SQLAlchemy Poll model

        Returns:
            PollEntity: Доменная сущность poll

        Raises:
            ValueError: Если ORM модель невалидна (отсутствуют обязательные поля)

        **Type Conversions**:
        - id: UUID → str
        - owner_id: UUID → UserId(UUID)
        - stream_id: UUID → str
        - chat_id: int → ChatId(int) (если есть в ORM, иначе используем None)
        - status: ORMPollStatus(Enum) → DomainPollStatus(Enum)
        - options: List[PollOptionORM] → List[PollOption]
        """
        # Валидация обязательных полей
        if not orm_poll.id or not orm_poll.owner_id:
            raise ValueError(f"Poll ORM model has missing required fields: {orm_poll}")

        if not orm_poll.question or not orm_poll.question.strip():
            raise ValueError(f"Poll {orm_poll.id} must have non-empty question")

        # Конвертируем ORM Enum → Domain Enum
        status_mapping = {
            ORMPollStatus.DRAFT: DomainPollStatus.DRAFT,
            ORMPollStatus.ACTIVE: DomainPollStatus.ACTIVE,
            ORMPollStatus.PAUSED: DomainPollStatus.ACTIVE,  # PAUSED treated as ACTIVE for now
            ORMPollStatus.CLOSED: DomainPollStatus.CLOSED,
        }

        domain_status = status_mapping.get(orm_poll.status)
        if domain_status is None:
            raise ValueError(f"Unknown ORM poll status: {orm_poll.status}")

        # Конвертируем options
        poll_options = []
        for orm_option in orm_poll.options:
            poll_option = PollOption(
                id=str(orm_option.id),
                option_text=orm_option.text,
                vote_count=orm_option.vote_count
            )
            poll_options.append(poll_option)

        # Создаём Value Objects
        owner_id = UserId(value=orm_poll.owner_id if isinstance(orm_poll.owner_id, uuid.UUID) else uuid.UUID(str(orm_poll.owner_id)))

        # ChatId может быть NULL в Poll ORM (создаем из None или 0)
        # В доменной модели Poll всегда требует ChatId, используем заглушку если нет
        chat_id_value = getattr(orm_poll, 'chat_id', None) or 0
        chat_id = ChatId(value=int(chat_id_value))

        # Stream ID (используем None или пустую строку если не привязан к стриму)
        stream_id = str(getattr(orm_poll, 'stream_id', None) or uuid.uuid4())

        # Создаём Entity напрямую (загружаем из БД с уже существующими данными)
        poll_entity = PollEntity(
            id=str(orm_poll.id),
            stream_id=stream_id,
            chat_id=chat_id,
            created_by=owner_id,
            question=orm_poll.question,
            options=poll_options,
            status=domain_status,
            allow_multiple_votes=orm_poll.allow_multiple_votes,
            created_at=orm_poll.created_at or datetime.utcnow(),
            published_at=orm_poll.started_at,
            closed_at=orm_poll.closed_at,
        )

        return poll_entity

    @staticmethod
    def to_orm(poll_entity: PollEntity, existing_orm: Optional[PollORM] = None) -> PollORM:
        """
        Конвертирует доменную сущность в ORM модель.

        Args:
            poll_entity: Domain Poll Entity
            existing_orm: Опциональная существующая ORM модель для обновления

        Returns:
            PollORM: SQLAlchemy Poll model (новая или обновлённая)

        Note:
            Если existing_orm передан, обновляет его поля вместо создания нового.

        **Type Conversions**:
        - str → id (UUID)
        - UserId.value (UUID) → owner_id (UUID)
        - ChatId.value (int) → chat_id (BigInteger)
        - DomainPollStatus → ORMPollStatus
        """
        if existing_orm:
            # Обновляем существующую модель
            PollMapper.update_orm(existing_orm, poll_entity)
            return existing_orm

        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainPollStatus.DRAFT: ORMPollStatus.DRAFT,
            DomainPollStatus.ACTIVE: ORMPollStatus.ACTIVE,
            DomainPollStatus.CLOSED: ORMPollStatus.CLOSED,
        }

        orm_status = status_mapping.get(poll_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain poll status: {poll_entity.status}")

        # Создаём новые ORM модели для options
        orm_options = []
        for option in poll_entity.options:
            orm_option = PollOptionORM(
                id=uuid.UUID(option.id) if option.id != str(uuid.UUID(option.id)) else uuid.UUID(option.id),
                poll_id=None,  # Will be set when poll is saved
                text=option.option_text,
                vote_count=option.vote_count,
                order=len(orm_options)
            )
            orm_options.append(orm_option)

        # Создаём новую ORM модель
        orm_poll = PollORM(
            id=uuid.UUID(poll_entity.id) if poll_entity.id != str(uuid.UUID(poll_entity.id)) else uuid.UUID(poll_entity.id),
            owner_id=poll_entity.created_by.value,
            question=poll_entity.question,
            status=orm_status,
            allow_multiple_votes=poll_entity.allow_multiple_votes,
            created_at=poll_entity.created_at,
            started_at=poll_entity.published_at,
            closed_at=poll_entity.closed_at,
            options=orm_options,
        )

        return orm_poll

    @staticmethod
    def update_orm(orm_poll: PollORM, poll_entity: PollEntity) -> None:
        """
        Обновляет существующую ORM модель из доменной сущности.

        Args:
            orm_poll: Существующая SQLAlchemy Poll model
            poll_entity: Domain Poll Entity с новыми данными

        Note:
            Не обновляет immutable поля: id, owner_id, created_at.
            Обновляет только изменяемые поля: question, status, timestamps, options.

        **Updated Fields**:
        - question (может измениться при редактировании)
        - status (lifecycle transitions: DRAFT → ACTIVE → CLOSED)
        - allow_multiple_votes (настройки опроса)
        - published_at/started_at (устанавливается при publish())
        - closed_at (устанавливается при close())
        - options (обновление вариантов и голосов)
        """
        # Immutable поля не трогаем: id, owner_id, created_at

        # Обновляем изменяемые поля
        orm_poll.question = poll_entity.question

        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainPollStatus.DRAFT: ORMPollStatus.DRAFT,
            DomainPollStatus.ACTIVE: ORMPollStatus.ACTIVE,
            DomainPollStatus.CLOSED: ORMPollStatus.CLOSED,
        }

        orm_status = status_mapping.get(poll_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain poll status: {poll_entity.status}")

        orm_poll.status = orm_status
        orm_poll.allow_multiple_votes = poll_entity.allow_multiple_votes
        orm_poll.started_at = poll_entity.published_at
        orm_poll.closed_at = poll_entity.closed_at

        # Обновляем options (синхронизируем списки)
        # Сначала удаляем отсутствующие options
        entity_option_ids = {uuid.UUID(opt.id) for opt in poll_entity.options}

        for orm_option in orm_poll.options[:]:
            if orm_option.id not in entity_option_ids:
                orm_poll.options.remove(orm_option)

        # Обновляем или добавляем options
        entity_options_map = {uuid.UUID(opt.id): opt for opt in poll_entity.options}
        for orm_option in orm_poll.options:
            if orm_option.id in entity_options_map:
                entity_option = entity_options_map[orm_option.id]
                orm_option.text = entity_option.option_text
                orm_option.vote_count = entity_option.vote_count

        # Добавляем новые options
        existing_option_ids = {opt.id for opt in orm_poll.options}
        for option in poll_entity.options:
            option_uuid = uuid.UUID(option.id)
            if option_uuid not in existing_option_ids:
                orm_option = PollOptionORM(
                    id=option_uuid,
                    poll_id=orm_poll.id,
                    text=option.option_text,
                    vote_count=option.vote_count,
                    order=len(orm_poll.options)
                )
                orm_poll.options.append(orm_option)

    @staticmethod
    def to_entity_list(orm_polls: list[PollORM]) -> list[PollEntity]:
        """
        Конвертирует список ORM моделей в список доменных сущностей.

        Args:
            orm_polls: Список SQLAlchemy Poll models

        Returns:
            List[PollEntity]: Список доменных сущностей

        Note:
            Пропускает невалидные записи (например, без question или с некорректным status).
            В production рекомендуется логировать пропущенные записи.
        """
        entities = []
        for orm_poll in orm_polls:
            try:
                entities.append(PollMapper.to_entity(orm_poll))
            except (ValueError, Exception) as e:
                # Логируем и пропускаем невалидные записи
                # TODO: Добавить логирование через logger
                print(f"Skipping invalid poll {orm_poll.id}: {e}")
                continue

        return entities
