"""
Feature 009 Phase 1: Adaptive Stream Configuration Model

Модель для конфигурации адаптивного битрейта, включая пороги пропускной способности
и правила для различных типов устройств.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, ForeignKey, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class AdaptiveStreamConfig(Base):
    """
    Конфигурация адаптивного битрейта для потока

    Используется для:
    - Автоматического регулирования качества на основе пропускной способности
    - Применения различных профилей качества для разных устройств
    - Настройки порогов переключения между уровнями качества

    **Quality Levels**: low (360p), medium (480p), high (720p), ultra (1080p)
    """
    __tablename__ = "adaptive_stream_config"

    __table_args__ = (
        CheckConstraint(
            "default_quality IN ('low', 'medium', 'high', 'ultra')",
            name='ck_asc_default_quality'
        ),
        CheckConstraint(
            "min_quality IN ('low', 'medium', 'high', 'ultra')",
            name='ck_asc_min_quality'
        ),
        CheckConstraint(
            "max_quality IN ('low', 'medium', 'high', 'ultra')",
            name='ck_asc_max_quality'
        ),
    )

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    # Foreign Key to Stream
    stream_id = Column(GUID(), ForeignKey("streams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Quality Settings
    enabled = Column(Boolean, default=True, nullable=False, comment="Включена ли адаптивная трансляция")
    default_quality = Column(String(20), default="high", nullable=False, comment="Качество по умолчанию")
    min_quality = Column(String(20), default="low", nullable=False, comment="Минимальное качество")
    max_quality = Column(String(20), default="ultra", nullable=False, comment="Максимальное качество")

    # Bandwidth Thresholds (Kbps)
    # Пороги пропускной способности для переключения между качествами
    bandwidth_threshold_low_kbps = Column(Integer, default=500, nullable=False, comment="Порог для low quality (Kbps)")
    bandwidth_threshold_medium_kbps = Column(Integer, default=1500, nullable=False, comment="Порог для medium quality (Kbps)")
    bandwidth_threshold_high_kbps = Column(Integer, default=3000, nullable=False, comment="Порог для high quality (Kbps)")
    bandwidth_threshold_ultra_kbps = Column(Integer, default=6000, nullable=False, comment="Порог для ultra quality (Kbps)")

    # Adaptive Settings
    adaptation_interval_seconds = Column(Integer, default=30, nullable=False, comment="Интервал проверки пропускной способности (сек)")
    bandwidth_smoothing_factor = Column(Float, default=0.3, nullable=False, comment="Коэффициент сглаживания измерений (0-1)")
    consecutive_measurements_required = Column(Integer, default=3, nullable=False, comment="Количество последовательных измерений для переключения")

    # Device-specific rules (JSONB)
    # Формат: {"mobile": {"max_quality": "high", "bandwidth_multiplier": 0.7}, "desktop": {...}}
    device_rules = Column(JSONB, default={}, nullable=True, comment="Правила для различных типов устройств")

    # Quality Profiles (JSONB)
    # Формат: {"low": {"resolution": "640x360", "video_bitrate": 500, "audio_bitrate": 64}, ...}
    quality_profiles = Column(JSONB, default={}, nullable=True, comment="Пользовательские профили качества")

    # Monitoring Settings
    enable_bandwidth_monitoring = Column(Boolean, default=True, nullable=False)
    enable_quality_logging = Column(Boolean, default=True, nullable=False)

    # Statistics (JSONB)
    # Формат: {"quality_changes": 5, "last_quality": "high", "avg_bandwidth_kbps": 2500}
    statistics = Column(JSONB, default={}, nullable=True, comment="Статистика адаптивной трансляции")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    stream = relationship("src.models.stream.Stream", back_populates="adaptive_config", lazy="joined")

    def __repr__(self) -> str:
        return f"<AdaptiveStreamConfig(id={self.id}, stream_id={self.stream_id}, enabled={self.enabled}, default_quality='{self.default_quality}')>"
