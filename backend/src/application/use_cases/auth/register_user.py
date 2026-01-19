"""
RegisterUserUseCase - Use Case регистрации нового пользователя

Ответственность:
- Валидация email/username/password
- Проверка уникальности email
- Хеширование пароля
- Создание User entity
- Публикация UserCreatedEvent

Зависимости (через порты):
- IUserRepository: Проверка уникальности + сохранение
- IPasswordHasher: Хеширование пароля
- IEventBus: Публикация domain events
"""

from datetime import datetime
from typing import Protocol

from src.application.dtos.auth import (
    RegisterUserRequest,
    RegisterUserResponse,
)
from src.application.errors import RegistrationError
from src.application.ports.i_event_bus import IEventBus
from src.application.ports.i_password_hasher import IPasswordHasher
from src.application.ports.i_user_repository import IUserRepository
from src.domain.entities.user import User
from src.domain.value_objects.email import Email
from src.domain.value_objects.user_id import UserId
from src.shared.kernel.result import Result


class RegisterUserUseCase:
    """
    Use Case: Регистрация нового пользователя в системе.
    
    Orchestration:
    1. Валидировать email (через Email Value Object)
    2. Валидировать username (длина, формат)
    3. Валидировать пароль (сложность)
    4. Проверить уникальность email в репозитории
    5. Хешировать пароль через IPasswordHasher
    6. Создать User entity через factory method
    7. Сохранить в репозиторий
    8. Опубликовать UserCreatedEvent
    9. Вернуть RegisterUserResponse
    
    Пример использования:
        use_case = RegisterUserUseCase(user_repo, hasher, event_bus)
        request = RegisterUserRequest(
            email="newuser@example.com",
            username="newuser",
            password="SecurePassword123!"
        )
        result = use_case.execute(request)
        
        match result:
            case Ok(response):
                print(f"User {response.user_id} created: {response.email}")
            case Err(error):
                print(f"Registration failed: {error.message}")
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: IPasswordHasher,
        event_bus: IEventBus,
    ):
        """
        Инициализация Use Case с зависимостями (Dependency Injection).
        
        Args:
            user_repository: Репозиторий для работы с пользователями
            password_hasher: Сервис хеширования паролей
            event_bus: Шина событий для публикации domain events
        """
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._event_bus = event_bus
    
    async def execute(
        self,
        request: RegisterUserRequest
    ) -> Result[RegisterUserResponse, RegistrationError]:
        """
        Выполнить регистрацию нового пользователя.
        
        Args:
            request: DTO с email, username, password
        
        Returns:
            Result[RegisterUserResponse, RegistrationError]:
                Ok: Response с user_id, email, username, created_at
                Err: RegistrationError (email_already_exists, invalid_email, weak_password, username_too_short)
        """
        # 1. Валидировать email через Value Object
        try:
            email = Email(request.email)
        except Exception:
            return Result.failure(
                RegistrationError.invalid_email(request.email)
            )
        
        # 2. Валидировать username (минимум 3 символа)
        if len(request.username) < 3:
            return Result.failure(
                RegistrationError.username_too_short()
            )
        
        # 3. Валидировать пароль (минимальная сложность)
        if not self._is_password_strong(request.password):
            return Result.failure(
                RegistrationError.weak_password()
            )
        
        # 4. Проверить уникальность email
        existing_user = await self._user_repository.get_by_email(email)
        if existing_user is not None:
            return Result.failure(
                RegistrationError.email_already_exists(request.email)
            )
        
        # 5. Хешировать пароль
        hashed_password = await self._password_hasher.hash(request.password)
        
        # 6. Создать User entity
        # NOTE: UserId генерируется автоматически
        user = User.create(
            user_id=UserId.generate(),
            email=email,
            username=request.username,
            hashed_password=hashed_password,
        )
        
        # 7. Сохранить пользователя (репозиторий назначит ID)
        await self._user_repository.save(user)
        
        # 8. Публикация domain event
        # TODO: Реализовать UserCreatedEvent в domain/events/
        # self._event_bus.publish(
        #     UserCreatedEvent(
        #         user_id=user.id,
        #         email=user.email,
        #         username=user.username,
        #         created_at=datetime.utcnow()
        #     )
        # )
        
        # 9. Сформировать Response DTO
        response = RegisterUserResponse(
            user_id=user.id.value,
            email=user.email.value,
            username=user.username,
            created_at=datetime.utcnow(),
        )
        
        return Result.success(response)
    
    def _is_password_strong(self, password: str) -> bool:
        """
        Проверка сложности пароля (упрощенная версия).
        
        Требования:
        - Минимум 8 символов
        - Хотя бы 1 цифра
        - Хотя бы 1 буква
        
        В production используйте:
        - Библиотеки типа zxcvbn-python
        - Проверку на утечки (Have I Been Pwned API)
        - Настраиваемые правила через конфиг
        """
        if len(password) < 8:
            return False
        
        has_digit = any(char.isdigit() for char in password)
        has_letter = any(char.isalpha() for char in password)
        
        return has_digit and has_letter
