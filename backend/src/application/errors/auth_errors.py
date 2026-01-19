"""
Authentication & Registration Errors

Ошибки Use Cases для аутентификации и регистрации пользователей.
"""

from src.domain.errors import DomainError


class AuthenticationError(DomainError):
    """Ошибка аутентификации пользователя."""
    
    def __init__(self, message: str, code: str = "authentication_error"):
        super().__init__(message)
        self.code = code
    
    @staticmethod
    def invalid_credentials() -> "AuthenticationError":
        """Неверный email или пароль."""
        return AuthenticationError("Invalid email or password", code="invalid_credentials")
    
    @staticmethod
    def user_not_found(email: str) -> "AuthenticationError":
        """Пользователь не найден."""
        return AuthenticationError(f"User with email {email} not found", code="user_not_found")
    
    @staticmethod
    def account_deactivated() -> "AuthenticationError":
        """Аккаунт деактивирован."""
        return AuthenticationError("User account is deactivated", code="account_deactivated")


class RegistrationError(DomainError):
    """Ошибка регистрации пользователя."""
    
    def __init__(self, message: str, code: str = "registration_error"):
        super().__init__(message)
        self.code = code
    
    @staticmethod
    def email_already_exists(email: str) -> "RegistrationError":
        """Email уже зарегистрирован."""
        return RegistrationError(f"User with email {email} already exists", code="email_already_exists")
    
    @staticmethod
    def invalid_email(email: str) -> "RegistrationError":
        """Невалидный email."""
        return RegistrationError(f"Email {email} is invalid", code="invalid_email")
    
    @staticmethod
    def weak_password() -> "RegistrationError":
        """Слабый пароль."""
        return RegistrationError("Password does not meet security requirements", code="weak_password")
    
    @staticmethod
    def username_too_short() -> "RegistrationError":
        """Имя пользователя слишком короткое."""
        return RegistrationError("Username must be at least 3 characters long", code="username_too_short")
