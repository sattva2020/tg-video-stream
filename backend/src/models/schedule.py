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
    func, BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB
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


class PlaylistRepeatMode(str, PyEnum):
    """Режимы воспроизведения плейлиста."""
    NONE = "none"           # Без повтора (остановиться после последнего трека)
    ONE = "one"             # Повторять один трек
    ALL = "all"             # Повторять весь плейлист (зациклить)


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
    
    # Повторение (используем values_callable для передачи .value вместо .name)
    repeat_type = Column(
        Enum(RepeatType, values_callable=lambda x: [e.value for e in x]),
        default=RepeatType.NONE,
        nullable=False
    )
    repeat_days = Column(JSONB, nullable=True)  # [0,1,2,3,4] для пн-пт (0=понедельник)
    repeat_until = Column(Date, nullable=True)  # До какой даты повторять
    
    # Метаданные для отображения
    title = Column(String(255), nullable=True)  # Название слота (опционально)
    description = Column(Text, nullable=True)   # Описание
    color = Column(String(7), default="#3B82F6")  # HEX цвет для календаря
    
    # Управление
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(BigInteger, default=0)  # Приоритет при пересечении (выше = важнее)
    
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
    slots = Column(JSONB, nullable=False, default=list)
    
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


class PlaylistTemplate(Base):
    """
    Шаблон плейлиста — сохранённая структура плейлиста для быстрого создания.

    Позволяет:
    - Сохранить часто используемые наборы треков/видео
    - Быстро создавать новые плейлисты на основе шаблона
    - Делиться шаблонами между пользователями
    """
    __tablename__ = "playlist_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Владелец шаблона
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Привязка к каналу (опционально - можно сделать общий шаблон)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)

    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Элементы шаблона плейлиста в формате JSON
    # Формат: [
    #   {"url": "...", "title": "...", "duration": 180, "type": "youtube"},
    #   ...
    # ]
    items = Column(JSONB, nullable=False, default=list)

    # Статистика
    total_duration = Column(BigInteger, default=0)  # Общая длительность в секундах
    items_count = Column(BigInteger, default=0)     # Количество элементов

    # Флаги
    is_public = Column(Boolean, default=False)  # Доступен другим пользователям

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="playlist_templates")
    channel = relationship("Channel", backref="playlist_templates")

    def __repr__(self):
        return f"<PlaylistTemplate {self.id}: {self.name} ({self.items_count} items)>"

    def __init__(self, *args, **kwargs):
        # Ensure items and stats are computed when created via constructor
        items = kwargs.get('items') or []
        # If caller didn't provide explicit items_count/total_duration, compute them
        if 'items_count' not in kwargs:
            kwargs['items_count'] = len(items)
        if 'total_duration' not in kwargs:
            kwargs['total_duration'] = sum(item.get('duration', 0) for item in items)
        super().__init__(*args, **kwargs)


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

    # Привязка к родительской группе (для вложенных папок)
    parent_id = Column(GUID(), ForeignKey("playlist_groups.id", ondelete="SET NULL"), nullable=True, index=True)

    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366F1")  # Индиго по умолчанию
    icon = Column(String(50), default="folder")   # Иконка группы
    
    # Порядок сортировки
    position = Column(BigInteger, default=0)
    
    # Флаги
    is_expanded = Column(Boolean, default=True)   # Развёрнута ли группа в UI
    is_active = Column(Boolean, default=True)
    
    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="playlist_groups")
    channel = relationship("Channel", backref="playlist_groups")
    parent = relationship("PlaylistGroup", remote_side=[id], back_populates="children")
    children = relationship("PlaylistGroup", back_populates="parent", cascade="all, delete-orphan")
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
    position = Column(BigInteger, default=0)
    
    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#8B5CF6")  # Фиолетовый по умолчанию

    # Режим повтора при воспроизведении
    repeat_mode = Column(
        Enum(PlaylistRepeatMode, values_callable=lambda x: [e.value for e in x]),
        default=PlaylistRepeatMode.NONE,
        nullable=False
    )

    # Источник плейлиста
    source_type = Column(String(50), default="manual")  # manual, youtube, m3u, folder, gdrive_folder
    source_url = Column(String(2048), nullable=True)    # URL источника (YouTube playlist, m3u)
    
    # Элементы плейлиста (JSON массив)
    # Формат: [
    #   {"url": "...", "title": "...", "duration": 180, "type": "youtube"},
    #   ...
    # ]
    items = Column(JSONB, nullable=False, default=list)
    
    # Статистика
    total_duration = Column(BigInteger, default=0)  # Общая длительность в секундах
    items_count = Column(BigInteger, default=0)     # Количество элементов
    
    # Флаги
    is_active = Column(Boolean, default=True)
    is_shuffled = Column(Boolean, default=False)  # Перемешивать при воспроизведении
    is_public = Column(Boolean, default=False)     # Доступен другим пользователям
    share_code = Column(String(32), unique=True, nullable=True, index=True)  # Код для шаринга
    
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


class SmartPlaylist(Base):
    """
    Умный плейлист — плейлист с автоформлением по критериям.

    Позволяет:
    - Создавать плейлисты на основе правил и фильтров
    - Автоматически обновлять содержимое по расписанию
    - Фильтровать по тегам, жанрам, артистам, длительности и т.д.

    Примеры критериев:
    - {"genre": "meditation", "duration_min": 300, "duration_max": 1800}
    - {"tags": ["ambient", "chill"], "added_after": "2024-01-01"}
    - {"artist": "Karunesh", "order_by": "date_added", "limit": 50}
    """
    __tablename__ = "smart_playlists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Владелец умного плейлиста
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Привязка к каналу (опционально)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)

    # Привязка к группе (опционально)
    group_id = Column(GUID(), ForeignKey("playlist_groups.id", ondelete="SET NULL"), nullable=True, index=True)

    # Ссылка на автоматически создаваемый плейлист
    playlist_id = Column(GUID(), ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True, index=True)

    # Порядок сортировки внутри группы
    position = Column(BigInteger, default=0)

    # Метаданные
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#10B981")  # Изумрудный по умолчанию

    # Критерии формирования плейлиста (JSONB)
    # Формат: {
    #   "filters": {
    #     "genre": ["meditation", "ambient"],
    #     "tags": ["chill", "relax"],
    #     "artist": "Karunesh",
    #     "duration_min": 300,
    #     "duration_max": 1800,
    #     "added_after": "2024-01-01",
    #     "added_before": "2024-12-31"
    #   },
    #   "order_by": "date_added",  # date_added, duration, name, artist
    #   "order_direction": "desc",  # asc, desc
    #   "limit": 100,  # Максимум треков
    #   "shuffle": false  # Перемешать результат
    # }
    criteria = Column(JSONB, nullable=False, default=dict)

    # Автообновление
    auto_update = Column(Boolean, default=False)  # Включено ли автообновление
    auto_update_interval = Column(Integer, default=24)  # Интервал в часах
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)  # Последнее обновление

    # Статистика (вычисляется при обновлении)
    items_count = Column(BigInteger, default=0)  # Количество элементов в плейлисте
    total_duration = Column(BigInteger, default=0)  # Общая длительность в секундах

    # Флаги
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Доступен другим пользователям

    # Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="smart_playlists")
    channel = relationship("Channel", backref="smart_playlists")
    group = relationship("PlaylistGroup", backref="smart_playlists")
    playlist = relationship("Playlist", foreign_keys=[playlist_id])

    def __repr__(self):
        return f"<SmartPlaylist {self.id}: {self.name} ({self.items_count} items)>"

    @property
    def needs_refresh(self):
        """Проверяет, пора ли обновить умный плейлист."""
        if not self.auto_update:
            return False
        if not self.last_refreshed_at:
            return True
        from datetime import timedelta
        return datetime.now() - self.last_refreshed_at > timedelta(hours=self.auto_update_interval)
