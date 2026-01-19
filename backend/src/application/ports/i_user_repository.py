"""
IUserRepository Port Interface

Контракт для доступа к пользователям в хранилище.
Application layer определяет что нужно, Infrastructure реализует как.
"""

from typing import Protocol, Optional
from src.domain.entities.user import User
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.email import Email


class IUserRepository(Protocol):
    """
    Интерфейс репозитория пользователей.
    
    Использует Protocol (structural subtyping) для гибкости:
    - Не требует явного наследования
    - Позволяет легко создавать моки для тестов
    - Совместимо с любым классом, реализующим эти методы
    
    Examples:
        >>> user = User.create(...)
        >>> await repository.save(user)
        >>> found = await repository.get_by_id(user.id)
        >>> assert found == user
    """
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """
        Получить пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            User entity или None если не найден
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        ...
    
    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Получить пользователя по email.
        
        Args:
            email: Email адрес пользователя
            
        Returns:
            User entity или None если не найден
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        ...
    
    async def save(self, user: User) -> None:
        """
        Сохранить пользователя (create или update).
        
        Репозиторий сам определяет, создавать новую запись или обновлять существующую
        на основе user.id.
        
        Args:
            user: User entity для сохранения
            
        Raises:
            RepositoryError: При ошибке сохранения
            DuplicateEmailError: Если email уже существует (для create)
        """
        ...
    
    async def delete(self, user_id: UserId) -> None:
        """
        Удалить пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Raises:
            RepositoryError: При ошибке удаления
            UserNotFoundError: Если пользователь не найден
        """
        ...
    
    async def exists(self, user_id: UserId) -> bool:
        """
        Проверить существование пользователя.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            True если пользователь существует, False иначе
            
        Raises:
            RepositoryError: При ошибке проверки
        """
        ...
