"""
FilePath Value Object для валидации путей к файлам (T019).

**Architecture Layer**: Domain
**Dependencies**: pathlib (stdlib)
**Usage**: Track Entity, playlist management.
"""

from dataclasses import dataclass
from pathlib import Path

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class FilePath(ValueObject):
    """
    Путь к файлу с валидацией расширения.

    **Validation**:
    - Не пустой путь
    - Содержит расширение файла
    - Опционально: проверка разрешённых расширений

    **Design Decision**: Не проверяем существование файла в конструкторе
    (Domain не знает о файловой системе), но валидируем формат.

    Examples:
        >>> file_path = FilePath("/path/to/audio.mp3")
        >>> file_path.extension
        '.mp3'

        >>> FilePath("")
        ValidationError: FilePath cannot be empty

        >>> FilePath("/path/without/extension")
        ValidationError: FilePath must have file extension
    """

    value: str

    # Разрешённые расширения аудио/видео файлов
    ALLOWED_EXTENSIONS = {
        ".mp3",
        ".mp4",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
        ".avi",
        ".mkv",
        ".mov",
    }

    def __post_init__(self):
        """Валидация file path при создании."""
        if not self.value or not self.value.strip():
            raise ValidationError("FilePath cannot be empty")

        path = Path(self.value)
        if not path.suffix:
            raise ValidationError(
                f"FilePath must have file extension: {self.value}"
            )

        # Опциональная проверка разрешённых расширений
        # (закомментировано, т.к. может быть слишком strict для domain)
        # if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
        #     raise ValidationError(
        #         f"Invalid file extension: {path.suffix}. "
        #         f"Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
        #     )

    @property
    def extension(self) -> str:
        """Возвращает расширение файла (e.g., '.mp3')."""
        return Path(self.value).suffix.lower()

    @property
    def name(self) -> str:
        """Возвращает имя файла с расширением (e.g., 'audio.mp3')."""
        return Path(self.value).name

    @property
    def name_without_extension(self) -> str:
        """Возвращает имя файла без расширения (e.g., 'audio')."""
        return Path(self.value).stem

    def is_audio(self) -> bool:
        """True если файл - аудио формат."""
        return self.extension in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

    def is_video(self) -> bool:
        """True если файл - видео формат."""
        return self.extension in {".mp4", ".avi", ".mkv", ".mov"}

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return self.value
