"""
ChatId Value Object для Telegram chat identifiers (T017).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Stream Entity, broadcast use cases.
"""

from dataclasses import dataclass
from typing import Union

from src.domain.errors import ValidationError
from src.shared.kernel.result import Result
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class ChatId(ValueObject):
    """
    Telegram chat ID (integer или string для usernames).

    **Telegram Chat ID Types**:
    - Private chat: positive integer (user ID)
    - Group/Channel: negative integer
    - Username: string starting with @ (e.g., "@channel_name")

    **Validation**:
    - Не пустое значение
    - Integer или string с @
    - Integer не равен 0

    Examples:
        >>> chat_id = ChatId(123456789)  # User ID
        >>> chat_id.value
        123456789

        >>> group_id = ChatId(-1001234567890)  # Channel ID
        >>> username = ChatId("@my_channel")
    """

    value: int | str

    def __post_init__(self):
        """Валидация chat ID при создании."""
        if not self._is_valid(self.value):
            raise ValidationError(f"Invalid ChatId: {self.value}")

    @staticmethod
    def _is_valid(chat_id: int | str) -> bool:
        """
        Проверяет валидность chat ID.

        **Rules**:
        - Integer: не 0, может быть отрицательным (группы/каналы)
        - String: начинается с @ и длина >= 2
        """
        if isinstance(chat_id, int):
            return chat_id != 0
        if isinstance(chat_id, str):
            return len(chat_id) >= 2 and chat_id.startswith("@")
        return False

    @staticmethod
    def create(value: Union[int, str]) -> Result["ChatId", ValidationError]:
        """
        Factory method с Result pattern для безопасного создания ChatId.
        
        Args:
            value: int (chat ID) или str (username с @)
            
        Returns:
            Result[ChatId, ValidationError]: Ok(ChatId) или Err(ValidationError)
        """
        if not ChatId._is_valid(value):
            return Result.failure(ValidationError(f"Invalid ChatId: {value}"))
        return Result.success(ChatId(value=value))

    def is_user(self) -> bool:
        """True если chat ID - это пользователь (positive integer)."""
        return isinstance(self.value, int) and self.value > 0

    def is_group_or_channel(self) -> bool:
        """True если chat ID - это группа/канал (negative integer)."""
        return isinstance(self.value, int) and self.value < 0

    def is_username(self) -> bool:
        """True если chat ID - это username (string с @)."""
        return isinstance(self.value, str)

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return str(self.value)
