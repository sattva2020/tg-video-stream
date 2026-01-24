"""Poll ORM Models.

SQLAlchemy models для персистентности Poll Entity (interactive polls).
Создан в рамках Feature 020 (Viewer Interaction & Engagement Features).

**Purpose**: Хранение состояния интерактивных опросов в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется PollMapper для конвертации Poll Entity ↔ Poll ORM

**Design Decision**:
- NEW models для поддержки интерактивных опросов
- Поддержка single choice и multiple choice polls
- Поддержка anonymous и authenticated voting
- Кэширование vote_count для производительности

**Schema Reference**: См. specs/020-viewer-interaction-engagement-features/spec.md
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, func, Index
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class PollType(str, PyEnum):
    """Типы опросов."""
    SINGLE_CHOICE = "single_choice"    # Выбор одного варианта
    MULTIPLE_CHOICE = "multiple_choice"  # Выбор нескольких вариантов


class PollStatus(str, PyEnum):
    """Статусы опросов."""
    DRAFT = "draft"         # Черновик, не опубликован
    ACTIVE = "active"       # Активный опрос
    PAUSED = "paused"       # Приостановлен
    CLOSED = "closed"       # Завершен


class Poll(Base):
    """ORM Model для интерактивных опросов.

    **Table**: polls
    **Entity Mapping**: См. infrastructure/persistence/mappers/poll_mapper.py

    **Relationships**:
    - owner: User (FK to users.id)
    - options: List[PollOption] (one-to-many, cascade delete)
    - votes: List[PollVote] (one-to-many, cascade delete)

    **Timestamps**:
    - created_at: Время создания poll
    - started_at: Время запуска (NULL если не запускался)
    - ended_at: Запланированное время окончания (NULL если бессрочный)
    - closed_at: Фактическое время закрытия (NULL если открыт)
    """
    __tablename__ = "polls"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Core Fields
    question = Column(String(500), nullable=False, comment="Вопрос опроса")
    description = Column(String(2000), nullable=True, comment="Описание опроса (опционально)")
    poll_type = Column(
        SQLEnum(PollType, name="poll_type", create_type=True),
        nullable=False,
        default=PollType.SINGLE_CHOICE,
        comment="Тип опроса (single/multiple choice)"
    )
    status = Column(
        SQLEnum(PollStatus, name="poll_status", create_type=True),
        nullable=False,
        default=PollStatus.DRAFT,
        comment="Текущий статус опроса"
    )

    # Voting Settings
    allow_multiple_votes = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Разрешить пользователю голосовать несколько раз"
    )
    is_anonymous = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Анонимное голосование (не записывать user_id)"
    )
    max_votes_per_user = Column(
        Integer,
        nullable=True,
        comment="Максимальное количество голосов одного пользователя (NULL = без ограничений)"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания опроса"
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время запуска опроса (NULL если не запускался)"
    )
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Запланированное время окончания (NULL если бессрочный)"
    )
    closed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Фактическое время закрытия (NULL если открыт)"
    )

    # Relationships
    owner = relationship("src.models.user.User", lazy="joined")
    options = relationship(
        "src.models.poll.PollOption",
        back_populates="poll",
        cascade="all, delete-orphan",
        order_by="src.models.poll.PollOption.order",
        lazy="select"
    )
    votes = relationship(
        "src.models.poll.PollVote",
        back_populates="poll",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Poll(id={self.id}, question='{self.question}', status={self.status})>"


class PollOption(Base):
    """ORM Model для вариантов ответа в опросе.

    **Table**: poll_options
    **Entity Mapping**: Часть Poll Entity

    **Relationships**:
    - poll: Poll (FK to polls.id)
    - votes: List[PollVote] (one-to-many, cascade delete)

    **Fields**:
    - vote_count: Кэшированное количество голосов (обновляется при голосовании)
    """
    __tablename__ = "poll_options"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    poll_id = Column(GUID(), ForeignKey("polls.id"), nullable=False, index=True)

    # Core Fields
    text = Column(String(500), nullable=False, comment="Текст варианта ответа")
    order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Порядок отображения варианта"
    )
    vote_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Кэшированное количество голосов"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания варианта"
    )

    # Relationships
    poll = relationship("src.models.poll.Poll", back_populates="options", lazy="joined")
    votes = relationship(
        "src.models.poll.PollVote",
        back_populates="option",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes
    __table_args__ = (
        Index("ix_poll_options_poll_order", "poll_id", "order"),
    )

    def __repr__(self) -> str:
        return f"<PollOption(id={self.id}, text='{self.text}', vote_count={self.vote_count})>"


class PollVote(Base):
    """ORM Model для голосов в опросе.

    **Table**: poll_votes
    **Entity Mapping**: Часть Poll Entity

    **Relationships**:
    - poll: Poll (FK to polls.id)
    - option: PollOption (FK to poll_options.id)
    - user: User (FK to users.id, nullable)

    **Fields**:
    - user_id: ID зарегистрированного пользователя (NULL если анонимный)
    - telegram_user_id: Telegram ID для анонимных пользователей
    """
    __tablename__ = "poll_votes"

    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    poll_id = Column(GUID(), ForeignKey("polls.id"), nullable=False, index=True)
    option_id = Column(GUID(), ForeignKey("poll_options.id"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # User identification (for anonymous users)
    telegram_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram ID для анонимных пользователей"
    )

    # Timestamps
    voted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время голосования"
    )

    # Relationships
    poll = relationship("src.models.poll.Poll", back_populates="votes", lazy="joined")
    option = relationship("src.models.poll.PollOption", back_populates="votes", lazy="joined")
    user = relationship("src.models.user.User", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_poll_votes_poll_user", "poll_id", "user_id"),
        Index("ix_poll_votes_poll_telegram", "poll_id", "telegram_user_id"),
    )

    def __repr__(self) -> str:
        return f"<PollVote(id={self.id}, poll_id={self.poll_id}, option_id={self.option_id})>"
