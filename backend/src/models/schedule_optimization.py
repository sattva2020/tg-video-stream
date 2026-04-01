"""
Модели для оптимизации расписания и AI-рекомендаций.
Feature: 015-smart-scheduling-auto-pilot-mode
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey,
    Boolean, Enum, Integer, Text, Float,
    func, BigInteger, Numeric, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class OptimizationStatus(str, PyEnum):
    """Статусы оптимизации расписания."""
    PENDING = "pending"           # Ожидает обработки
    IN_PROGRESS = "in_progress"   # В процессе
    COMPLETED = "completed"       # Завершена успешно
    FAILED = "failed"             # Завершена с ошибкой
    CANCELLED = "cancelled"       # Отменена


class RecommendationType(str, PyEnum):
    """Типы рекомендаций."""
    FILL_GAP = "fill_gap"         # Заполнить пробел в расписании
    PEAK_HOURS = "peak_hours"     # Разместить в пиковые часы
    VARIETY = "variety"           # Добавить разнообразие
    PERFORMANCE = "performance"   # Улучшить вовлеченность
    CONFLICT = "conflict"         # Разрешить конфликт


class ScheduleOptimization(Base):
    """
    Результат оптимизации расписания.

    Хранит результаты оптимизации, метрики производительности
    и предложения по улучшению расписания.
    """
    __tablename__ = "schedule_optimizations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Привязка к каналу
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    # Пользователь, инициировавший оптимизацию
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Временной диапазон оптимизации
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)

    # Статус оптимизации
    status = Column(
        Enum(OptimizationStatus, values_callable=lambda x: [e.value for e in x]),
        default=OptimizationStatus.PENDING,
        nullable=False,
        index=True
    )

    # Метрики оптимизации (JSON)
    # Формат: {
    #   "gap_hours": 12.5,              # Количество часов без контента
    #   "coverage_percent": 85.2,       # Покрытие расписания (%)
    #   "engagement_score": 7.8,        # Оценка вовлеченности (0-10)
    #   "variety_score": 6.5,           # Оценка разнообразия (0-10)
    #   "conflicts_resolved": 3,        # Количество разрешенных конфликтов
    #   "total_slots": 42,              # Общее количество слотов
    #   "peak_hours_coverage": 95.0     # Покрытие пиковых часов (%)
    # }
    metrics = Column(JSONB, nullable=True)

    # Предложения по расписанию (JSON)
    # Формат: [
    #   {
    #     "action": "add|modify|remove",
    #     "slot_id": "uuid",
    #     "start_time": "09:00",
    #     "end_time": "12:00",
    #     "playlist_id": "uuid",
    #     "reason": "Высокая вовлеченность в утренние часы",
    #     "priority": 8
    #   },
    #   ...
    # ]
    suggestions = Column(JSONB, nullable=True)

    # Параметры оптимизации (JSON)
    # Формат: {
    #   "maximize_engagement": true,
    #   "minimize_gaps": true,
    #   "balance_variety": true,
    #   "respect_priority": true,
    #   "target_hours": 24
    # }
    parameters = Column(JSONB, nullable=True)

    # Результат применения (JSON)
    # Формат: {
    #   "slots_created": 5,
    #   "slots_modified": 3,
    #   "slots_removed": 1,
    #   "gaps_filled": 4,
    #   "conflicts_resolved": 2
    # }
    applied_changes = Column(JSONB, nullable=True)

    # Ошибки и предупреждения
    error_message = Column(Text, nullable=True)
    warnings = Column(JSONB, nullable=True)  # ["...", "..."]

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    channel = relationship("Channel", backref="schedule_optimizations")
    user = relationship("User", foreign_keys=[user_id])
    recommendations = relationship(
        "ScheduleRecommendation",
        backref="optimization",
        cascade="all, delete-orphan",
        order_by="ScheduleRecommendation.priority.desc()"
    )

    def __repr__(self):
        return f"<ScheduleOptimization {self.id}: {self.channel_id} {self.start_date}-{self.end_date} ({self.status})>"


class ScheduleRecommendation(Base):
    """
    AI-рекомендация по размещению контента.

    Хранит отдельные рекомендации с оценками и метриками
    для принятия решений пользователем.
    """
    __tablename__ = "schedule_recommendations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Привязка к оптимизации (опционально - может быть самостоятельной)
    optimization_id = Column(GUID(), ForeignKey("schedule_optimizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Привязка к каналу
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    # Тип рекомендации
    rec_type = Column(
        Enum(RecommendationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # Что рекомендуется разместить
    playlist_id = Column(GUID(), ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)

    # Где разместить (временной слот)
    recommended_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)  # "HH:MM"
    end_time = Column(String(5), nullable=False)    # "HH:MM"

    # Оценки и метрики
    confidence_score = Column(Numeric(5, 2), nullable=False, default=0.0)  # 0.00-100.00
    expected_engagement = Column(Numeric(5, 2), nullable=True)  # Ожидаемая вовлеченность (0-10)
    expected_listeners = Column(BigInteger, nullable=True)      # Прогноз слушателей

    # Приоритет рекомендации (выше = важнее)
    priority = Column(BigInteger, nullable=False, default=5, index=True)

    # Обоснование рекомендации
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Метаданные для анализа
    # Формат: {
    #   "similar_performances": [playlist_id, ...],
    #   "avg_listeners_at_time": 150,
    #   "historical_engagement": 8.2,
    #   "competitor_analysis": {...},
    #   "trend": "rising|stable|falling"
    # }
    metadata = Column(JSONB, nullable=True)

    # Статус применения
    is_applied = Column(Boolean, default=False, nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Флаги
    is_dismissed = Column(Boolean, default=False)  # Отклонена пользователем
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    channel = relationship("Channel", backref="schedule_recommendations")
    playlist = relationship("Playlist", backref="recommendations")

    # Indexes for performance
    __table_args__ = (
        Index('idx_recommendations_channel_date', 'channel_id', 'recommended_date'),
        Index('idx_recommendations_type_priority', 'rec_type', 'priority'),
        Index('idx_recommendations_applied', 'is_applied', 'is_dismissed'),
    )

    def __repr__(self):
        return f"<ScheduleRecommendation {self.id}: {self.rec_type} {self.recommended_date} {self.start_time}-{self.end_time} (confidence: {self.confidence_score})>"


class PeakHoursAnalytics(Base):
    """
    Аналитика пиковых часов прослушивания.

    Хранит агрегированные данные о пиковых часах
    для оптимизации расписания.
    """
    __tablename__ = "peak_hours_analytics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Привязка к каналу
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    # День недели (0=понедельник, 6=воскресенье)
    day_of_week = Column(BigInteger, nullable=False, index=True)

    # Час суток (0-23)
    hour = Column(BigInteger, nullable=False, index=True)

    # Метрики за период
    total_plays = Column(BigInteger, nullable=False, default=0)
    avg_listeners = Column(Numeric(10, 2), nullable=False, default=0)
    peak_listeners = Column(BigInteger, nullable=False, default=0)
    avg_duration_seconds = Column(BigInteger, nullable=False, default=0)

    # Уникальные треки за этот час
    unique_tracks_count = Column(BigInteger, nullable=False, default=0)

    # Период анализа
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    sample_size = Column(BigInteger, nullable=False, default=0)  # Количество дней в выборке

    # Аудит
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    channel = relationship("Channel", backref="peak_hours_analytics")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_peak_hours_channel_day_hour', 'channel_id', 'day_of_week', 'hour'),
        Index('idx_peak_hours_period', 'period_start', 'period_end'),
    )

    def __repr__(self):
        return f"<PeakHoursAnalytics(ch={self.channel_id}, dow={self.day_of_week}, hour={self.hour}, avg_listeners={self.avg_listeners})>"
