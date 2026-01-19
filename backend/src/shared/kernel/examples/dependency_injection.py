"""
Dependency Injection Example - Clean Architecture

Пример Composition Root и фабрик для DI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Optional, Callable
from functools import lru_cache


# ========================
# Ports (Application Layer)
# ========================

class IUserRepository(Protocol):
    """Порт репозитория пользователей."""
    
    async def find_by_email(self, email: str) -> Optional[dict]:
        ...
    
    async def save(self, user: dict) -> int:
        ...


class IPasswordHasher(Protocol):
    """Порт для хеширования паролей."""
    
    def hash(self, password: str) -> str:
        ...
    
    def verify(self, password: str, hashed: str) -> bool:
        ...


class IEmailService(Protocol):
    """Порт для отправки email."""
    
    async def send(self, to: str, subject: str, body: str) -> bool:
        ...


# ========================
# Use Case
# ========================

@dataclass(frozen=True)
class RegisterUserRequest:
    email: str
    password: str
    name: str


@dataclass(frozen=True)
class RegisterUserResponse:
    user_id: int
    email: str


class RegisterUserUseCase:
    """Use Case с внедрёнными зависимостями."""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: IPasswordHasher,
        email_service: IEmailService
    ):
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._email_service = email_service
    
    async def execute(self, request: RegisterUserRequest) -> RegisterUserResponse:
        # Проверяем уникальность email
        existing = await self._user_repository.find_by_email(request.email)
        if existing:
            raise ValueError("Email already registered")
        
        # Хешируем пароль
        hashed_password = self._password_hasher.hash(request.password)
        
        # Сохраняем пользователя
        user = {
            "email": request.email,
            "password_hash": hashed_password,
            "name": request.name
        }
        user_id = await self._user_repository.save(user)
        
        # Отправляем welcome email
        await self._email_service.send(
            to=request.email,
            subject="Welcome!",
            body=f"Hello {request.name}, welcome to our service!"
        )
        
        return RegisterUserResponse(user_id=user_id, email=request.email)


# ========================
# Infrastructure Implementations
# ========================

class InMemoryUserRepository:
    """In-Memory реализация для тестов."""
    
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._next_id = 1
    
    async def find_by_email(self, email: str) -> Optional[dict]:
        return self._users.get(email)
    
    async def save(self, user: dict) -> int:
        user_id = self._next_id
        self._next_id += 1
        user["id"] = user_id
        self._users[user["email"]] = user
        return user_id


class BcryptPasswordHasher:
    """BCrypt реализация."""
    
    def hash(self, password: str) -> str:
        # В реальности: bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        return f"bcrypt:{password}:hashed"
    
    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"bcrypt:{password}:hashed"


class SmtpEmailService:
    """SMTP реализация."""
    
    def __init__(self, smtp_host: str, smtp_port: int):
        self._host = smtp_host
        self._port = smtp_port
    
    async def send(self, to: str, subject: str, body: str) -> bool:
        print(f"[SMTP] Sending email to {to}: {subject}")
        return True


class MockEmailService:
    """Mock для тестов."""
    
    def __init__(self):
        self.sent_emails: list[dict] = []
    
    async def send(self, to: str, subject: str, body: str) -> bool:
        self.sent_emails.append({"to": to, "subject": subject, "body": body})
        return True


# ========================
# DI Container
# ========================

class DIContainer:
    """
    Простой DI контейнер.
    
    В production обычно используют:
    - dependency-injector
    - FastAPI Depends
    - punq
    """
    
    def __init__(self):
        self._factories: dict[type, Callable] = {}
        self._singletons: dict[type, object] = {}
    
    def register(
        self, 
        interface: type, 
        factory: Callable,
        singleton: bool = False
    ) -> None:
        """Регистрирует фабрику для интерфейса."""
        if singleton:
            self._factories[interface] = lru_cache(maxsize=1)(factory)
        else:
            self._factories[interface] = factory
    
    def resolve(self, interface: type):
        """Разрешает зависимость."""
        if interface not in self._factories:
            raise KeyError(f"No factory registered for {interface}")
        return self._factories[interface]()


# ========================
# Composition Root
# ========================

def create_production_container() -> DIContainer:
    """
    Composition Root для production.
    
    Здесь собираются все зависимости приложения.
    Вызывается один раз при старте приложения.
    """
    container = DIContainer()
    
    # Infrastructure
    container.register(
        IUserRepository,
        lambda: InMemoryUserRepository(),  # В prod: SqlAlchemyUserRepository(session)
        singleton=True
    )
    
    container.register(
        IPasswordHasher,
        lambda: BcryptPasswordHasher(),
        singleton=True
    )
    
    container.register(
        IEmailService,
        lambda: SmtpEmailService("smtp.example.com", 587),
        singleton=True
    )
    
    # Use Cases
    container.register(
        RegisterUserUseCase,
        lambda: RegisterUserUseCase(
            user_repository=container.resolve(IUserRepository),
            password_hasher=container.resolve(IPasswordHasher),
            email_service=container.resolve(IEmailService)
        )
    )
    
    return container


def create_test_container() -> DIContainer:
    """
    Composition Root для тестов.
    
    Использует mock-реализации.
    """
    container = DIContainer()
    
    # Mock implementations
    container.register(IUserRepository, InMemoryUserRepository, singleton=True)
    container.register(IPasswordHasher, BcryptPasswordHasher, singleton=True)
    container.register(IEmailService, MockEmailService, singleton=True)
    
    container.register(
        RegisterUserUseCase,
        lambda: RegisterUserUseCase(
            user_repository=container.resolve(IUserRepository),
            password_hasher=container.resolve(IPasswordHasher),
            email_service=container.resolve(IEmailService)
        )
    )
    
    return container


# ========================
# FastAPI Integration Example
# ========================

def get_fastapi_dependencies():
    """
    Пример интеграции с FastAPI Depends.
    
    Usage:
        @app.post("/register")
        async def register(
            request: RegisterRequest,
            use_case: RegisterUserUseCase = Depends(get_register_use_case)
        ):
            return await use_case.execute(request)
    """
    from functools import lru_cache
    
    @lru_cache
    def get_container() -> DIContainer:
        return create_production_container()
    
    def get_user_repository() -> IUserRepository:
        return get_container().resolve(IUserRepository)
    
    def get_password_hasher() -> IPasswordHasher:
        return get_container().resolve(IPasswordHasher)
    
    def get_email_service() -> IEmailService:
        return get_container().resolve(IEmailService)
    
    def get_register_use_case(
        # FastAPI автоматически внедрит эти зависимости
        user_repo: IUserRepository = None,  # Depends(get_user_repository)
        hasher: IPasswordHasher = None,     # Depends(get_password_hasher)
        email: IEmailService = None         # Depends(get_email_service)
    ) -> RegisterUserUseCase:
        return RegisterUserUseCase(
            user_repository=user_repo or get_user_repository(),
            password_hasher=hasher or get_password_hasher(),
            email_service=email or get_email_service()
        )
    
    return {
        "get_user_repository": get_user_repository,
        "get_password_hasher": get_password_hasher,
        "get_email_service": get_email_service,
        "get_register_use_case": get_register_use_case,
    }


# ========================
# Usage Example
# ========================

async def main():
    """Демонстрация DI."""
    
    print("=== Production Container ===")
    prod_container = create_production_container()
    
    use_case = prod_container.resolve(RegisterUserUseCase)
    result = await use_case.execute(RegisterUserRequest(
        email="user@example.com",
        password="secret123",
        name="John Doe"
    ))
    print(f"Registered: {result.email} (ID: {result.user_id})")
    
    print("\n=== Test Container ===")
    test_container = create_test_container()
    
    use_case = test_container.resolve(RegisterUserUseCase)
    result = await use_case.execute(RegisterUserRequest(
        email="test@example.com",
        password="test123",
        name="Test User"
    ))
    print(f"Registered: {result.email} (ID: {result.user_id})")
    
    # Проверяем mock
    email_service = test_container.resolve(IEmailService)
    print(f"Emails sent: {len(email_service.sent_emails)}")
    print(f"Last email to: {email_service.sent_emails[-1]['to']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
