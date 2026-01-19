"""
Внешние сервисы и интеграции.

Этот пакет содержит реализации интеграций с внешними API.
"""

from .telegram_client import PyrogramTelegramClient

__all__ = [
    "PyrogramTelegramClient",
]
