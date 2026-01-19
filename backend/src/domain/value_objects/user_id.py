"""
UserId Value Object для уникальной идентификации пользователей (T014).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Используется в User Entity как типобезопасный ID.
"""

from dataclasses import dataclass
from typing import Union
from uuid import UUID, uuid4

from src.domain.errors import ValidationError
from src.shared.kernel.result import Result
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class UserId(ValueObject):
    """
    Уникальный идентификатор пользователя (UUID).

    **Immutability**: Frozen dataclass (неизменяемый после создания).
    **Validation**: Проверяет валидность UUID при создании.
    **Type Safety**: Предотвращает передачу String вместо UserId.

    Examples:
        >>> user_id = UserId.generate()
        >>> user_id.value
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> UserId.from_string("invalid")
        ValidationError: Invalid UUID format
    """

    value: UUID

    def __post_init__(self):
        """Валидация UUID при создании."""
        if not isinstance(self.value, UUID):
            raise ValidationError(f"UserId must be UUID, got {type(self.value)}")

    @staticmethod
    def generate() -> "UserId":
        """Генерирует новый уникальный UserId."""
        return UserId(value=uuid4())

    @staticmethod
    def create(value: Union[UUID, str, int]) -> Result["UserId", ValidationError]:
        """
        Factory method с Result pattern для безопасного создания UserId.
        
        Args:
            value: UUID, строка UUID или int (legacy support)
            
        Returns:
            Result[UserId, ValidationError]: Ok(UserId) или Err(ValidationError)
        """
        try:
            if isinstance(value, UUID):
                return Result.success(UserId(value=value))
            elif isinstance(value, str):
                return Result.success(UserId(value=UUID(value)))
            elif isinstance(value, int):
                # Legacy support: конвертируем int в UUID (для совместимости)
                # Используем namespace UUID для детерминированной генерации
                import hashlib
                hash_bytes = hashlib.md5(str(value).encode()).digest()
                return Result.success(UserId(value=UUID(bytes=hash_bytes)))
            else:
                return Result.failure(ValidationError(f"UserId must be UUID, str or int, got {type(value)}"))
        except (ValueError, AttributeError) as e:
            return Result.failure(ValidationError(f"Invalid UUID format: {value}"))

    @staticmethod
    def from_string(id_str: str) -> "UserId":
        """
        Создаёт UserId из string representation.

        Args:
            id_str: UUID в формате строки (e.g., "550e8400-e29b-41d4-a716-446655440000")

        Raises:
            ValidationError: Если строка не является валидным UUID.
        """
        try:
            return UserId(value=UUID(id_str))
        except (ValueError, AttributeError) as e:
            raise ValidationError(f"Invalid UUID format: {id_str}") from e

    def to_string(self) -> str:
        """Возвращает string representation UUID."""
        return str(self.value)

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return self.to_string()
