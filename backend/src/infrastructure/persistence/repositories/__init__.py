"""
Репозитории для доступа к хранилищу данных.

Этот пакет содержит реализации repository ports из application слоя.
"""

from .sqlalchemy_user_repository import SqlAlchemyUserRepository
from .sqlalchemy_stream_repository import SqlAlchemyStreamRepository
from .sqlalchemy_poll_repository import SqlAlchemyPollRepository, PollRepository
from .in_memory import InMemoryUserRepository, InMemoryStreamRepository

__all__ = [
    # SQLAlchemy implementations
    "SqlAlchemyUserRepository",
    "SqlAlchemyStreamRepository",
    "SqlAlchemyPollRepository",
    "PollRepository",  # Alias for SqlAlchemyPollRepository
    # In-memory implementations (для тестов)
    "InMemoryUserRepository",
    "InMemoryStreamRepository",
]
