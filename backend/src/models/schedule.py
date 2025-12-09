"""
Модели для системы расписания трансляций.
Позволяет привязывать плейлисты к временным слотам календаря.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, DateTime, Date, Time, 
    ForeignKey, Boolean, Enum, Integer, Text,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class RepeatType(str, PyEnum):
    """Типы повторения расписания."""
    NONE = "none"           # Без повторения (однократно)
    DAILY = "daily"         # Ежедневно
    WEEKLY = "weekly"       # Еженедельно (тот же день недели)
    WEEKDAYS = "weekdays"   # По будням (Пн-Пт)
    WEEKENDS = "weekends"   # По выходным (Сб-Вс)
    CUSTOM = "custom"       # Пользовательский (указать дни)


class ScheduleSlot(Base):
    """
    Слот расписания — привязка плейлиста/контента к временному интервалу.
    
    Пример использования:
    - Понедельник 09:00-12:00 -> Плейлист "Утреннее шоу"
    - Ежедневно 20:00-22:00 -> Плейлист "Вечерний эфир"
    """
    __tablename__ = "schedule_slots"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Привязка к каналу (обязательно)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Привязка к плейлисту (опционально - можно указать позже)
    playlist_id = Column(GUID(), ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    
    # Временные параметры слота
    start_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Повторение
    repeat_type = Column(Enum(RepeatType), default=RepeatType.NONE, nullable=False)
    repeat_days = Column(JSON, nullable=True)  # [0,1,2,3,4] для пн-пт (0=понедельник)
    repeat_until = Column(Date, nullable=True)  # До какой даты повторять
    
    # Метаданные для отображения
    title = Column(String(255), nullable=True)  # Название слота (опционально)
    description = Column(Text, nullable=True)   # Описание
    color = Column(String(7), default="#3B82F6")  # HEX цвет для календаря
    
    # Управление
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0)  # Приоритет при пересечении (выше = важнее)
    
    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    channel = relationship("Channel", backref="schedule_slots")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ScheduleSlot {self.id}: {self.start_date} {self.start_time}-{self.end_time}>"


class ScheduleTemplate(Base):
    """
    Шаблон расписания — набор слотов для быстрого применения.
    
    Позволяет:
    - Сохранить типовое расписание дня/недели
    - Быстро применить на выбранные даты
    - Делиться шаблонами между каналами
    """
    __tablename__ = "schedule_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Владелец шаблона
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Привязка к каналу (опционально - можно сделать общий шаблон)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    
    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Слоты шаблона в формате JSON
    # Формат: [
    #   {"start_time": "09:00", "end_time": "12:00", "playlist_id": "uuid", "title": "...", "color": "#..."},
    #   ...
    # ]
    slots = Column(JSON, nullable=False, default=list)
    
    # Флаги
    is_public = Column(Boolean, default=False)  # Доступен другим пользователям
    
    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="schedule_templates")
    channel = relationship("Channel", backref="schedule_templates")

    def __repr__(self):
        return f"<ScheduleTemplate {self.id}: {self.name}>"


class PlaylistGroup(Base):
    """
    Группа плейлистов — для логической организации плейлистов.
    
    Примеры:
    - "Музыка для медитации"
    - "Karunesh Discography"
    - "Утренние эфиры"
    """
    __tablename__ = "playlist_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Владелец группы
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Привязка к каналу (опционально — группа может быть общей)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    
    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366F1")  # Индиго по умолчанию
    icon = Column(String(50), default="folder")   # Иконка группы
    
    # Порядок сортировки
    position = Column(Integer, default=0)
    
    # Флаги
    is_expanded = Column(Boolean, default=True)   # Развёрнута ли группа в UI
    is_active = Column(Boolean, default=True)
    
    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="playlist_groups")
    channel = relationship("Channel", backref="playlist_groups")
    playlists = relationship("Playlist", back_populates="group", order_by="Playlist.position")

    def __repr__(self):
        return f"<PlaylistGroup {self.id}: {self.name}>"


class Playlist(Base):
    """
    Плейлист — коллекция треков/видео для трансляции.
    
    Отличается от PlaylistItem тем, что это контейнер,
    а не отдельный элемент очереди.
    """
    __tablename__ = "playlists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Владелец
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Привязка к каналу (опционально)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    
    # Привязка к группе (опционально)
    group_id = Column(GUID(), ForeignKey("playlist_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Порядок сортировки внутри группы
    position = Column(Integer, default=0)
    
    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#8B5CF6")  # Фиолетовый по умолчанию
    
    # Источник плейлиста
    source_type = Column(String(50), default="manual")  # manual, youtube, m3u, folder
    source_url = Column(String(2048), nullable=True)    # URL источника (YouTube playlist, m3u)
    
    # Элементы плейлиста (JSON массив)
    # Формат: [
    #   {"url": "...", "title": "...", "duration": 180, "type": "youtube"},
    #   ...
    # ]
    items = Column(JSON, nullable=False, default=list)
    
    # Статистика
    total_duration = Column(Integer, default=0)  # Общая длительность в секундах
    items_count = Column(Integer, default=0)     # Количество элементов
    
    # Флаги
    is_active = Column(Boolean, default=True)
    is_shuffled = Column(Boolean, default=False)  # Перемешивать при воспроизведении
    
    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="playlists")
    channel = relationship("Channel", backref="playlists")
    group = relationship("PlaylistGroup", back_populates="playlists")

    def __repr__(self):
        return f"<Playlist {self.id}: {self.name} ({self.items_count} items)>"

    def __init__(self, *args, **kwargs):
        # Ensure items and stats are computed when created via constructor
        items = kwargs.get('items') or []
        # If caller didn't provide explicit items_count/total_duration, compute them
        if 'items_count' not in kwargs:
            kwargs['items_count'] = len(items)
        if 'total_duration' not in kwargs:
            kwargs['total_duration'] = sum(item.get('duration', 0) for item in items)
        super().__init__(*args, **kwargs)
