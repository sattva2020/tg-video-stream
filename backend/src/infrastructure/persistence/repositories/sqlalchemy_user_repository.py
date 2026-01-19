"""
SQLAlchemy реализация репозитория пользователей.

Этот модуль реализует IUserRepository port используя SQLAlchemy ORM.
Преобразования между Entity и ORM моделями выполняются через UserMapper.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.application.ports.i_user_repository import IUserRepository
from src.domain.entities.user import User
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.mappers.user_mapper import UserMapper
from src.models.user import User as UserORM
from src.domain.errors import RepositoryError, DuplicateEmailError, UserNotFoundError


class SqlAlchemyUserRepository:
    """
    SQLAlchemy реализация IUserRepository.
    
    Использует UserMapper для преобразования между Domain entities и ORM models.
    Репозиторий НЕ выполняет commit - это ответственность use case.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            session: Async SQLAlchemy сессия
        """
        self._session = session
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """
        Найти пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Returns:
            User entity или None если не найден
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = select(UserORM).where(UserORM.id == user_id.value)
            result = await self._session.execute(stmt)
            orm_user = result.scalar_one_or_none()
            
            if not orm_user:
                return None
            
            return UserMapper.to_entity(orm_user)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get user by id {user_id}: {e}") from e
    
    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Найти пользователя по email.
        
        Args:
            email: Email адрес пользователя
            
        Returns:
            User entity або None если не найден
            
        Raises:
            RepositoryError: При ошибке доступа к хранилищу
        """
        try:
            stmt = select(UserORM).where(UserORM.email == email.value)
            result = await self._session.execute(stmt)
            orm_user = result.scalar_one_or_none()
            
            if not orm_user:
                return None
            
            return UserMapper.to_entity(orm_user)
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get user by email {email}: {e}") from e
    
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
        try:
            # Проверяем, существует ли пользователь
            stmt = select(UserORM).where(UserORM.id == user.id.value)
            result = await self._session.execute(stmt)
            existing_orm = result.scalar_one_or_none()
            
            if existing_orm:
                # Update: обновляем существующий ORM объект
                UserMapper.update_orm(existing_orm, user)
            else:
                # Create: создаем новый ORM объект
                orm_user = UserMapper.to_orm(user)
                self._session.add(orm_user)
            
            # flush() для раннего обнаружения constraint violations
            # commit() НЕ вызываем - это ответственность use case
            await self._session.flush()
            
        except IntegrityError as e:
            # Email unique constraint violation
            if "email" in str(e.orig).lower():
                raise DuplicateEmailError(f"User with email {user.email} already exists") from e
            raise RepositoryError(f"Integrity error saving user: {e}") from e
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save user {user.id}: {e}") from e
    
    async def delete(self, user_id: UserId) -> None:
        """
        Удалить пользователя по ID.
        
        Args:
            user_id: Уникальный идентификатор пользователя
            
        Raises:
            RepositoryError: При ошибке удаления
            UserNotFoundError: Если пользователь не найден
        """
        try:
            stmt = select(UserORM).where(UserORM.id == user_id.value)
            result = await self._session.execute(stmt)
            orm_user = result.scalar_one_or_none()
            
            if not orm_user:
                raise UserNotFoundError(f"User {user_id} not found")
            
            await self._session.delete(orm_user)
            await self._session.flush()
            
        except UserNotFoundError:
            raise  # Re-raise domain errors as-is
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete user {user_id}: {e}") from e
    
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
        try:
            stmt = select(UserORM.id).where(UserORM.id == user_id.value)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to check user existence {user_id}: {e}") from e
