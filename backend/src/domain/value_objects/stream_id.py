"""
StreamId Value Object для уникальной идентификации стримов (T016).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Stream Entity (Aggregate Root) как типобезопасный ID.
"""

from dataclasses import dataclass
from typing import Union
from uuid import UUID, uuid4

from src.domain.errors import ValidationError
from src.shared.kernel.result import Result
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class StreamId(ValueObject):
    """
    Уникальный идентификатор стрима (UUID).

    **Immutability**: Frozen dataclass (неизменяемый после создания).
    **Validation**: Проверяет валидность UUID при создании.
    **Type Safety**: Предотвращает передачу String вместо StreamId.

    Examples:
        >>> stream_id = StreamId.generate()
        >>> stream_id.value
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> StreamId.from_string("invalid")
        ValidationError: Invalid UUID format
    """

    value: UUID

    def __post_init__(self):
        """Валидация UUID при создании."""
        if not isinstance(self.value, UUID):
            raise ValidationError(f"StreamId must be UUID, got {type(self.value)}")

    @staticmethod
    def generate() -> "StreamId":
        """Генерирует новый уникальный StreamId."""
        return StreamId(value=uuid4())

    @staticmethod
    def create(value: Union[UUID, str]) -> Result["StreamId", ValidationError]:
        """
        Создаёт StreamId с Result pattern для явной обработки ошибок.
        
        Args:
            value: UUID объект или строка UUID
            
        Returns:
            Result[StreamId, ValidationError]
        """
        if isinstance(value, UUID):
            return Result.success(StreamId(value=value))
        
        if isinstance(value, str):
            try:
                return Result.success(StreamId(value=UUID(value)))
            except (ValueError, AttributeError):
                return Result.failure(
                    ValidationError(f"Invalid UUID format: {value}")
                )
        
        return Result.failure(
            ValidationError(f"StreamId must be UUID or string, got {type(value)}")
        )

    @staticmethod
    def from_string(id_str: str) -> "StreamId":
        """
        Создаёт StreamId из string representation.

        Args:
            id_str: UUID в формате строки

        Raises:
            ValidationError: Если строка не является валидным UUID.
        """
        try:
            return StreamId(value=UUID(id_str))
        except (ValueError, AttributeError) as e:
            raise ValidationError(f"Invalid UUID format: {id_str}") from e

    def to_string(self) -> str:
        """Возвращает string representation UUID."""
        return str(self.value)

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return self.to_string()
