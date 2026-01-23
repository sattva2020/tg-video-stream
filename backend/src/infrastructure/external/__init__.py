"""
Внешние сервисы и интеграции.

Этот пакет содержит реализации интеграций с внешними API.
"""

from .telegram_client import PyrogramTelegramClient
from .cloudflare_client import CloudflareCDNClient
from .cloudfront_client import CloudFrontCDNClient
from .fastly_client import FastlyCDNClient

__all__ = [
    "PyrogramTelegramClient",
    "CloudflareCDNClient",
    "CloudFrontCDNClient",
    "FastlyCDNClient",
]
