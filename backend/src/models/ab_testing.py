"""
Модели для системы A/B тестирования контента.
Позволяет сравнивать различные варианты контента и измерять их влияние на вовлеченность аудитории.
Feature: 016-a-b-testing-framework-for-content
"""

import uuid
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean,
    Enum, Text, BigInteger, Numeric, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class ABTestStatus(str, PyEnum):
    """Статусы A/B теста."""
    DRAFT = "draft"           # Черновик (не запущен)
    RUNNING = "running"       # Активен (сбор данных)
    PAUSED = "paused"         # Приостановлен
    COMPLETED = "completed"   # Завершен (данные собраны)
    STOPPED = "stopped"       # Остановлен досрочно


class ABTest(Base):
    """
    A/B тест — эксперимент для сравнения вариантов контента.

    Примеры использования:
    - Сравнить два видео для определения более вовлекающего
    - Тестировать разные расписания трансляций
    - Сравнивать конфигурации стрима
    """
    __tablename__ = "ab_tests"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Привязка к каналу (обязательно)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    # Метаданные теста
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)  # Гипотеза теста

    # Статус и управление
    status = Column(
        Enum(ABTestStatus, values_callable=lambda x: [e.value for e in x]),
        default=ABTestStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Временные параметры
    start_time = Column(DateTime(timezone=True), nullable=True)  # Когда запущен
    end_time = Column(DateTime(timezone=True), nullable=True)    # Когда завершен
    planned_duration_hours = Column(BigInteger, nullable=True)   # Планируемая длительность в часах

    # Конфигурация распределения трафика
    # Формат: {"algorithm": "weighted", "auto_stop": true, "min_sample_size": 1000}
    traffic_config = Column(JSONB, nullable=True)

    # Результаты теста
    winner_variant_id = Column(GUID(), ForeignKey("ab_test_variants.id", ondelete="SET NULL"), nullable=True)
    confidence_level = Column(Numeric(5, 2), nullable=True)  # Уровень доверия (например, 95.00)
    is_significant = Column(Boolean, nullable=True)           # Статистически значимый результат

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    channel = relationship("Channel", backref="ab_tests")
    creator = relationship("User", foreign_keys=[created_by])
    winner_variant = relationship("ABTestVariant", foreign_keys=[winner_variant_id])
    variants = relationship("ABTestVariant", back_populates="test", cascade="all, delete-orphan", order_by="ABTestVariant.position")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ab_tests_channel_status', 'channel_id', 'status'),
        Index('idx_ab_tests_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ABTest {self.id}: {self.name} ({self.status})>"


class ABTestVariant(Base):
    """
    Вариант A/B теста — один из тестируемых вариантов.

    Примеры:
    - Вариант A: видео с коротким вступлением
    - Вариант B: видео с длинным вступлением
    """
    __tablename__ = "ab_test_variants"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Привязка к тесту
    test_id = Column(GUID(), ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False, index=True)

    # Порядок отображения
    position = Column(BigInteger, default=0)

    # Метаданные варианта
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Распределение трафика
    traffic_allocation = Column(BigInteger, nullable=False, default=50)  # Процент трафика (0-100)

    # Конфигурация варианта (зависит от типа теста)
    # Формат: {
    #   "type": "playlist",  # или "schedule", "stream_config"
    #   "playlist_id": "uuid",
    #   "schedule_settings": {...},
    #   "stream_config": {...}
    # }
    configuration = Column(JSONB, nullable=False, default=dict)

    # Результаты
    is_winner = Column(Boolean, default=False, nullable=False)
    conversion_rate = Column(Numeric(10, 4), nullable=True)  # Конверсия (0.0000 - 1.0000)
    improvement = Column(Numeric(10, 2), nullable=True)      # Улучшение в % относительно baseline

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    test = relationship("ABTest", back_populates="variants")
    metrics = relationship("ABTestMetric", back_populates="variant", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ab_test_variants_test_position', 'test_id', 'position'),
    )

    def __repr__(self):
        return f"<ABTestVariant {self.id}: {self.name} ({self.traffic_allocation}% traffic)>"


class ABTestMetric(Base):
    """
    Метрика A/B теста — измеряемый показатель для варианта.

    Примеры метрик:
    - Impressions (просмотры)
    - Clicks (клики)
    - Conversions (конверсии)
    - Watch time (время просмотра)
    - Peak listeners (пик слушателей)
    """
    __tablename__ = "ab_test_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Привязка к варианту
    variant_id = Column(GUID(), ForeignKey("ab_test_variants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Тип метрики
    metric_type = Column(String(50), nullable=False, index=True)  # impressions, clicks, conversions, etc.

    # Значение метрики
    metric_value = Column(BigInteger, nullable=False, default=0)

    # Время записи метрики
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Дополнительные данные (опционально)
    # Формат: {"metadata_key": "value"}
    metadata = Column(JSONB, nullable=True)

    # Relationships
    variant = relationship("ABTestVariant", back_populates="metrics")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ab_test_metrics_variant_type', 'variant_id', 'metric_type'),
        Index('idx_ab_test_metrics_recorded_at', 'recorded_at'),
    )

    def __repr__(self):
        return f"<ABTestMetric(id={self.id}, type={self.metric_type}, value={self.metric_value})>"
