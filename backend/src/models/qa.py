"""Q&A ORM Models.

SQLAlchemy models для персистентности Q&A Entity (question and answer sessions).
Создан в рамках Feature 020 (Viewer Interaction & Engagement Features).

**Purpose**: Хранение состояния вопросов и ответов в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется QuestionMapper для конвертации Question Entity ↔ Question ORM

**Design Decision**:
- NEW models для поддержки Q&A сессий
- Поддержка anonymous и authenticated вопросов
- Поддержка upvoting вопросов зрителями
- Кэширование upvote_count для производительности

**Schema Reference**: См. specs/020-viewer-interaction-engagement-features/spec.md
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, func, Index, Text
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class QuestionStatus(str, PyEnum):
    """Статусы вопросов."""
    PENDING = "pending"       # Ожидает ответа
    ANSWERED = "answered"     # Отвечен
    REJECTED = "rejected"     # Отклонен (модерацией)
    PINNED = "pinned"         # Закреплен (важный вопрос)


class Question(Base):
    """ORM Model для вопросов зрителей.

    **Table**: questions
    **Entity Mapping**: См. infrastructure/persistence/mappers/question_mapper.py

    **Relationships**:
    - stream: Stream (FK to streams.id)
    - author: User (FK to users.id, nullable)
    - upvotes: List[QuestionUpvote] (one-to-many, cascade delete)

    **Timestamps**:
    - created_at: Время создания вопроса
    - answered_at: Время ответа на вопрос (NULL если не отвечен)
    """
    __tablename__ = "questions"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=False, index=True)
    author_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # User identification (for anonymous users)
    telegram_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram ID для анонимных пользователей"
    )
    author_name = Column(
        String(255),
        nullable=True,
        comment="Имя автора (для анонимных вопросов или отображения)"
    )

    # Core Fields
    content = Column(
        Text,
        nullable=False,
        comment="Текст вопроса"
    )
    status = Column(
        SQLEnum(QuestionStatus, name="question_status", create_type=True),
        nullable=False,
        default=QuestionStatus.PENDING,
        comment="Текущий статус вопроса"
    )
    is_pinned = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Вопрос закреплен (важный)"
    )
    upvote_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Кэшированное количество upvotes"
    )

    # Answer fields
    answer = Column(
        Text,
        nullable=True,
        comment="Ответ на вопрос (NULL если не отвечен)"
    )
    answered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время ответа на вопрос (NULL если не отвечен)"
    )

    # Moderation
    is_filtered = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Вопрос отфильтрован модерацией"
    )
    filter_reason = Column(
        String(500),
        nullable=True,
        comment="Причина фильтрации (например, неуместный контент)"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания вопроса"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Время последнего обновления"
    )

    # Relationships
    stream = relationship("src.models.stream.Stream", back_populates="questions", lazy="joined")
    author = relationship("src.models.user.User", lazy="joined")
    upvotes = relationship(
        "src.models.qa.QuestionUpvote",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes
    __table_args__ = (
        Index("ix_questions_stream_status", "stream_id", "status"),
        Index("ix_questions_stream_upvotes", "stream_id", "upvote_count"),
        Index("ix_questions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, content='{self.content[:50]}...', status={self.status}, upvotes={self.upvote_count})>"


class QuestionUpvote(Base):
    """ORM Model для upvotes на вопросы.

    **Table**: question_upvotes
    **Entity Mapping**: Часть Question Entity

    **Relationships**:
    - question: Question (FK to questions.id)
    - user: User (FK to users.id, nullable)

    **Fields**:
    - user_id: ID зарегистрированного пользователя (NULL если анонимный)
    - telegram_user_id: Telegram ID для анонимных пользователей
    """
    __tablename__ = "question_upvotes"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    question_id = Column(GUID(), ForeignKey("questions.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # User identification (for anonymous users)
    telegram_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram ID для анонимных пользователей"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время upvote"
    )

    # Relationships
    question = relationship("src.models.qa.Question", back_populates="upvotes", lazy="joined")
    user = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_question_upvotes_question_user", "question_id", "user_id"),
        Index("ix_question_upvotes_question_telegram", "question_id", "telegram_user_id"),
        Index("ix_question_upvotes_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<QuestionUpvote(id={self.id}, question_id={self.question_id})>"
