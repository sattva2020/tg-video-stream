"""
Базовые доменные исключения (FR-021: Domain Error Hierarchy).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: Наследуй от DomainError для specific бизнес-исключений.

Examples:
    >>> class InvalidEmailError(ValidationError):
    ...     def __init__(self, email: str):
    ...         super().__init__(f"Invalid email format: {email}")

    >>> raise InvalidEmailError("invalid@")
"""


class DomainError(Exception):
    """
    Базовый класс для всех доменных ошибок.

    **Design Decision** (research.md §TD7):
    - Domain: Только DomainError и подклассы
    - Application: Ловит DomainError, возвращает Result[T, DomainError]
    - Infrastructure: Трансформирует InfrastructureException → DomainError
    - Frameworks: Маппит DomainError → HTTP codes

    **Naming Convention**: {What}Error (InvalidEmailError, UserNotFoundError)
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ValidationError(DomainError):
    """
    Ошибки валидации Value Objects и Entity инвариантов (FR-011, US6).

    **When to use**:
    - Value Object creation failures (email format, positive integers)
    - Entity invariant violations (business rules)
    - Guard clause failures

    **NOT for**:
    - HTTP request validation (используй Pydantic в Frameworks layer)
    - Database constraint violations (Infrastructure concern)
    """

    pass


class EntityNotFoundError(DomainError):
    """
    Агрегат или Entity не найден по ID (FR-009: Repository contracts).

    **When to use**:
    - Repository.get_by_id() не находит сущность
    - Use Case требует существующую сущность

    **Example**:
        >>> class UserNotFoundError(EntityNotFoundError):
        ...     def __init__(self, user_id: str):
        ...         super().__init__(f"User with id {user_id} not found")
    """

    pass


class BusinessRuleViolationError(DomainError):
    """
    Нарушение бизнес-правила в Entity/Domain Service (US1: Domain Logic).

    **When to use**:
    - Stream.start() когда status != "ready"
    - Playlist.add_track() когда playlist full
    - Money arithmetic с разными валютами

    **NOT for**:
    - Value Object validation (используй ValidationError)
    - Authorization (используй SecurityError в Application)
    """

    pass


class ConcurrencyError(DomainError):
    """
    Конфликт версий при optimistic locking (FR-014, Edge Cases).

    **When to use**:
    - Repository.save() обнаруживает version mismatch
    - Domain event replay с outdated aggregate

    **Handling**:
    - Application layer: Retry logic с backoff
    - Frameworks layer: HTTP 409 Conflict
    """

    pass


class SecurityError(DomainError):
    """
    Нарушение security constraints на domain уровне.

    **When to use**:
    - Unauthorized action (User.delete_stream() чужого стрима)
    - Permission checks в Domain Services
    - Resource access control

    **NOT for**:
    - JWT validation (Frameworks layer)
    - API authentication (Frameworks/Infrastructure)
    """

    pass


class RepositoryError(DomainError):
    """
    Общая ошибка репозитория при работе с хранилищем.

    **When to use**:
    - Database connection errors
    - Query execution failures
    - Data access problems
    """

    pass


class UserNotFoundError(EntityNotFoundError):
    """Пользователь не найден по заданным критериям."""

    pass


class StreamNotFoundError(EntityNotFoundError):
    """Стрим не найден по заданным критериям."""

    pass


class DuplicateEmailError(DomainError):
    """Email уже зарегистрирован в системе."""

    pass


# Convenience constructors для common error cases
def validation_error(message: str) -> ValidationError:
    """Создаёт ValidationError с message."""
    return ValidationError(message)


def not_found_error(entity_type: str, entity_id: str) -> EntityNotFoundError:
    """Создаёт EntityNotFoundError с standard message format."""
    return EntityNotFoundError(f"{entity_type} with id '{entity_id}' not found")


def business_rule_error(rule: str, reason: str) -> BusinessRuleViolationError:
    """Создаёт BusinessRuleViolationError с structured message."""
    return BusinessRuleViolationError(f"Business rule '{rule}' violated: {reason}")
