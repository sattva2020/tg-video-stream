"""
InteractionMapper - маппинг между Interaction Entities и ORM Models.

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Преобразование между доменными сущностями взаимодействий и ORM моделями
**Dependencies**:
- Domain: Reaction Entity
- ORM: models.EmojiReaction, models.ChatMessage (SQLAlchemy models)

**Pattern**: Mapper Pattern (Entity ↔ ORM)
- to_entity(): ORM Model → Domain Entity
- to_orm(): Domain Entity → ORM Model
- update_orm(): Обновление существующего ORM объекта из Entity

**Usage**:
```python
# ORM → Entity
reaction_entity = InteractionMapper.reaction_to_entity(orm_reaction)

# Entity → новая ORM модель
orm_reaction = InteractionMapper.reaction_to_orm(reaction_entity)

# Entity → обновление существующей ORM модели
InteractionMapper.update_reaction_orm(orm_reaction, reaction_entity)
```
"""

import uuid
from typing import Optional, List
from datetime import datetime

from src.domain.entities.reaction import Reaction as ReactionEntity, ReactionType
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId
from src.models.interaction import EmojiReaction as EmojiReactionORM, ReactionDisplayStatus, ChatMessage as ChatMessageORM


class InteractionMapper:
    """Mapper для конвертации между Interaction Entities и ORM Models."""

    @staticmethod
    def reaction_to_entity(orm_reaction: EmojiReactionORM) -> ReactionEntity:
        """
        Конвертирует EmojiReaction ORM модель в Reaction доменную сущность.

        Args:
            orm_reaction: SQLAlchemy EmojiReaction model

        Returns:
            ReactionEntity: Доменная сущность реакции

        Raises:
            ValueError: Если ORM модель невалидна

        **Type Conversions**:
        - id: UUID → str
        - stream_id: UUID → str
        - emoji: str → ReactionType(Enum)
        - user_id: UUID → UserId(UUID) (если есть)
        - display_status: ReactionDisplayStatus → (учитывается в бизнес-логике)
        """
        if not orm_reaction.id or not orm_reaction.stream_id:
            raise ValueError(f"EmojiReaction ORM model has missing required fields: {orm_reaction.id}")

        if not orm_reaction.emoji or not orm_reaction.emoji.strip():
            raise ValueError(f"EmojiReaction {orm_reaction.id} must have non-empty emoji")

        # Конвертируем emoji строку в ReactionType enum
        # Если эмодзи не соответствует стандартному типу, используем его как custom
        try:
            reaction_type = ReactionType(orm_reaction.emoji)
        except ValueError:
            # Для custom emoji создаем объект с сырым значением
            reaction_type = orm_reaction.emoji

        # ChatId из stream (предполагаем, что у stream есть chat_id)
        # Временно используем заглушку, если нет доступа к stream.chat_id
        chat_id = ChatId(value=0)  # TODO: Получать из stream

        # UserId может быть NULL для анонимных пользователей
        user_id = None
        if orm_reaction.user_id:
            user_id = UserId(value=orm_reaction.user_id if isinstance(orm_reaction.user_id, uuid.UUID) else uuid.UUID(str(orm_reaction.user_id)))

        # Создаём Reaction entity
        # Используем create() factory для бизнес-логики
        reaction_id = str(orm_reaction.id)
        stream_id = str(orm_reaction.stream_id)

        # Примечание: т.к. мы загружаем из БД, создаем entity напрямую
        # Вместо использования factory метода (который устанавливает created_at)
        reaction_entity = ReactionEntity(
            id=reaction_id,
            stream_id=stream_id,
            chat_id=chat_id,
            user_id=user_id or UserId(value=uuid.uuid4()),  # Fallback для анонимных
            reaction_type=reaction_type if isinstance(reaction_type, ReactionType) else ReactionType.HEART,
            count=1,  # Каждая ORM запись = одна реакция
            created_at=orm_reaction.created_at or datetime.utcnow(),
            expires_at=orm_reaction.expires_at,
        )

        return reaction_entity

    @staticmethod
    def reaction_to_orm(reaction_entity: ReactionEntity) -> EmojiReactionORM:
        """
        Конвертирует Reaction доменную сущность в ORM модель.

        Args:
            reaction_entity: Domain Reaction Entity

        Returns:
            EmojiReactionORM: SQLAlchemy EmojiReaction model

        **Type Conversions**:
        - str → id (UUID)
        - ReactionType → emoji (str)
        - UserId.value → user_id (UUID, nullable)
        """
        # Конвертируем ReactionType в строку emoji
        if isinstance(reaction_entity.reaction_type, ReactionType):
            emoji = reaction_entity.reaction_type.value
        else:
            emoji = str(reaction_entity.reaction_type)

        # Создаём новую ORM модель
        orm_reaction = EmojiReactionORM(
            id=uuid.UUID(reaction_entity.id) if reaction_entity.id != str(uuid.UUID(reaction_entity.id)) else uuid.UUID(reaction_entity.id),
            stream_id=uuid.UUID(reaction_entity.stream_id) if reaction_entity.stream_id != str(uuid.UUID(reaction_entity.stream_id)) else uuid.UUID(reaction_entity.stream_id),
            user_id=reaction_entity.user_id.value if reaction_entity.user_id else None,
            emoji=emoji,
            display_status=ReactionDisplayStatus.PENDING,
            position_x=50,  # Default positions
            position_y=50,
            scale=100,
            created_at=reaction_entity.created_at,
            expires_at=reaction_entity.expires_at,
        )

        return orm_reaction

    @staticmethod
    def update_reaction_orm(orm_reaction: EmojiReactionORM, reaction_entity: ReactionEntity) -> None:
        """
        Обновляет существующую ORM модель из доменной сущности.

        Args:
            orm_reaction: Существующая SQLAlchemy EmojiReaction model
            reaction_entity: Domain Reaction Entity с новыми данными

        Note:
            Реакции immutable в большинстве случаев - обновляется редко.
            Обновляет только expires_at и display_status.
        """
        # Immutable поля не трогаем: id, stream_id, user_id, emoji, created_at

        # Обновляем изменяемые поля
        orm_reaction.expires_at = reaction_entity.expires_at

    @staticmethod
    def reaction_to_entity_list(orm_reactions: List[EmojiReactionORM]) -> List[ReactionEntity]:
        """
        Конвертирует список ORM моделей в список доменных сущностей.

        Args:
            orm_reactions: Список SQLAlchemy EmojiReaction models

        Returns:
            List[ReactionEntity]: Список доменных сущностей

        Note:
            Пропускает невалидные записи с логированием.
        """
        entities = []
        for orm_reaction in orm_reactions:
            try:
                entities.append(InteractionMapper.reaction_to_entity(orm_reaction))
            except (ValueError, Exception) as e:
                # Логируем и пропускаем невалидные записи
                # TODO: Добавить логирование через logger
                print(f"Skipping invalid reaction {orm_reaction.id}: {e}")
                continue

        return entities
