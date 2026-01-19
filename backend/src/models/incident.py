"""
Модели для системы инцидентов и поддержки.

Включает:
- Incident: основная модель инцидента/обращения
- IncidentLog: логи браузера, прикреплённые к инциденту
- IncidentComment: комментарии к инциденту (от пользователя и поддержки)
- IncidentSolution: база знаний решений с embeddings для поиска
"""
import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime, func, Boolean, Text, BigInteger,
    ForeignKey, Float, Index, Enum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID

# Попытка импорта pgvector, fallback на обычный массив если недоступен
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None


class IncidentStatus(str, PyEnum):
    """Статусы инцидентов."""
    NEW = "new"                    # Новый, не обработан
    IN_PROGRESS = "in_progress"    # В работе
    WAITING_USER = "waiting_user"  # Ожидает ответа пользователя
    RESOLVED = "resolved"          # Решён
    CLOSED = "closed"              # Закрыт
    DUPLICATE = "duplicate"        # Дубликат


class IncidentPriority(str, PyEnum):
    """Приоритеты инцидентов."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(str, PyEnum):
    """Категории инцидентов (определяются AI)."""
    BUG = "bug"                    # Ошибка в системе
    FEATURE_REQUEST = "feature"    # Запрос на новую функцию
    QUESTION = "question"          # Вопрос по использованию
    PERFORMANCE = "performance"    # Проблемы производительности
    SECURITY = "security"          # Проблема безопасности
    UI_UX = "ui_ux"               # Проблемы интерфейса
    OTHER = "other"               # Прочее


class Incident(Base):
    """Основная модель инцидента/обращения в поддержку."""
    __tablename__ = "incidents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Связь с пользователем
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Основная информация
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Статус и категория
    status = Column(
        Enum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.NEW,
        index=True
    )
    priority = Column(
        Enum(IncidentPriority, name="incident_priority"),
        nullable=False,
        default=IncidentPriority.MEDIUM,
        index=True
    )
    category = Column(
        Enum(IncidentCategory, name="incident_category"),
        nullable=True,  # AI определит категорию
        index=True
    )
    
    # Контекст браузера (собирается автоматически)
    browser_info = Column(JSONB, nullable=True)  # {name, version, os, platform}
    page_url = Column(String(2000), nullable=True)
    
    # AI анализ
    ai_analysis = Column(JSONB, nullable=True)  # Результаты анализа AI
    ai_suggested_solution = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    similar_incident_id = Column(GUID(), ForeignKey("incidents.id"), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Назначенный оператор поддержки
    assigned_to_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Теги для классификации
    tags = Column(JSONB, nullable=True, default=list)  # ["audio", "playlist", "schedule"]
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="incidents")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    similar_incident = relationship("Incident", remote_side=[id])
    logs = relationship("IncidentLog", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("IncidentComment", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentComment.created_at")
    
    # Индексы для эффективного поиска
    __table_args__ = (
        Index("idx_incidents_status_priority", "status", "priority"),
        Index("idx_incidents_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Incident(id={self.id}, title='{self.title[:30]}...', status={self.status})>"


class IncidentLog(Base):
    """Логи браузера, прикреплённые к инциденту."""
    __tablename__ = "incident_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    incident_id = Column(GUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Тип лога
    log_type = Column(String(50), nullable=False, index=True)  # console, network, action, performance
    
    # Данные лога
    level = Column(String(20), nullable=True)  # error, warn, info, debug
    message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Для network логов
    url = Column(String(2000), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(BigInteger, nullable=True)
    response_time_ms = Column(BigInteger, nullable=True)
    
    # Для action логов
    action = Column(String(200), nullable=True)
    element = Column(String(500), nullable=True)
    
    # Дополнительные данные
    extra_data = Column(JSONB, nullable=True)
    
    # Временная метка события
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    incident = relationship("Incident", back_populates="logs")
    
    __table_args__ = (
        Index("idx_incident_logs_type_level", "log_type", "level"),
    )


class IncidentComment(Base):
    """Комментарии к инциденту."""
    __tablename__ = "incident_comments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    incident_id = Column(GUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Контент
    content = Column(Text, nullable=False)
    
    # Тип комментария
    is_internal = Column(Boolean, default=False)  # Внутренний комментарий (не виден пользователю)
    is_ai_generated = Column(Boolean, default=False)  # Сгенерирован AI
    
    # Вложения (скриншоты и т.д.)
    attachments = Column(JSONB, nullable=True, default=list)  # [{filename, url, mime_type}]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    incident = relationship("Incident", back_populates="comments")
    user = relationship("User", backref="incident_comments")


class IncidentSolution(Base):
    """База знаний решений с embeddings для семантического поиска."""
    __tablename__ = "incident_solutions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Связь с исходным инцидентом (если решение создано из инцидента)
    source_incident_id = Column(GUID(), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    
    # Проблема и решение
    problem_title = Column(String(500), nullable=False)
    problem_description = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)
    
    # Категория
    category = Column(
        Enum(IncidentCategory, name="incident_category"),
        nullable=True
    )
    
    # Ключевые слова для поиска
    keywords = Column(JSONB, nullable=True, default=list)  # ["audio", "playback", "error"]
    
    # Статистика эффективности
    times_used = Column(BigInteger, default=0)
    positive_feedback = Column(BigInteger, default=0)
    negative_feedback = Column(BigInteger, default=0)
    
    # Активность
    is_active = Column(Boolean, default=True)
    
    # Метаданные
    created_by_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    source_incident = relationship("Incident")
    created_by = relationship("User")
    
    def __repr__(self):
        return f"<IncidentSolution(id={self.id}, title='{self.problem_title[:30]}...')>"


# Отдельная таблица для embeddings (если pgvector доступен)
if PGVECTOR_AVAILABLE:
    class IncidentEmbedding(Base):
        """Embeddings для семантического поиска похожих инцидентов."""
        __tablename__ = "incident_embeddings"

        id = Column(GUID(), primary_key=True, default=uuid.uuid4)
        
        # Связь с инцидентом или решением
        incident_id = Column(GUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
        solution_id = Column(GUID(), ForeignKey("incident_solutions.id", ondelete="CASCADE"), nullable=True, index=True)
        
        # Embedding vector (1536 для OpenAI text-embedding-3-small)
        embedding = Column(Vector(1536), nullable=False)
        
        # Текст, из которого создан embedding
        text_hash = Column(String(64), nullable=False, index=True)  # SHA256 текста
        
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        
        # Relationships
        incident = relationship("Incident", backref="embeddings")
        solution = relationship("IncidentSolution", backref="embeddings")
else:
    # Fallback модель без pgvector
    class IncidentEmbedding(Base):
        """Placeholder для embeddings (pgvector не установлен)."""
        __tablename__ = "incident_embeddings"

        id = Column(GUID(), primary_key=True, default=uuid.uuid4)
        incident_id = Column(GUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
        solution_id = Column(GUID(), ForeignKey("incident_solutions.id", ondelete="CASCADE"), nullable=True, index=True)
        
        # Без pgvector храним как JSONB (менее эффективно, но работает)
        embedding = Column(JSONB, nullable=False)
        text_hash = Column(String(64), nullable=False, index=True)
        
        created_at = Column(DateTime(timezone=True), server_default=func.now())
