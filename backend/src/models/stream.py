"""Stream ORM Model.

SQLAlchemy model для персистентности Stream Entity (broadcast streams).
Создан в рамках Phase 6 (Clean Architecture Refactoring).

**Purpose**: Хранение состояния broadcast streams в PostgreSQL
**Layer**: Infrastructure (persistence)
**Mapping**: Используется StreamMapper для конвертации Stream Entity ↔ Stream ORM

**Design Decision**:
- NEW model (не переиспользуем RadioStream или StreamState)
- RadioStream - для internet radio streams (другая бизнес-логика)
- StreamState - Pydantic model для state management (не persistence)

**Schema Reference**: См. specs/025-clean-architecture-rules/data-model.md §ORM Model Mapping
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, BigInteger, DateTime, Enum as SQLEnum, ForeignKey, func
from sqlalchemy.orm import relationship

from src.database import Base, GUID


class StreamStatus(str, PyEnum):
    """Статусы broadcast stream (синхронизирован с domain/entities/stream.py)."""
    IDLE = "idle"           # Stream создан, но не запущен
    ACTIVE = "active"       # Stream активно транслирует
    PAUSED = "paused"       # Stream приостановлен
    STOPPED = "stopped"     # Stream остановлен
    ERROR = "error"         # Ошибка при трансляции


class Stream(Base):
    """ORM Model для broadcast streams.
    
    **Table**: streams
    **Entity Mapping**: См. infrastructure/persistence/mappers/stream_mapper.py
    
    **Relationships**:
    - owner: User (FK to users.id)
    - playlists: List[PlaylistItem] (one-to-many, cascade delete)
    - questions: List[Question] (one-to-many, cascade delete)
    
    **Timestamps**:
    - created_at: Время создания stream
    - started_at: Время последнего запуска (NULL если никогда не запускался)
    - stopped_at: Время последней остановки (NULL если не останавливался)
    """
    __tablename__ = "streams"
    
    # Primary Key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    owner_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    
    # Core Fields
    chat_id = Column(BigInteger, nullable=False, index=True, comment="Telegram chat ID для трансляции")
    title = Column(String(255), nullable=False, comment="Название stream")
    status = Column(
        SQLEnum(StreamStatus, name="stream_status", create_type=True), 
        nullable=False, 
        default=StreamStatus.IDLE,
        comment="Текущий статус stream"
    )
    current_track_index = Column(
        BigInteger, 
        nullable=False, 
        default=0,
        comment="Индекс текущего трека в плейлисте (0-based)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        comment="Время создания stream"
    )
    started_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Время последнего запуска stream (NULL если никогда не запускался)"
    )
    stopped_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Время последней остановки stream (NULL если не останавливался)"
    )
    
    # Relationships
    owner = relationship("src.models.user.User", back_populates="streams", lazy="joined")
    playlists = relationship(
        "src.models.playlist.PlaylistItem",
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="src.models.playlist.PlaylistItem.position",
        lazy="select"
    )
    questions = relationship(
        "src.models.qa.Question",
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="src.models.qa.Question.upvote_count.desc()",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        return f"<Stream(id={self.id}, title='{self.title}', status={self.status}, chat_id={self.chat_id})>"
