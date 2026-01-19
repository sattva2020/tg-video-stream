"""
Базовый класс ValueObject для Domain Layer (FR-011, US6).

**Architecture Layer**: Shared Kernel
**Dependencies**: None (pure Python)
**Usage**: Все Value Objects наследуют от ValueObject.

Examples:
    >>> @dataclass(frozen=True)
    ... class Email(ValueObject):
    ...     value: str
    ...
    ...     def __post_init__(self):
    ...         if "@" not in self.value:
    ...             raise ValidationError(f"Invalid email: {self.value}")
"""

from abc import ABC
from typing import Any


class ValueObject(ABC):
    """
    Базовый класс для всех Value Objects.

    **Immutability**: Value Objects неизменяемы после создания.
    **Equality**: Сравниваются по значениям всех атрибутов (value equality).
    **Validation**: Конструктор гарантирует валидность (fail-fast).
    **Self-Validation**: Value Objects валидируют сами себя, не полагаясь на внешние сервисы.

    **Design Principles** (FR-011):
    1. **Immutability**: Используй @dataclass(frozen=True) или свойства только для чтения
    2. **Value Equality**: Два Value Objects равны, если все атрибуты равны
    3. **Side-Effect Free**: Методы не меняют состояние, возвращают новые объекты
    4. **Self-Contained**: Вся валидация в конструкторе, без внешних зависимостей

    **Naming Convention**: Существительные, описывающие концепт (Email, Duration, Money)

    **Implementation Pattern**:
        ```python
        from dataclasses import dataclass
        from src.shared.kernel.value_object import ValueObject
        from src.domain.errors import ValidationError

        @dataclass(frozen=True)
        class Email(ValueObject):
            value: str

            def __post_init__(self):
                if not self._is_valid(self.value):
                    raise ValidationError(f"Invalid email: {self.value}")

            @staticmethod
            def _is_valid(email: str) -> bool:
                return "@" in email and "." in email.split("@")[1]
        ```
    """

    def __eq__(self, other: Any) -> bool:
        """
        Value Objects равны, если все атрибуты равны (value equality).

        **Value vs Identity Equality**:
        - Value Object: сравниваем все атрибуты
        - Entity: сравниваем только ID

        Example:
            >>> email1 = Email("user@example.com")
            >>> email2 = Email("user@example.com")
            >>> email1 == email2  # True (same value)
            >>> email1 is email2  # False (different objects)
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """
        Hash based on all attributes (для использования в sets/dicts).

        **Immutability Required**: Все атрибуты должны быть immutable.
        **Implementation Note**: Работает с @dataclass(frozen=True) автоматически.
        """
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        """
        Debug representation с class name и всеми атрибутами.

        Example:
            >>> Email("user@example.com")
            Email(value='user@example.com')
        """
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


# Type hint для документации
# Используй для аннотации параметров: def create_user(email: EmailVO) -> User
# где EmailVO = Email (Value Object тип)
