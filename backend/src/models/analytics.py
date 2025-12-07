"""
Analytics models for tracking plays and monthly statistics.
Feature: 021-admin-analytics-menu
"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, BigInteger, DateTime, Date, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class TrackPlay(Base):
    """
    Запись о воспроизведении трека.
    Основной источник данных для аналитики.
    """
    __tablename__ = "track_plays"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Ссылка на playlist_items.id (UUID)
    playlist_item_id = Column(GUID(), ForeignKey("playlist_items.id", ondelete="SET NULL"), nullable=True, index=True)
    # Время начала воспроизведения
    played_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    # Длительность воспроизведения в секундах (может быть NULL если неизвестно)
    duration_seconds = Column(Integer, nullable=True)
    # Количество слушателей в момент воспроизведения
    listeners_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    playlist_item = relationship("PlaylistItem", backref="plays")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_track_plays_played_at', 'played_at'),
        Index('idx_track_plays_playlist_item', 'playlist_item_id'),
    )
    
    def __repr__(self):
        return f"<TrackPlay(id={self.id}, played_at={self.played_at}, listeners={self.listeners_count})>"


class MonthlyAnalytics(Base):
    """
    Агрегированные данные за месяц.
    Хранятся после того, как детальные данные удаляются (>90 дней).
    """
    __tablename__ = "monthly_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Первый день месяца
    month = Column(Date, nullable=False, unique=True, index=True)
    # Общее количество воспроизведений
    total_plays = Column(Integer, nullable=False, default=0)
    # Суммарное время вещания в секундах
    total_duration_seconds = Column(BigInteger, nullable=False, default=0)
    # Пиковое количество слушателей
    peak_listeners = Column(Integer, nullable=False, default=0)
    # Среднее количество слушателей
    avg_listeners = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    # Количество уникальных треков
    unique_tracks = Column(Integer, nullable=False, default=0)
    
    def __repr__(self):
        return f"<MonthlyAnalytics(month={self.month}, plays={self.total_plays})>"
