"""
QuestionMapper - маппинг между Question Entity и Question ORM Model.

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Преобразование между доменными сущностями и ORM моделями
**Dependencies**:
- Domain: Question Entity, QuestionStatus Enum, ChatId, UserId Value Objects
- ORM: models.qa.Question (SQLAlchemy model)

**Pattern**: Mapper Pattern (Entity ↔ ORM)
- to_entity(): ORM Model → Domain Entity
- to_orm(): Domain Entity → ORM Model
- update_orm(): Обновление существующего ORM объекта из Entity

**Key Mappings**:
- Question.id (UUID) ↔ str
- Question.stream_id (UUID) ↔ str
- Question.author_id (UUID FK) ↔ UserId.value (UUID)
- Question.chat_id (BigInteger) ↔ ChatId.value (int)
- Question.status (SQLAlchemy Enum) ↔ QuestionEntity.status (Python Enum)
- Question.content ↔ QuestionEntity.question_text

**Usage**:
```python
# ORM → Entity
question_entity = QuestionMapper.to_entity(orm_question)

# Entity → новая ORM модель
orm_question = QuestionMapper.to_orm(question_entity)

# Entity → обновление существующей ORM модели
QuestionMapper.update_orm(orm_question, question_entity)
```
"""

import uuid
from datetime import datetime

from src.domain.entities.question import Question as QuestionEntity, QuestionStatus as DomainQuestionStatus
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.user_id import UserId
from src.models.qa import Question as QuestionORM, QuestionStatus as ORMQuestionStatus


class QuestionMapper:
    """Mapper для конвертации между Question Entity и Question ORM Model."""

    @staticmethod
    def to_entity(orm_question: QuestionORM) -> QuestionEntity:
        """
        Конвертирует ORM модель в доменную сущность.

        Args:
            orm_question: SQLAlchemy Question model

        Returns:
            QuestionEntity: Доменная сущность вопроса

        Raises:
            ValueError: Если ORM модель невалидна (отсутствуют обязательные поля)

        **Type Conversions**:
        - id: UUID → str
        - stream_id: UUID → str
        - author_id: UUID → UserId(UUID) (если есть)
        - content (ORM) → question_text (Entity)
        - status: ORMQuestionStatus(Enum) → DomainQuestionStatus(Enum)
        """
        # Валидация обязательных полей
        if not orm_question.id or not orm_question.stream_id:
            raise ValueError(f"Question ORM model has missing required fields: {orm_question}")

        if not orm_question.content or not orm_question.content.strip():
            raise ValueError(f"Question {orm_question.id} must have non-empty content")

        # Конвертируем ORM Enum → Domain Enum
        status_mapping = {
            ORMQuestionStatus.PENDING: DomainQuestionStatus.PENDING,
            ORMQuestionStatus.ANSWERED: DomainQuestionStatus.ANSWERED,
            ORMQuestionStatus.REJECTED: DomainQuestionStatus.REJECTED,
            ORMQuestionStatus.PINNED: DomainQuestionStatus.APPROVED,  # PINNED treated as APPROVED
        }

        domain_status = status_mapping.get(orm_question.status)
        if domain_status is None:
            raise ValueError(f"Unknown ORM question status: {orm_question.status}")

        # Создаём Value Objects
        stream_id = str(orm_question.stream_id)

        # ChatId from telegram_user_id if available, otherwise use 0
        chat_id_value = orm_question.telegram_user_id or 0
        chat_id = ChatId(value=int(chat_id_value))

        # UserId from author_id if available
        user_id = None
        if orm_question.author_id:
            user_id = UserId(value=orm_question.author_id if isinstance(orm_question.author_id, uuid.UUID) else uuid.UUID(str(orm_question.author_id)))
        else:
            # For anonymous questions, use telegram_user_id as UserId
            user_id = UserId(value=uuid.uuid4())  # Generate dummy ID for anonymous

        # question_text from content
        question_text = orm_question.content

        # vote_count from upvote_count
        vote_count = orm_question.upvote_count

        # timestamps
        created_at = orm_question.created_at or datetime.utcnow()
        approved_at = None
        answered_at = orm_question.answered_at
        rejected_at = None

        # Determine approved_at and rejected_at based on status
        if orm_question.status == ORMQuestionStatus.PINNED:
            # For pinned questions, we don't have approved_at, so use created_at
            approved_at = created_at
        elif orm_question.status == ORMQuestionStatus.REJECTED:
            # We don't track rejected_at in ORM, use current time
            rejected_at = datetime.utcnow()

        # answer
        answer = orm_question.answer

        # Создаём Entity напрямую (загружаем из БД с уже существующими данными)
        question_entity = QuestionEntity(
            id=str(orm_question.id),
            stream_id=stream_id,
            chat_id=chat_id,
            user_id=user_id,
            question_text=question_text,
            status=domain_status,
            vote_count=vote_count,
            created_at=created_at,
            approved_at=approved_at,
            answered_at=answered_at,
            rejected_at=rejected_at,
            answer=answer,
        )

        return question_entity

    @staticmethod
    def to_orm(question_entity: QuestionEntity) -> QuestionORM:
        """
        Конвертирует доменную сущность в ORM модель.

        Args:
            question_entity: Domain Question Entity

        Returns:
            QuestionORM: SQLAlchemy Question model (новая)

        **Type Conversions**:
        - str → id (UUID)
        - UserId.value (UUID) → author_id (UUID)
        - ChatId.value (int) → telegram_user_id (BigInteger)
        - DomainQuestionStatus → ORMQuestionStatus
        - question_text (Entity) → content (ORM)
        """
        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainQuestionStatus.PENDING: ORMQuestionStatus.PENDING,
            DomainQuestionStatus.APPROVED: ORMQuestionStatus.PINNED,  # Use PINNED for approved
            DomainQuestionStatus.ANSWERED: ORMQuestionStatus.ANSWERED,
            DomainQuestionStatus.REJECTED: ORMQuestionStatus.REJECTED,
        }

        orm_status = status_mapping.get(question_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain question status: {question_entity.status}")

        # Создаём новую ORM модель
        orm_question = QuestionORM(
            id=uuid.UUID(question_entity.id) if question_entity.id else uuid.uuid4(),
            stream_id=uuid.UUID(question_entity.stream_id) if question_entity.stream_id else uuid.uuid4(),
            author_id=question_entity.user_id.value,
            telegram_user_id=question_entity.chat_id.value,
            content=question_entity.question_text,
            status=orm_status,
            upvote_count=question_entity.vote_count,
            answer=question_entity.answer,
            answered_at=question_entity.answered_at,
            created_at=question_entity.created_at,
        )

        return orm_question

    @staticmethod
    def update_orm(orm_question: QuestionORM, question_entity: QuestionEntity) -> None:
        """
        Обновляет существующую ORM модель из доменной сущности.

        Args:
            orm_question: Существующая SQLAlchemy Question model
            question_entity: Domain Question Entity с новыми данными

        Note:
            Не обновляет immutable поля: id, stream_id, author_id, created_at.
            Обновляет только изменяемые поля.

        **Updated Fields**:
        - content/question_text
        - status (lifecycle transitions)
        - upvote_count
        - answer
        - answered_at
        """
        # Immutable поля не трогаем: id, stream_id, author_id, created_at

        # Обновляем изменяемые поля
        orm_question.content = question_entity.question_text

        # Конвертируем Domain Enum → ORM Enum
        status_mapping = {
            DomainQuestionStatus.PENDING: ORMQuestionStatus.PENDING,
            DomainQuestionStatus.APPROVED: ORMQuestionStatus.PINNED,
            DomainQuestionStatus.ANSWERED: ORMQuestionStatus.ANSWERED,
            DomainQuestionStatus.REJECTED: ORMQuestionStatus.REJECTED,
        }

        orm_status = status_mapping.get(question_entity.status)
        if orm_status is None:
            raise ValueError(f"Unknown domain question status: {question_entity.status}")

        orm_question.status = orm_status
        orm_question.upvote_count = question_entity.vote_count
        orm_question.answer = question_entity.answer
        orm_question.answered_at = question_entity.answered_at

    @staticmethod
    def to_entity_list(orm_questions: list[QuestionORM]) -> list[QuestionEntity]:
        """
        Конвертирует список ORM моделей в список доменных сущностей.

        Args:
            orm_questions: Список SQLAlchemy Question models

        Returns:
            List[QuestionEntity]: Список доменных сущностей

        Note:
            Пропускает невалидные записи (например, без content или с некорректным status).
            В production рекомендуется логировать пропущенные записи.
        """
        entities = []
        for orm_question in orm_questions:
            try:
                entities.append(QuestionMapper.to_entity(orm_question))
            except (ValueError, Exception) as e:
                # Логируем и пропускаем невалидные записи
                # TODO: Добавить логирование через logger
                print(f"Skipping invalid question {orm_question.id}: {e}")
                continue

        return entities
