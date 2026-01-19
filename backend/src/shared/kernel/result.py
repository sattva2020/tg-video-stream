"""
Result[T, E] Pattern для функционального обработки ошибок.

Реализует Railway Oriented Programming pattern для явного handling ошибок
без использования exceptions в бизнес-логике (FR-021, FR-019).

Examples:
    >>> result = Result.success(42)
    >>> result.is_success
    True
    >>> result.value
    42

    >>> error = Result.failure("Something went wrong")
    >>> error.is_failure
    True
    >>> error.error
    'Something went wrong'
"""

from typing import Callable, Generic, TypeVar, Union

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Transformed success type


class Result(Generic[T, E]):
    """
    Представляет результат операции: либо Success(value), либо Failure(error).

    **Design Decision** (from research.md §TD7):
    - Domain/Application: Result[T, DomainError] для бизнес-логики
    - Infrastructure: Exceptions → Result для внешних операций
    - Frameworks: Result → HTTP codes (200/4xx/5xx)
    """

    def __init__(self, value: Union[T, None] = None, error: Union[E, None] = None):
        if value is not None and error is not None:
            raise ValueError("Result cannot have both value and error")
        if value is None and error is None:
            raise ValueError("Result must have either value or error")

        self._value = value
        self._error = error

    @property
    def is_success(self) -> bool:
        """True если результат содержит значение (success case)."""
        return self._value is not None

    @property
    def is_failure(self) -> bool:
        """True если результат содержит ошибку (failure case)."""
        return self._error is not None

    # Алиасы для совместимости с разными стилями API
    @property
    def is_ok(self) -> bool:
        """Alias for is_success (Rust-style API)."""
        return self.is_success

    @property
    def is_err(self) -> bool:
        """Alias for is_failure (Rust-style API)."""
        return self.is_failure

    @property
    def value(self) -> T:
        """
        Извлекает значение. Raises ValueError если результат - failure.

        **Use in Domain**: Только после проверки is_success или в тестах.
        """
        if self._value is None:
            raise ValueError("Cannot get value from a failure result")
        return self._value

    @property
    def error(self) -> E:
        """
        Извлекает ошибку. Raises ValueError если результат - success.

        **Use in Frameworks**: Для mapping в HTTP response codes.
        """
        if self._error is None:
            raise ValueError("Cannot get error from a success result")
        return self._error

    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        """
        Применяет функцию к success value, оставляет error без изменений.

        Railway Oriented Programming: операции можно chain'ить без if-checks.

        Example:
            >>> Result.success(5).map(lambda x: x * 2)
            Result(value=10)
        """
        if self.is_success:
            return Result.success(func(self.value))
        return Result.failure(self.error)

    def flat_map(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """
        Применяет функцию, возвращающую Result (для chaining операций).

        **Use in Use Cases**: Последовательные операции с проверками.

        Example:
            >>> def validate_positive(x: int) -> Result[int, str]:
            ...     return Result.success(x) if x > 0 else Result.failure("Not positive")
            >>> Result.success(5).flat_map(validate_positive)
            Result(value=5)
        """
        if self.is_success:
            return func(self.value)
        return Result.failure(self.error)

    def map_error(self, func: Callable[[E], E]) -> "Result[T, E]":
        """
        Применяет функцию к error, оставляет value без изменений.

        **Use in Infrastructure**: Трансформация internal errors в domain errors.
        """
        if self.is_failure:
            return Result.failure(func(self.error))
        return Result.success(self.value)

    def unwrap_or(self, default: T) -> T:
        """
        Извлекает значение или возвращает default при failure.

        **Use carefully**: Используй только когда можешь безопасно игнорировать ошибку.
        """
        return self.value if self.is_success else default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """
        Извлекает значение или вычисляет fallback из ошибки.

        **Use in Use Cases**: Fallback strategies для бизнес-логики.
        """
        return self.value if self.is_success else func(self.error)

    @staticmethod
    def success(value: T) -> "Result[T, E]":
        """Создаёт успешный Result с value."""
        return Result(value=value)

    @staticmethod
    def failure(error: E) -> "Result[T, E]":
        """Создаёт неуспешный Result с error."""
        return Result(error=error)

    def __repr__(self) -> str:
        if self.is_success:
            return f"Result(value={self._value!r})"
        return f"Result(error={self._error!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return False
        if self.is_success != other.is_success:
            return False
        if self.is_success:
            return self.value == other.value
        return self.error == other.error


# Convenience type aliases для common use cases
Success = Result.success  # type: ignore[misc]
Failure = Result.failure  # type: ignore[misc]
