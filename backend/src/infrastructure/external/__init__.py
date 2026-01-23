"""
Внешние сервисы и интеграции.

Этот пакет содержит реализации интеграций с внешними API.
"""

from .telegram_client import PyrogramTelegramClient
from .cloudflare_client import CloudflareCDNClient

__all__ = [
    "PyrogramTelegramClient",
    "CloudflareCDNClient",
]
