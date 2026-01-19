"""
AuthenticateUserUseCase - Use Case аутентификации пользователя

Ответственность:
- Валидация email/password
- Верификация пароля
- Генерация JWT токенов
- Публикация UserAuthenticatedEvent

Зависимости (через порты):
- IUserRepository: Загрузка пользователя по email
- IPasswordHasher: Верификация пароля
- IEventBus: Публикация domain events
"""

from datetime import datetime, timedelta
from typing import Protocol

from src.application.dtos.auth import (
    AuthenticateUserRequest,
    AuthenticateUserResponse,
)
from src.application.errors import AuthenticationError
from src.application.ports.i_event_bus import IEventBus
from src.application.ports.i_password_hasher import IPasswordHasher
from src.application.ports.i_user_repository import IUserRepository
from src.domain.value_objects.email import Email
from src.shared.kernel.result import Result


class AuthenticateUserUseCase:
    """
    Use Case: Аутентификация пользователя по email и паролю.
    
    Orchestration:
    1. Валидировать email (через Value Object)
    2. Загрузить пользователя из репозитория
    3. Проверить пароль через IPasswordHasher
    4. Сгенерировать JWT токены (access + refresh)
    5. Опубликовать UserAuthenticatedEvent
    6. Вернуть AuthenticateUserResponse с токенами
    
    Пример использования:
        use_case = AuthenticateUserUseCase(user_repo, hasher, event_bus)
        request = AuthenticateUserRequest(
            email="user@example.com",
            password="SecurePassword123!"
        )
        result = use_case.execute(request)
        
        match result:
            case Ok(response):
                print(f"Access token: {response.access_token}")
            case Err(error):
                print(f"Authentication failed: {error.message}")
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
            password_hasher: Сервис хеширования/проверки паролей
            event_bus: Шина событий для публикации domain events
        """
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._event_bus = event_bus
    
    async def execute(
        self, 
        request: AuthenticateUserRequest
    ) -> Result[AuthenticateUserResponse, AuthenticationError]:
        """
        Выполнить аутентификацию пользователя.
        
        Args:
            request: DTO с email и password
        
        Returns:
            Result[AuthenticateUserResponse, AuthenticationError]:
                Ok: Response с user_id, email, username, access_token, refresh_token, expires_at
                Err: AuthenticationError (invalid_credentials, user_not_found, account_deactivated)
        """
        # 1. Валидировать email через Value Object
        try:
            email = Email(request.email)
        except Exception:
            # Invalid email format
            return Result.failure(
                AuthenticationError.invalid_credentials()
            )
        
        # 2. Загрузить пользователя по email
        user = await self._user_repository.get_by_email(email)
        if user is None:
            return Result.failure(
                AuthenticationError.user_not_found(request.email)
            )
        
        # 3. Проверить, активен ли пользователь
        if not user.is_active:
            return Result.failure(
                AuthenticationError.account_deactivated()
            )
        
        # 4. Верифицировать пароль
        is_valid = await self._password_hasher.verify(
            plain_password=request.password,
            hashed_password=user.hashed_password,
        )
        if not is_valid:
            return Result.failure(
                AuthenticationError.invalid_credentials()
            )
        
        # 5. Генерация JWT токенов (в реальности используется JWT библиотека)
        # TODO: Интегрировать с реальной JWT генерацией (python-jose, PyJWT)
        access_token = self._generate_access_token(user.id.value, user.email.value)
        refresh_token = self._generate_refresh_token(user.id.value)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Access token TTL: 1 hour
        
        # 6. Публикация domain event (для аудита, логирования)
        # TODO: Реализовать UserAuthenticatedEvent в domain/events/
        # self._event_bus.publish(UserAuthenticatedEvent(user_id=user.id, timestamp=datetime.utcnow()))
        
        # 7. Сформировать Response DTO
        response = AuthenticateUserResponse(
            user_id=user.id.value,
            email=user.email.value,
            username=user.username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        
        return Result.success(response)
    
    def _generate_access_token(self, user_id: int, email: str) -> str:
        """
        Генерация access токена (placeholder).
        
        В production используйте:
        - python-jose для JWT
        - Секретный ключ из .env
        - Payload: user_id, email, exp, iat, jti
        """
        # Placeholder для демонстрации
        return f"access_token_{user_id}_{email}_{datetime.utcnow().isoformat()}"
    
    def _generate_refresh_token(self, user_id: int) -> str:
        """
        Генерация refresh токена (placeholder).
        
        В production:
        - Длительный TTL (7-30 дней)
        - Сохранение в Redis или БД
        - Rotation при использовании
        """
        # Placeholder для демонстрации
        return f"refresh_token_{user_id}_{datetime.utcnow().isoformat()}"
