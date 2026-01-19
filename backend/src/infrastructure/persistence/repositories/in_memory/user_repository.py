"""
In-memory реализация репозитория пользователей для тестирования.

Этот модуль реализует IUserRepository используя простой dict.
Используется в unit тестах для изоляции от базы данных.
"""

from typing import Optional, Dict
from uuid import UUID

from src.application.ports.i_user_repository import IUserRepository
from src.domain.entities.user import User
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.email import Email
from src.domain.errors import DuplicateEmailError, UserNotFoundError


class InMemoryUserRepository:
    """
    In-memory реализация IUserRepository для тестирования.
    
    Хранит User entities напрямую в dict без ORM.
    Не требует UserMapper т.к. работает с entities напрямую.
    """
    
    def __init__(self):
        """Инициализация репозитория с пустым хранилищем."""
        self._users: Dict[UUID, User] = {}  # {user_id.value: User entity}
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """
        Найти пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            User entity или None если не найден
        """
        return self._users.get(user_id.value)
    
    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Найти пользователя по email.
        
        Args:
            email: Email адрес пользователя
            
        Returns:
            User entity или None если не найден
        """
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    async def save(self, user: User) -> None:
        """
        Сохранить пользователя (create или update).
        
        Args:
            user: User entity для сохранения
            
        Raises:
            DuplicateEmailError: Если email уже существует (для create)
        """
        # Проверка на дублирование email (только для create)
        existing_id = user.id.value
        if existing_id not in self._users:
            # Create: проверяем уникальность email
            existing_with_email = await self.get_by_email(user.email)
            if existing_with_email and existing_with_email.id != user.id:
                raise DuplicateEmailError(f"User with email {user.email} already exists")
        
        # Сохраняем копию entity (immutability)
        self._users[user.id.value] = user
    
    async def delete(self, user_id: UserId) -> None:
        """
        Удалить пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Raises:
            UserNotFoundError: Если пользователь не найден
        """
        if user_id.value not in self._users:
            raise UserNotFoundError(f"User {user_id} not found")
        
        del self._users[user_id.value]
    
    async def exists(self, user_id: UserId) -> bool:
        """
        Проверить существование пользователя.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            True если пользователь существует, False иначе
        """
        return user_id.value in self._users
    
    def clear(self) -> None:
        """Очистить хранилище (для тестов)."""
        self._users.clear()
