"""
User Entity - доменная сущность пользователя (T020).

**Architecture Layer**: Domain
**Dependencies**: UserId, Email, Password, Title Value Objects, DomainEvent
**Usage**: Authentication, user management use cases.
"""

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.events import UserCreatedEvent, UserActivatedEvent, UserDeactivatedEvent
from src.domain.value_objects.email import Email
from src.domain.value_objects.password import Password
from src.domain.value_objects.title import Title
from src.domain.value_objects.user_id import UserId

@dataclass
class User:
    """
    Пользователь системы (администратор, оператор стрима).

    **Invariants**:
    - Email уникален (проверяется через IUserRepository)
    - Username (Title) валиден и не пустой
    - Password (hashed) валиден

    **Lifecycle**:
    1. Создание через create() factory
    2. Активация/деактивация через activate()/deactivate()
    3. Обновление профиля через change_email()/update_profile()

    **Domain Events**:
    - UserCreatedEvent: при создании
    - UserActivatedEvent: при активации
    - UserDeactivatedEvent: при деактивации
    """

    id: UserId  # Entity identity
    email: Email
    username: Title  # Value Object для имени пользователя
    hashed_password: Password  # Value Object для хешированного пароля
    is_active: bool
    created_at: datetime
    _domain_events: list = field(default_factory=list, repr=False, compare=False)

    def __eq__(self, other: object) -> bool:
        """Entities равны если имеют одинаковый ID."""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    @staticmethod
    def create(
        user_id: UserId,
        email: Email,
        username: Title,
        hashed_password: Password,
    ) -> "User":
        """
        Factory method для создания нового пользователя.

        Args:
            user_id: Уникальный ID пользователя
            email: Email для аутентификации
            username: Title VO для отображаемого имени
            hashed_password: Password VO (хеш bcrypt/argon2)

        Returns:
            User entity с is_active=True и текущим timestamp.

        Note:
            Валидация username и hashed_password выполняется
            в соответствующих Value Objects при создании.
        """
        user = User(
            id=user_id,
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        # Domain Event: UserCreated
        user._domain_events.append(
            UserCreatedEvent(
                user_id=user_id,
                email=email.value,
                username=str(username),  # Convert Title to str for event
            )
        )

        return user

    def activate(self) -> None:
        """
        Активирует пользователя (is_active=True).

        **Business Rule**: Нельзя активировать уже активного пользователя.

        Raises:
            BusinessRuleViolationError: Если пользователь уже активен.
        """
        if self.is_active:
            from src.domain.errors import BusinessRuleViolationError
            raise BusinessRuleViolationError(f"User {self.id} is already active")

        self.is_active = True
        self._domain_events.append(UserActivatedEvent(user_id=self.id))

    def deactivate(self) -> None:
        """
        Деактивирует пользователя (is_active=False).

        **Business Rule**: Нельзя деактивировать уже неактивного пользователя.

        Raises:
            BusinessRuleViolationError: Если пользователь уже неактивен.
        """
        if not self.is_active:
            from src.domain.errors import BusinessRuleViolationError
            raise BusinessRuleViolationError(f"User {self.id} is already inactive")

        self.is_active = False
        self._domain_events.append(UserDeactivatedEvent(user_id=self.id))

    def change_email(self, new_email: Email) -> None:
        """
        Изменяет email пользователя.

        **Business Rule**: Новый email должен отличаться от текущего.

        Args:
            new_email: Новый валидный Email Value Object

        Raises:
            BusinessRuleViolationError: Если новый email совпадает с текущим.
        """
        if self.email == new_email:
            from src.domain.errors import BusinessRuleViolationError
            raise BusinessRuleViolationError(
                f"New email {new_email} is the same as current email"
            )

        self.email = new_email

    def update_profile(self, username: Title) -> None:
        """
        Обновляет профиль пользователя (username).

        Args:
            username: Новое имя пользователя (Title Value Object)

        Note:
            Валидация выполняется в Title VO при создании.
        """
        self.username = username

    def collect_domain_events(self) -> list:
        """
        Собирает и очищает domain events для публикации.

        Returns:
            Список domain events, генерированных entity.
        """
        events = self._domain_events[:]
        self._domain_events.clear()
        return events
