"""
PlaylistMapper - преобразование Playlist Entity ↔ PlaylistItem ORM (T055).

**Architecture Layer**: Infrastructure / Persistence
**Pattern**: Aggregate/Disaggregate Mapper для Aggregate Root с коллекциями

Playlist - это **Aggregate Root**, содержащий коллекцию Track entities.
ORM использует normalized schema (playlist_items table с FK на streams).

**Mapping Strategy**:
- to_entity(): Агрегация List[PlaylistItemORM] → Playlist Entity с embedded List[Track]
- to_orm_list(): Дезагрегация Playlist Entity → List[PlaylistItemORM]
- Transaction boundary: Весь aggregate сохраняется/удаляется атомарно

**Usage**:
```python
from src.infrastructure.persistence.mappers import PlaylistMapper

# Загрузка aggregate (ORM rows → Entity)
orm_items = session.query(PlaylistItemORM).filter_by(stream_id=stream_id).all()
playlist = PlaylistMapper.to_entity(orm_items, stream_id)

# Сохранение aggregate (Entity → ORM rows)
orm_items = PlaylistMapper.to_orm_list(playlist)
for item in orm_items:
    session.add(item)
```

**Важно**: Mapper НЕ управляет транзакциями - это ответственность Repository.

**Contract Tests**: backend/tests/integration/persistence/test_playlist_mapper.py
"""

from typing import List, Optional
import uuid

from src.domain.entities.playlist import Playlist
from src.domain.entities.track import Track
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.file_path import FilePath
from src.domain.value_objects.duration import Duration
from src.models.playlist import PlaylistItem as PlaylistItemORM


class PlaylistMapper:
    """
    Mapper для агрегации/дезагрегации Playlist Aggregate Root.
    
    **Aggregate Pattern**: Playlist содержит коллекцию Track, но в БД они normalized (separate rows).
    """

    @staticmethod
    def to_entity(orm_items: List[PlaylistItemORM], stream_id: StreamId) -> Optional[Playlist]:
        """
        Агрегирует множество ORM rows → единый Playlist Entity.

        Args:
            orm_items: Список PlaylistItemORM для одного stream_id
            stream_id: StreamId Value Object (для связи с Stream Aggregate Root)

        Returns:
            Playlist Entity с embedded List[Track] или None если orm_items пустой

        **Type Conversions**:
        - PlaylistItemORM.id (UUID) → Track.id (int) - ВНИМАНИЕ: потеря precision, но Track.id не используется вне контекста
        - PlaylistItemORM.url → Track.file_path (FilePath Value Object)
        - PlaylistItemORM.title → Track.title (string)
        - PlaylistItemORM.duration → Track.duration (Duration Value Object, seconds)
        - PlaylistItemORM.position → Track.order (int, 0-based)

        **Ordering**: Tracks сортируются по position перед агрегацией (BR-006: sequential order)

        Raises:
            ValueError: Если один из треков имеет невалидные данные
        """
        if not orm_items:
            return None

        # Сортируем треки по position для соблюдения порядка (BR-006)
        sorted_items = sorted(orm_items, key=lambda x: x.position)

        # Агрегируем ORM items → Track entities
        tracks = []
        for item in sorted_items:
            # Валидация обязательных полей
            if not item.url:
                raise ValueError(f"PlaylistItem {item.id} must have non-empty url")

            # Конвертируем значения в Value Objects
            try:
                file_path = FilePath(value=item.url)
            except Exception as e:
                raise ValueError(f"Invalid file_path for PlaylistItem {item.id}: {e}") from e

            # Duration может быть None (неизвестная длительность)
            if item.duration is not None and item.duration > 0:
                try:
                    duration = Duration(seconds=item.duration)
                except Exception as e:
                    raise ValueError(f"Invalid duration for PlaylistItem {item.id}: {e}") from e
            else:
                # Fallback для неизвестной длительности (1 second minimum для валидации)
                duration = Duration(seconds=1)

            # Создаём Track Entity
            # ВАЖНО: UUID → int конвертация для Track.id (не критично, Track.id используется только внутри aggregate)
            track_id = hash(item.id) % (10 ** 9)  # Простое преобразование UUID → int
            
            track = Track.create(
                track_id=track_id,
                file_path=file_path,
                title=item.title or "Untitled",  # Fallback для пустого title
                duration=duration,
                order=item.position,
            )
            tracks.append(track)

        # Создаём Playlist Aggregate Root
        # Playlist.id берём из первого item (предполагаем, что все items принадлежат одному playlist)
        playlist_id = hash(sorted_items[0].stream_id) % (10 ** 9)  # stream_id → playlist_id mapping

        playlist = Playlist.create(
            playlist_id=playlist_id,
            stream_id=stream_id,
            tracks=tracks,
        )

        return playlist

    @staticmethod
    def to_orm_list(playlist: Playlist) -> List[PlaylistItemORM]:
        """
        Дезагрегирует Playlist Entity → множество ORM rows.

        Args:
            playlist: Playlist Entity с embedded List[Track]

        Returns:
            List[PlaylistItemORM] для сохранения в БД (separate rows)

        **Type Conversions**:
        - Playlist.stream_id (StreamId UUID) → PlaylistItemORM.stream_id (UUID)
        - Track.file_path (FilePath) → PlaylistItemORM.url (string)
        - Track.title → PlaylistItemORM.title
        - Track.duration (Duration) → PlaylistItemORM.duration (int seconds)
        - Track.order → PlaylistItemORM.position

        **ORM Fields**:
        - id: генерируется uuid.uuid4() для новых треков
        - channel_id: None (Clean Architecture использует stream_id, не channel_id)
        - type: "local" (по умолчанию для файлов)
        - status: "queued" (по умолчанию)
        - created_by: None (не храним в Playlist Entity)

        **Важно**: Не удаляем старые ORM rows - это ответственность Repository (DELETE затем INSERT)
        """
        orm_items = []

        for track in playlist.tracks:
            orm_item = PlaylistItemORM(
                id=uuid.uuid4(),  # Новый UUID для каждой ORM row
                channel_id=None,  # Legacy field, не используется в Clean Architecture
                stream_id=playlist.stream_id.value,  # StreamId.value → UUID
                url=str(track.file_path),  # FilePath → string
                title=track.title,
                type="local",  # Предполагаем локальные файлы по умолчанию
                status="queued",  # Новый трек всегда queued
                duration=track.duration.seconds if track.duration else None,  # Duration → int seconds
                position=track.order,  # Track.order → position
                created_by=None,  # Не храним в Entity
            )
            orm_items.append(orm_item)

        return orm_items

    @staticmethod
    def to_entity_list(orm_items_by_stream: dict[uuid.UUID, List[PlaylistItemORM]]) -> List[Playlist]:
        """
        Пакетная конвертация множества плейлистов (каждый - aggregate root).

        Args:
            orm_items_by_stream: Dict[stream_id, List[PlaylistItemORM]]

        Returns:
            List[Playlist] entities

        **Use Case**: Загрузка плейлистов для нескольких стримов одновременно.

        **Error Handling**: Пропускает невалидные плейлисты с логированием (не прерывает всю операцию).
        """
        playlists = []

        for stream_id_uuid, items in orm_items_by_stream.items():
            try:
                stream_id = StreamId(value=stream_id_uuid)
                playlist = PlaylistMapper.to_entity(items, stream_id)
                if playlist:
                    playlists.append(playlist)
            except Exception as e:
                # TODO: Использовать proper logger вместо print
                print(f"⚠️ PlaylistMapper: Не удалось сконвертировать playlist для stream_id={stream_id_uuid}: {e}")
                continue

        return playlists
