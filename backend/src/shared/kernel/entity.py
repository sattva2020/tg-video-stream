"""
Базовый класс Entity для Domain Layer (FR-006, US1).

**Architecture Layer**: Shared Kernel
**Dependencies**: None (pure Python)
**Usage**: Все domain entities наследуют от Entity.

Examples:
    >>> class User(Entity[UserId]):
    ...     def __init__(self, id: UserId, email: Email):
    ...         super().__init__(id)
    ...         self.email = email
"""

from abc import ABC
from typing import Generic, TypeVar

# ID может быть любым типом (UserId, StreamId, etc.)
ID = TypeVar("ID")


class Entity(ABC, Generic[ID]):
    """
    Базовый класс для всех Domain Entities.

    **Identity**: Entities сравниваются по ID, не по атрибутам.
    **Invariants**: Конструктор и методы должны гарантировать валидность.
    **Immutable ID**: ID устанавливается при создании и не меняется.

    **Design Principles** (FR-006):
    1. **Identity**: Entity определяется уникальным ID
    2. **Encapsulation**: Бизнес-логика инкапсулирована в методах
    3. **Invariants**: Конструктор гарантирует валидное состояние
    4. **No Framework Dependencies**: Только Python stdlib и domain code

    **Naming Convention**: Существительные в ед. числе (User, Stream, Playlist)
    """

    def __init__(self, id: ID):
        """
        Инициализирует Entity с уникальным ID.

        Args:
            id: Уникальный идентификатор (Value Object типа UserId, StreamId, etc.)

        **Validation**: ID должен быть non-null (проверка в конструкторе подклассов).
        """
        if id is None:
            raise ValueError(f"{self.__class__.__name__} requires non-null ID")
        self._id = id

    @property
    def id(self) -> ID:
        """
        Возвращает уникальный идентификатор Entity (immutable).

        **Immutability**: ID нельзя изменить после создания.
        """
        return self._id

    def __eq__(self, other: object) -> bool:
        """
        Entities равны, если имеют одинаковый ID (identity equality).

        **Identity vs Value Equality**:
        - Entity: сравниваем по ID
        - Value Object: сравниваем по всем атрибутам

        Example:
            >>> user1 = User(UserId("123"), Email("user@example.com"))
            >>> user2 = User(UserId("123"), Email("other@example.com"))
            >>> user1 == user2  # True (same ID)
        """
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """
        Hash based on ID (для использования в sets/dicts).

        **Immutability Required**: ID не должен меняться после создания.
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Debug representation с class name и ID."""
        return f"{self.__class__.__name__}(id={self.id!r})"
