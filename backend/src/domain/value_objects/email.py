"""
Email Value Object с валидацией формата (T015).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python, regex)
**Usage**: User Entity, authentication use cases.
"""

import re
from dataclasses import dataclass

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Email(ValueObject):
    """
    Email address с валидацией формата.

    **Validation Rules**:
    - Содержит @ символ
    - Домен содержит точку
    - Минимум 3 символа
    - Не содержит пробелов

    **Design Decision**: Простая regex валидация, не RFC 5322 compliant
    (бизнес-требование: basic email check, не 100% spec compliance).

    Examples:
        >>> email = Email("user@example.com")
        >>> email.value
        'user@example.com'

        >>> Email("invalid")
        ValidationError: Invalid email format: invalid
    """

    value: str

    # Простой regex для email (не полный RFC 5322)
    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __post_init__(self):
        """Валидация email формата при создании."""
        if not self._is_valid(self.value):
            raise ValidationError(f"Invalid email format: {self.value}")

    @classmethod
    def _is_valid(cls, email: str) -> bool:
        """
        Проверяет валидность email формата.

        **Rules**:
        - Длина >= 3 символа
        - Содержит @ и точку в домене
        - Нет пробелов
        """
        if not email or len(email) < 3:
            return False
        if not cls.EMAIL_PATTERN.match(email):
            return False
        return True

    def domain(self) -> str:
        """Извлекает домен из email (часть после @)."""
        return self.value.split("@")[1]

    def local_part(self) -> str:
        """Извлекает local part из email (часть до @)."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return self.value
