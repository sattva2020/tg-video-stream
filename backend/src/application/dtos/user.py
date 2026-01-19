"""
User DTOs (Data Transfer Objects)

Request/Response DTOs для Use Cases управления пользователями.

**Phase 7**: Clean Architecture - DTO для границ слоёв
**Reference**: specs/025-clean-architecture-rules/tasks.md T068
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

from .common import PaginationRequest, PaginatedResponse, PaginationMeta


class UserRole(str, Enum):
    """Роли пользователей."""
    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """Статусы пользователей."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


# =============================================================================
# User DTOs (Read Operations)
# =============================================================================

@dataclass(frozen=True)
class UserDTO:
    """
    Полное представление пользователя для API ответов.
    
    Используется для GET /users/{id} и подобных endpoint'ов.
    Не содержит sensitive данные (пароли, токены).
    
    Attributes:
        id: Уникальный идентификатор
        email: Email адрес
        username: Имя пользователя
        role: Роль пользователя
        status: Статус аккаунта
        is_email_verified: Подтверждён ли email
        telegram_id: Telegram ID (optional)
        created_at: Время создания
        last_login_at: Время последнего входа (optional)
    """
    id: int
    email: str
    username: str
    role: UserRole
    status: UserStatus
    is_email_verified: bool
    telegram_id: Optional[int] = None
    created_at: datetime = None
    last_login_at: Optional[datetime] = None


@dataclass(frozen=True)
class UserSummaryDTO:
    """
    Краткое представление пользователя для списков.
    
    Используется в списках, выпадающих меню, связях.
    Минимум данных для отображения.
    
    Attributes:
        id: Уникальный идентификатор
        username: Имя пользователя
        role: Роль пользователя
    """
    id: int
    username: str
    role: UserRole


# =============================================================================
# User Request DTOs
# =============================================================================

@dataclass(frozen=True)
class GetUserRequest:
    """
    Запрос на получение пользователя по ID.
    
    Attributes:
        user_id: ID пользователя
    """
    user_id: int


@dataclass(frozen=True)
class ListUsersRequest:
    """
    Запрос на получение списка пользователей.
    
    Attributes:
        pagination: Параметры пагинации
        role: Фильтр по роли (optional)
        status: Фильтр по статусу (optional)
        search: Поиск по username/email (optional)
    """
    pagination: PaginationRequest
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    search: Optional[str] = None


@dataclass(frozen=True)
class CreateUserRequest:
    """
    Запрос на создание нового пользователя (админ).
    
    Attributes:
        email: Email адрес
        username: Имя пользователя
        password: Пароль в открытом виде
        role: Роль пользователя (default: USER)
    """
    email: str
    username: str
    password: str
    role: UserRole = UserRole.USER


@dataclass(frozen=True)
class UpdateUserRequest:
    """
    Запрос на обновление данных пользователя.
    
    Все поля optional - обновляются только переданные.
    
    Attributes:
        user_id: ID пользователя для обновления
        username: Новое имя пользователя (optional)
        email: Новый email (optional)
        role: Новая роль (optional)
        status: Новый статус (optional)
    """
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


@dataclass(frozen=True)
class ChangePasswordRequest:
    """
    Запрос на смену пароля.
    
    Attributes:
        user_id: ID пользователя
        current_password: Текущий пароль
        new_password: Новый пароль
    """
    user_id: int
    current_password: str
    new_password: str


@dataclass(frozen=True)
class DeleteUserRequest:
    """
    Запрос на удаление пользователя.
    
    Attributes:
        user_id: ID пользователя для удаления
    """
    user_id: int


# =============================================================================
# User Response DTOs
# =============================================================================

@dataclass(frozen=True)
class CreateUserResponse:
    """
    Результат создания пользователя.
    
    Attributes:
        user: Созданный пользователь
    """
    user: UserDTO


@dataclass(frozen=True)
class UpdateUserResponse:
    """
    Результат обновления пользователя.
    
    Attributes:
        user: Обновлённый пользователь
    """
    user: UserDTO


@dataclass(frozen=True)
class ListUsersResponse:
    """
    Результат запроса списка пользователей.
    
    Attributes:
        users: Список пользователей
        meta: Метаданные пагинации
    """
    users: List[UserDTO]
    meta: PaginationMeta


@dataclass(frozen=True)
class ChangePasswordResponse:
    """
    Результат смены пароля.
    
    Attributes:
        success: Успешно ли изменён пароль
        message: Сообщение (optional)
    """
    success: bool
    message: Optional[str] = None
