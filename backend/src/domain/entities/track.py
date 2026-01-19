"""
Track Entity - медиа-трек в плейлисте (T023).

**Architecture Layer**: Domain
**Dependencies**: FilePath, Duration Value Objects
**Usage**: Playlist management, streaming.
"""

from dataclasses import dataclass

from src.domain.errors import ValidationError
from src.domain.value_objects.duration import Duration
from src.domain.value_objects.file_path import FilePath
from src.shared.kernel.entity import Entity


@dataclass
class Track:
    """
    Медиа-трек (аудио/видео файл) для вещания.

    **Invariants**:
    - title не пустой
    - order >= 0
    - file_path указывает на существующий файл (проверяется в Infrastructure)

    **Properties**:
    - id: Уникальный идентификатор трека
    - file_path: Путь к медиа-файлу
    - title: Название трека (отображается в UI)
    - duration: Длительность трека
    - order: Порядок в плейлисте (0-based)
    """

    id: int  # Entity identity
    file_path: FilePath
    title: str
    duration: Duration
    order: int

    @staticmethod
    def create(
        track_id: int,
        file_path: FilePath,
        title: str,
        duration: Duration,
        order: int,
    ) -> "Track":
        """
        Factory method для создания трека.

        Args:
            track_id: Уникальный ID трека
            file_path: FilePath Value Object (валидный путь)
            title: Название трека (не пустое)
            duration: Duration Value Object (положительное значение)
            order: Порядок в плейлисте (>= 0)

        Returns:
            Track entity.

        Raises:
            ValidationError: Если title пустой или order < 0.
        """
        if not title or not title.strip():
            raise ValidationError("Track title cannot be empty")

        if order < 0:
            raise ValidationError(f"Track order must be >= 0, got {order}")

        return Track(
            id=track_id,
            file_path=file_path,
            title=title.strip(),
            duration=duration,
            order=order,
        )

    def update_title(self, new_title: str) -> None:
        """
        Обновляет название трека.

        Args:
            new_title: Новое название (не пустое)

        Raises:
            ValidationError: Если new_title пустой.
        """
        if not new_title or not new_title.strip():
            raise ValidationError("Track title cannot be empty")

        self.title = new_title.strip()

    def __str__(self) -> str:
        """Human-readable representation для logging."""
        return f"Track(id={self.id}, title='{self.title}', duration={self.duration})"
