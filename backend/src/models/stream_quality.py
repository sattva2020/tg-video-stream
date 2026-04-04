"""
Feature 022 Phase 3: Stream Quality History and Alert Models

Модели для сохранения истории качества потока и конфигурации alerts.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, ForeignKey, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base


class StreamQualityHistory(Base):
    """
    Историческое качество потока (каждые 5 минут)
    
    Используется для:
    - Трендовой аналитики
    - Графиков 24 часа
    - Анализа стабильности
    """
    __tablename__ = "stream_quality_history"
    
    __table_args__ = (
        CheckConstraint(
            "overall_quality IN ('low', 'medium', 'high', 'lossless', 'ultra')",
            name='ck_sqh_overall_quality'
        ),
    )
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    
    # Идентификация потока
    stream_url = Column(String(500), index=True, nullable=False)
    stream_name = Column(String(255), nullable=True)  # Человеческое имя потока
    
    # Метрики качества
    audio_codec = Column(String(50), nullable=True)
    audio_bitrate_kbps = Column(Integer, nullable=True)
    audio_sample_rate_hz = Column(Integer, nullable=True)
    audio_channels = Column(Integer, nullable=True)
    audio_quality = Column(String(20), nullable=True)  # low, medium, high, lossless
    
    video_codec = Column(String(50), nullable=True)
    video_bitrate_kbps = Column(Integer, nullable=True)
    video_resolution = Column(String(20), nullable=True)  # "1920x1080"
    video_fps = Column(Float, nullable=True)
    video_quality = Column(String(20), nullable=True)  # low, medium, high, ultra

    # Буферизация
    buffering_percentage = Column(Float, nullable=True)  # Процент буферизации (0-100)

    # Общее качество
    overall_quality = Column(String(20), index=True, nullable=False)  # low, medium, high, lossless, ultra
    is_audio_only = Column(Boolean, default=False)
    is_video_only = Column(Boolean, default=False)
    
    # Статус анализа
    analysis_duration_ms = Column(Integer, nullable=True)  # Время анализа в миллисекундах
    success = Column(Boolean, default=True)  # Успешен ли анализ
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке, если есть
    
    # Время (timezone-aware timestamps)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # JSONB backup исходных данных (на случай изменения структуры)
    raw_data = Column(JSONB, nullable=True)


class QualityAlertConfig(Base):
    """
    Конфигурация alerts для уведомления при падении качества
    
    Например:
    - Alert если quality < "high"
    - Alert если bitrate < 2000 kbps
    - Alert если более 5 минут без анализа
    """
    __tablename__ = "quality_alert_configs"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    
    # Идентификация
    stream_url = Column(String(500), unique=True, index=True, nullable=False)
    stream_name = Column(String(255), nullable=True)
    
    # Пороги качества
    min_overall_quality = Column(String(20), default="medium")  # low, medium, high, lossless, ultra
    min_audio_quality = Column(String(20), nullable=True)
    min_video_quality = Column(String(20), nullable=True)
    
    # Пороги bitrate (Kbps)
    min_audio_bitrate_kbps = Column(Integer, nullable=True)
    min_video_bitrate_kbps = Column(Integer, nullable=True)
    
    # Пороги разрешения
    min_video_resolution = Column(String(20), nullable=True)  # "1280x720", "1920x1080", etc
    min_video_fps = Column(Float, nullable=True)
    
    # Поведение alerts
    enabled = Column(Boolean, default=True)
    notify_on_degradation = Column(Boolean, default=True)  # Отправлять alert при падении
    notify_on_recovery = Column(Boolean, default=True)  # Отправлять alert при восстановлении
    consecutive_failures = Column(Integer, default=3)  # Сколько раз подряд нужно упасть для alert
    
    # Контакты для уведомлений (JSONB с GIN index)
    alert_channels = Column(JSONB, default={})  # {"telegram": [123, 456], "email": ["admin@example.com"]}
    
    # История alerts
    last_alert_at = Column(DateTime, nullable=True)
    last_alert_type = Column(String(50), nullable=True)  # "degradation", "recovery", "offline"
    consecutive_failures_count = Column(Integer, default=0)  # Текущий счётчик
    
    # Meta (timezone-aware timestamps)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QualityTrendSnapshot(Base):
    """
    Снимок тренда каждый час для быстрого доступа к графикам
    
    Вместо запроса всех точек за 24 часа, берём часовые агрегаты
    """
    __tablename__ = "quality_trend_snapshots"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    
    # Идентификация потока
    stream_url = Column(String(500), index=True, nullable=False)
    
    # Час (например, 2025-12-16 14:00:00) - timezone-aware
    hour = Column(DateTime(timezone=True), index=True, nullable=False)
    
    # Агрегированные метрики за час
    audio_quality_avg = Column(String(20), nullable=True)
    audio_bitrate_avg = Column(Float, nullable=True)
    audio_quality_min = Column(String(20), nullable=True)
    audio_bitrate_min = Column(Float, nullable=True)
    
    video_quality_avg = Column(String(20), nullable=True)
    video_bitrate_avg = Column(Float, nullable=True)
    video_resolution = Column(String(20), nullable=True)
    video_fps_avg = Column(Float, nullable=True)
    video_quality_min = Column(String(20), nullable=True)
    video_bitrate_min = Column(Float, nullable=True)
    
    # Общее качество
    overall_quality_avg = Column(String(20), nullable=True)
    overall_quality_min = Column(String(20), nullable=True)
    
    # Статистика
    samples_count = Column(Integer, default=0)  # Сколько sample'ов в этом часу
    success_rate = Column(Float, default=1.0)  # % успешных анализов (0-1)
    
    # Время создания (timezone-aware)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Не может быть двух снимков для одного потока в одном часу
        # (но скорее всего БД сама это обеспечит уникальностью по stream_url + hour)
    )
