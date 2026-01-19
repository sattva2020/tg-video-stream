"""
UserMapper - маппинг между User Entity и User ORM Model (T053).

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Преобразование между доменными сущностями и ORM моделями
**Dependencies**: 
- Domain: User Entity, UserId, Email Value Objects
- ORM: models.User (SQLAlchemy model)

**Pattern**: Mapper Pattern (Entity ↔ ORM)
- to_entity(): ORM Model → Domain Entity
- to_orm(): Domain Entity → ORM Model
- update_orm(): Обновление существующего ORM объекта из Entity

**Usage**:
```python
# ORM → Entity
user_entity = UserMapper.to_entity(orm_user)

# Entity → новая ORM модель
orm_user = UserMapper.to_orm(user_entity)

# Entity → обновление существующей ORM модели
UserMapper.update_orm(orm_user, user_entity)
```
"""

import uuid
from typing import Optional
from datetime import datetime

from src.domain.entities.user import User as UserEntity
from src.domain.value_objects.user_id import UserId
from src.domain.value_objects.email import Email
from src.models.user import User as UserORM


class UserMapper:
    """Mapper для конвертации между User Entity и User ORM Model."""

    @staticmethod
    def to_entity(orm_user: UserORM) -> UserEntity:
        """
        Конвертирует ORM модель в доменную сущность.

        Args:
            orm_user: SQLAlchemy User model

        Returns:
            UserEntity: Доменная сущность пользователя

        Raises:
            ValueError: Если ORM модель невалидна (например, нет email)
        """
        # Валидация: email обязателен для Entity (но может быть None в ORM для Telegram-only users)
        if not orm_user.email:
            raise ValueError(f"User {orm_user.id} must have email for Entity mapping")

        # Создаём Value Objects
        user_id = UserId(value=orm_user.id)  # UUID → UserId (прямая передача UUID)
        email = Email(value=orm_user.email)  # Может бросить ValidationError

        # Создаём Entity
        # Примечание: hashed_password может быть None для OAuth-only пользователей
        # Для упрощения используем пустую строку, если None
        user_entity = UserEntity(
            id=user_id,
            email=email,
            username=orm_user.full_name or orm_user.email.split('@')[0],  # fallback к части email
            hashed_password=orm_user.hashed_password or "",
            is_active=(orm_user.status == "approved"),  # ORM status → Entity is_active
            created_at=orm_user.created_at or datetime.utcnow(),
        )

        return user_entity

    @staticmethod
    def to_orm(user_entity: UserEntity, existing_orm: Optional[UserORM] = None) -> UserORM:
        """
        Конвертирует доменную сущность в ORM модель.

        Args:
            user_entity: Domain User Entity
            existing_orm: Опциональная существующая ORM модель для обновления

        Returns:
            UserORM: SQLAlchemy User model (новая или обновлённая)

        Note:
            Если existing_orm передан, обновляет его поля вместо создания нового.
        """
        if existing_orm:
            # Обновляем существующую модель
            UserMapper.update_orm(existing_orm, user_entity)
            return existing_orm

        # Создаём новую ORM модель
        orm_user = UserORM(
            id=uuid.UUID(user_entity.id.value) if isinstance(user_entity.id.value, str) else user_entity.id.value,
            email=user_entity.email.value,
            full_name=user_entity.username,
            hashed_password=user_entity.hashed_password if user_entity.hashed_password else None,
            status="approved" if user_entity.is_active else "pending",
            email_verified=True,  # Предполагаем, что Entity всегда с верифицированным email
            created_at=user_entity.created_at,
            role="user",  # Default role, может быть расширено в Entity
        )

        return orm_user

    @staticmethod
    def update_orm(orm_user: UserORM, user_entity: UserEntity) -> None:
        """
        Обновляет существующую ORM модель из доменной сущности.

        Args:
            orm_user: Существующая SQLAlchemy User model
            user_entity: Domain User Entity с новыми данными

        Note:
            Не обновляет id, created_at (immutable поля).
            Обновляет только изменяемые поля: email, username, password, is_active.
        """
        orm_user.email = user_entity.email.value
        orm_user.full_name = user_entity.username
        
        # Обновляем пароль только если он не пустой
        if user_entity.hashed_password:
            orm_user.hashed_password = user_entity.hashed_password
        
        # is_active → status mapping
        orm_user.status = "approved" if user_entity.is_active else "pending"
        
        # updated_at обновится автоматически через onupdate=func.now()

    @staticmethod
    def to_entity_list(orm_users: list[UserORM]) -> list[UserEntity]:
        """
        Конвертирует список ORM моделей в список доменных сущностей.

        Args:
            orm_users: Список SQLAlchemy User models

        Returns:
            List[UserEntity]: Список доменных сущностей

        Note:
            Пропускает пользователей без email (Telegram-only users).
        """
        entities = []
        for orm_user in orm_users:
            try:
                entities.append(UserMapper.to_entity(orm_user))
            except (ValueError, Exception) as e:
                # Логируем и пропускаем невалидные записи
                # TODO: Добавить логирование через logger
                print(f"Skipping invalid user {orm_user.id}: {e}")
                continue
        
        return entities
