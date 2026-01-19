"""
Password Value Object (hashed password storage).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: User Entity, authentication use cases.

**Phase 8**: Clean Architecture - Value Objects
**Reference**: specs/025-clean-architecture-rules/tasks.md T074
"""

from dataclasses import dataclass

from src.domain.errors import ValidationError
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class Password(ValueObject):
    """
    Hashed password с валидацией формата.

    **Security Note**: Это Value Object для ХЕШИРОВАННЫХ паролей.
    Обычные пароли никогда не хранятся в Domain.
    Хеширование происходит в Infrastructure layer (BcryptPasswordHasher).

    **Validation Rules**:
    - Не пустой
    - Минимум 20 символов (bcrypt hash минимум)
    - Начинается с '$' (bcrypt формат: $2a$, $2b$, etc.)

    **Design Decision**: 
    - Domain не знает о bcrypt (implementation detail)
    - Валидация проверяет только формат, не криптографию

    Examples:
        >>> # Bcrypt hash example
        >>> hashed = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4Z."
        >>> password = Password(hashed)
        
        >>> # Plain password fails validation
        >>> Password("mypassword123")
        ValidationError: Password must be a hashed value
    """

    value: str

    # Минимальная длина bcrypt hash
    MIN_HASH_LENGTH = 20
    
    # Bcrypt prefixes
    VALID_PREFIXES = ('$2a$', '$2b$', '$2y$', '$argon2')

    def __post_init__(self):
        """Валидация hashed password при создании."""
        if not self._is_valid_hash(self.value):
            raise ValidationError(
                "Password must be a hashed value (bcrypt/argon2 format)"
            )

    @classmethod
    def _is_valid_hash(cls, password_hash: str) -> bool:
        """
        Проверяет, что значение является хешем пароля.

        **Rules**:
        - Не пустой
        - Минимальная длина для hash
        - Начинается с известного prefix
        """
        if not password_hash:
            return False
        
        if len(password_hash) < cls.MIN_HASH_LENGTH:
            return False
        
        # Проверяем prefix bcrypt или argon2
        return any(password_hash.startswith(prefix) for prefix in cls.VALID_PREFIXES)

    @classmethod
    def from_hash(cls, hashed_value: str) -> "Password":
        """
        Factory method для создания из готового хеша.
        
        Args:
            hashed_value: Bcrypt/Argon2 hash string
            
        Returns:
            Password value object
            
        Raises:
            ValidationError: Если формат хеша невалиден
        """
        return cls(value=hashed_value)

    def __str__(self) -> str:
        """Возвращает маскированное значение для безопасности."""
        return "***HASHED***"
    
    def __repr__(self) -> str:
        """Repr без реального хеша."""
        return "Password(***)"

    def matches(self, other: "Password") -> bool:
        """
        Сравнивает два хеша (для внутренних проверок).
        
        **Note**: Это НЕ для проверки пароля пользователя!
        Для аутентификации используйте IPasswordHasher.verify()
        """
        return self.value == other.value
