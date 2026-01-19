"""
Dependency Injection Container для проекта.

Этот модуль связывает Application ports с Infrastructure implementations.
Реализует паттерн Dependency Injection для Clean Architecture.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from redis.asyncio import Redis

from src.application.ports.i_user_repository import IUserRepository
from src.application.ports.i_stream_repository import IStreamRepository
from src.application.ports.i_password_hasher import IPasswordHasher
from src.application.ports.i_telegram_client import ITelegramClient
from src.application.ports.i_event_bus import IEventBus

from src.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyStreamRepository,
)
from src.infrastructure.security import BcryptPasswordHasher
from src.infrastructure.external import PyrogramTelegramClient
from src.infrastructure.messaging import RedisEventBus


class Container:
    """
    DI Container для управления зависимостями.
    
    Связывает Application layer ports с Infrastructure implementations.
    Использует Factory паттерн для создания зависимостей.
    """
    
    def __init__(
        self,
        database_url: str,
        redis_url: str,
        telegram_api_id: int,
        telegram_api_hash: str,
        telegram_session_name: str = "streamer_bot"
    ):
        """
        Инициализация контейнера.
        
        Args:
            database_url: PostgreSQL connection URL
            redis_url: Redis connection URL
            telegram_api_id: Telegram API ID
            telegram_api_hash: Telegram API Hash
            telegram_session_name: Имя Telegram сессии
        """
        self._database_url = database_url
        self._redis_url = redis_url
        self._telegram_api_id = telegram_api_id
        self._telegram_api_hash = telegram_api_hash
        self._telegram_session_name = telegram_session_name
        
        # Создаем синглтоны
        self._db_engine = create_async_engine(
            database_url,
            echo=False,  # Set to True для SQL debug logging
            pool_pre_ping=True,  # Проверка соединений перед использованием
        )
        
        self._redis_client: Redis | None = None
        self._telegram_client: ITelegramClient | None = None
    
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Factory для SQLAlchemy сессий.
        
        Используется как dependency в FastAPI:
        ```python
        @router.post("/users")
        async def create_user(session: AsyncSession = Depends(container.get_db_session)):
            ...
        ```
        
        Yields:
            Async SQLAlchemy сессия
        """
        from sqlalchemy.ext.asyncio import AsyncSession as SessionType
        from sqlalchemy.orm import sessionmaker
        
        async_session = sessionmaker(
            self._db_engine,
            class_=SessionType,
            expire_on_commit=False
        )
        
        async with async_session() as session:
            yield session
    
    def get_user_repository(self, session: AsyncSession) -> IUserRepository:
        """
        Factory для User Repository.
        
        Args:
            session: SQLAlchemy сессия
            
        Returns:
            IUserRepository implementation
        """
        return SqlAlchemyUserRepository(session)
    
    def get_stream_repository(self, session: AsyncSession) -> IStreamRepository:
        """
        Factory для Stream Repository.
        
        Args:
            session: SQLAlchemy сессия
            
        Returns:
            IStreamRepository implementation
        """
        return SqlAlchemyStreamRepository(session)
    
    def get_password_hasher(self) -> IPasswordHasher:
        """
        Factory для Password Hasher.
        
        Returns:
            IPasswordHasher implementation (singleton)
        """
        return BcryptPasswordHasher(rounds=12)
    
    async def get_telegram_client(self) -> ITelegramClient:
        """
        Factory для Telegram Client.
        
        Returns:
            ITelegramClient implementation (singleton)
        """
        if self._telegram_client is None:
            self._telegram_client = PyrogramTelegramClient(
                api_id=self._telegram_api_id,
                api_hash=self._telegram_api_hash,
                session_name=self._telegram_session_name
            )
            await self._telegram_client.connect()
        
        return self._telegram_client
    
    async def get_event_bus(self) -> IEventBus:
        """
        Factory для Event Bus.
        
        Returns:
            IEventBus implementation
        """
        if self._redis_client is None:
            self._redis_client = await Redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        
        return RedisEventBus(self._redis_client)
    
    async def close(self) -> None:
        """
        Закрыть все соединения при остановке приложения.
        
        Вызывается в FastAPI shutdown event:
        ```python
        @app.on_event("shutdown")
        async def shutdown():
            await container.close()
        ```
        """
        # Закрываем Database Engine
        await self._db_engine.dispose()
        
        # Закрываем Redis
        if self._redis_client:
            await self._redis_client.close()
        
        # Закрываем Telegram
        if self._telegram_client:
            await self._telegram_client.disconnect()


# Глобальный экземпляр контейнера (будет инициализирован в FastAPI startup)
_container: Container | None = None


def get_container() -> Container:
    """
    Получить глобальный DI контейнер.
    
    Returns:
        Container instance
        
    Raises:
        RuntimeError: Если контейнер не инициализирован
    """
    if _container is None:
        raise RuntimeError("Container not initialized. Call init_container() first.")
    return _container


def init_container(
    database_url: str,
    redis_url: str,
    telegram_api_id: int,
    telegram_api_hash: str,
    telegram_session_name: str = "streamer_bot"
) -> Container:
    """
    Инициализировать глобальный DI контейнер.
    
    Вызывается в FastAPI startup event:
    ```python
    @app.on_event("startup")
    async def startup():
        init_container(
            database_url=settings.DATABASE_URL,
            redis_url=settings.REDIS_URL,
            ...
        )
    ```
    
    Args:
        database_url: PostgreSQL connection URL
        redis_url: Redis connection URL
        telegram_api_id: Telegram API ID
        telegram_api_hash: Telegram API Hash
        telegram_session_name: Имя Telegram сессии
        
    Returns:
        Инициализированный Container
    """
    global _container
    _container = Container(
        database_url=database_url,
        redis_url=redis_url,
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        telegram_session_name=telegram_session_name
    )
    return _container
