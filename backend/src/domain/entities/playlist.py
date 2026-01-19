"""
Playlist Entity - коллекция треков для стрима (T022).

**Architecture Layer**: Domain
**Dependencies**: StreamId, Track Entity
**Usage**: Playlist management, track scheduling.
"""

from dataclasses import dataclass, field

from src.domain.errors import BusinessRuleViolationError, EntityNotFoundError
from src.domain.value_objects.duration import Duration
from src.domain.value_objects.stream_id import StreamId
from src.shared.kernel.entity import Entity


# Forward reference для Track (избегаем circular import)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.track import Track


@dataclass
class Playlist:
    """
    Плейлист медиа-файлов для вещания.

    **Invariants**:
    - Плейлист содержит минимум 1 трек (не может быть пустым)
    - Все треки имеют уникальный order (автоинкремент)

    **Business Rules**:
    - BR-005: Нельзя удалить последний трек из плейлиста
    - BR-006: Порядок треков должен быть последовательным (0, 1, 2, ...)
    """

    id: int  # Entity identity
    stream_id: StreamId
    tracks: list["Track"] = field(default_factory=list)

    @staticmethod
    def create(
        playlist_id: int,
        stream_id: StreamId,
        tracks: list["Track"],
    ) -> "Playlist":
        """
        Factory method для создания плейлиста.

        Args:
            playlist_id: Уникальный ID плейлиста
            stream_id: ID стрима, которому принадлежит плейлист
            tracks: Список треков (минимум 1)

        Returns:
            Playlist entity с упорядоченными треками.

        Raises:
            BusinessRuleViolationError: Если список треков пустой.
        """
        if not tracks:
            raise BusinessRuleViolationError(
                "Playlist must have at least one track (BR-005)"
            )

        return Playlist(
            id=playlist_id,
            stream_id=stream_id,
            tracks=tracks,
        )

    def add_track(self, track: "Track") -> None:
        """
        Добавляет трек в конец плейлиста.

        **Automatically sets** track.order based on current playlist length.

        Args:
            track: Track entity для добавления
        """
        track.order = len(self.tracks)
        self.tracks.append(track)

    def remove_track(self, index: int) -> None:
        """
        Удаляет трек по индексу.

        **Business Rule BR-005**: Нельзя удалить последний трек.

        Args:
            index: Индекс трека в списке (0-based)

        Raises:
            EntityNotFoundError: Если индекс вне диапазона.
            BusinessRuleViolationError: Если пытаемся удалить последний трек.
        """
        if index < 0 or index >= len(self.tracks):
            raise EntityNotFoundError(
                f"Track index {index} out of range (0-{len(self.tracks) - 1})"
            )

        if len(self.tracks) == 1:
            raise BusinessRuleViolationError(
                "Cannot remove last track from playlist (BR-005)"
            )

        self.tracks.pop(index)
        self._reorder_tracks()

    def get_track(self, index: int) -> "Track | None":
        """
        Возвращает трек по индексу.

        Args:
            index: Индекс трека (0-based)

        Returns:
            Track entity или None если индекс вне диапазона.
        """
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def total_duration(self) -> Duration:
        """
        Вычисляет общую длительность плейлиста.

        Returns:
            Duration объект с суммой всех треков.
        """
        total_seconds = sum(track.duration.seconds for track in self.tracks)
        return Duration.from_seconds(total_seconds)

    def _reorder_tracks(self) -> None:
        """
        Переупорядочивает треки после удаления (0, 1, 2, ...).

        **Private method**: Вызывается внутри remove_track().
        """
        for idx, track in enumerate(self.tracks):
            track.order = idx

    def __len__(self) -> int:
        """Количество треков в плейлисте."""
        return len(self.tracks)
