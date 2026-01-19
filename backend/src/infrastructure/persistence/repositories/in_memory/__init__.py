"""
In-memory репозитории для тестирования.

Эти репозитории хранят entities в памяти без базы данных.
"""

from .user_repository import InMemoryUserRepository
from .stream_repository import InMemoryStreamRepository

__all__ = [
    "InMemoryUserRepository",
    "InMemoryStreamRepository",
]
