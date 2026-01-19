"""
Authentication DTOs

Request/Response DTOs для Use Cases аутентификации.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticateUserRequest:
    """
    Запрос на аутентификацию пользователя.
    
    Attributes:
        email: Email адрес пользователя
        password: Пароль в открытом виде
    """
    email: str
    password: str


@dataclass(frozen=True)
class AuthenticateUserResponse:
    """
    Результат успешной аутентификации.
    
    Attributes:
        user_id: ID пользователя
        email: Email пользователя
        username: Имя пользователя
        access_token: JWT access token
        refresh_token: JWT refresh token (optional)
        expires_at: Время истечения access token
    """
    user_id: int
    email: str
    username: str
    access_token: str
    refresh_token: str | None
    expires_at: datetime


@dataclass(frozen=True)
class RegisterUserRequest:
    """
    Запрос на регистрацию нового пользователя.
    
    Attributes:
        email: Email адрес
        username: Имя пользователя
        password: Пароль в открытом виде
    """
    email: str
    username: str
    password: str


@dataclass(frozen=True)
class RegisterUserResponse:
    """
    Результат успешной регистрации.
    
    Attributes:
        user_id: ID созданного пользователя
        email: Email пользователя
        username: Имя пользователя
        created_at: Время создания аккаунта
    """
    user_id: int
    email: str
    username: str
    created_at: datetime
