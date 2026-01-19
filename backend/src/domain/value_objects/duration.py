"""
Duration Value Object для временных интервалов (T018).

**Architecture Layer**: Domain
**Dependencies**: timedelta (stdlib)
**Usage**: Stream scheduling, playlist duration calculations.
"""

from dataclasses import dataclass
from datetime import timedelta

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Duration(ValueObject):
    """
    Временной интервал с валидацией положительности.

    **Validation**: Duration должен быть > 0 (non-negative).
    **Representation**: Внутри хранится timedelta, но API в seconds.

    **Design Decision**: Используем seconds как primary interface
    (проще для API/DB serialization), но timedelta для calculations.

    Examples:
        >>> duration = Duration.from_seconds(3600)  # 1 hour
        >>> duration.to_minutes()
        60.0

        >>> Duration.from_seconds(-10)
        ValidationError: Duration must be positive, got -10
    """

    seconds: int

    def __post_init__(self):
        """Валидация положительности duration."""
        if self.seconds <= 0:
            raise ValidationError(f"Duration must be positive, got {self.seconds}")

    @staticmethod
    def from_seconds(seconds: int) -> "Duration":
        """Создаёт Duration из секунд."""
        return Duration(seconds=seconds)

    @staticmethod
    def from_minutes(minutes: int) -> "Duration":
        """Создаёт Duration из минут."""
        return Duration(seconds=minutes * 60)

    @staticmethod
    def from_hours(hours: int) -> "Duration":
        """Создаёт Duration из часов."""
        return Duration(seconds=hours * 3600)

    def to_timedelta(self) -> timedelta:
        """Конвертирует в timedelta для datetime операций."""
        return timedelta(seconds=self.seconds)

    def to_minutes(self) -> float:
        """Возвращает duration в минутах (с дробной частью)."""
        return self.seconds / 60

    def to_hours(self) -> float:
        """Возвращает duration в часах (с дробной частью)."""
        return self.seconds / 3600

    def add(self, other: "Duration") -> "Duration":
        """
        Складывает две duration (immutable operation).

        Returns:
            Новый Duration объект с суммой.
        """
        return Duration(seconds=self.seconds + other.seconds)

    def subtract(self, other: "Duration") -> "Duration":
        """
        Вычитает duration (immutable operation).

        Returns:
            Новый Duration объект с разностью.

        Raises:
            ValidationError: Если результат <= 0.
        """
        new_seconds = self.seconds - other.seconds
        if new_seconds <= 0:
            raise ValidationError(
                f"Duration subtraction resulted in non-positive value: {new_seconds}"
            )
        return Duration(seconds=new_seconds)

    def __str__(self) -> str:
        """Human-readable representation (HH:MM:SS)."""
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
