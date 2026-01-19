"""
Title Value Object с валидацией длины и формата.

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Stream Entity, Playlist Entity, Track Entity.

**Phase 8**: Clean Architecture - Value Objects
**Reference**: specs/025-clean-architecture-rules/tasks.md T075
"""

from dataclasses import dataclass

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Title(ValueObject):
    """
    Title (название) с валидацией длины и формата.

    **Validation Rules**:
    - Не пустой (после trim)
    - Минимум 1 символ
    - Максимум 255 символов
    - Не только пробелы

    **Normalization**:
    - Удаляются ведущие/замыкающие пробелы
    - Сжимаются множественные пробелы в один

    Examples:
        >>> title = Title("My Stream")
        >>> title.value
        'My Stream'

        >>> Title("   ")
        ValidationError: Title cannot be empty

        >>> Title("a" * 300)
        ValidationError: Title must be at most 255 characters
    """

    value: str

    # Ограничения длины
    MIN_LENGTH = 1
    MAX_LENGTH = 255

    def __post_init__(self):
        """Валидация и нормализация при создании."""
        normalized = self._normalize(self.value)
        
        if not self._is_valid(normalized):
            if not normalized:
                raise ValidationError("Title cannot be empty")
            if len(normalized) > self.MAX_LENGTH:
                raise ValidationError(
                    f"Title must be at most {self.MAX_LENGTH} characters"
                )
            raise ValidationError(f"Invalid title: {self.value}")
        
        # Dataclass frozen=True требует object.__setattr__ для изменения
        object.__setattr__(self, 'value', normalized)

    @classmethod
    def _normalize(cls, title: str) -> str:
        """
        Нормализует title.

        - Strip leading/trailing whitespace
        - Collapse multiple spaces to single
        """
        if not title:
            return ""
        
        # Remove leading/trailing whitespace
        result = title.strip()
        
        # Collapse multiple spaces
        import re
        result = re.sub(r'\s+', ' ', result)
        
        return result

    @classmethod
    def _is_valid(cls, title: str) -> bool:
        """
        Проверяет валидность title.

        **Rules**:
        - Не пустой
        - В пределах допустимой длины
        """
        if not title:
            return False
        
        if len(title) < cls.MIN_LENGTH:
            return False
        
        if len(title) > cls.MAX_LENGTH:
            return False
        
        return True

    @classmethod
    def create(cls, title: str) -> "Title":
        """
        Factory method для создания Title.
        
        Args:
            title: Строка названия
            
        Returns:
            Title value object
            
        Raises:
            ValidationError: Если название невалидно
        """
        return cls(value=title)

    def __str__(self) -> str:
        """Возвращает значение title."""
        return self.value

    def truncate(self, max_length: int, suffix: str = "...") -> "Title":
        """
        Создаёт усечённую версию title.
        
        Args:
            max_length: Максимальная длина
            suffix: Суффикс для усечённого текста
            
        Returns:
            Новый Title (усечённый если нужно)
        """
        if len(self.value) <= max_length:
            return self
        
        truncated = self.value[:max_length - len(suffix)] + suffix
        return Title(value=truncated)

    def is_similar_to(self, other: "Title", threshold: float = 0.8) -> bool:
        """
        Проверяет похожесть двух title (для deduplication).
        
        Простое сравнение по lowercase. Для продвинутого сравнения
        используйте fuzzy matching в Application layer.
        
        Args:
            other: Другой Title для сравнения
            threshold: Порог похожести (не используется в базовой реализации)
            
        Returns:
            True если titles похожи
        """
        return self.value.lower() == other.value.lower()
