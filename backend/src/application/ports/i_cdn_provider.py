"""
ICDNProvider Port Interface

Контракт для взаимодействия с CDN провайдерами (Cloudflare, CloudFront, Fastly).
"""

from typing import Protocol, Optional
from datetime import datetime


class CDNHealthStatus:
    """Статус здоровья CDN."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ICDNProvider(Protocol):
    """
    Интерфейс CDN провайдера.

    Изолирует Application layer от конкретной CDN библиотеки.
    Позволяет легко менять реализацию или создавать моки для тестов.

    Examples:
        >>> await client.purge_cache(["https://example.com/video1.mp4"])
        >>> await client.get_health_status()
        >>> await client.list_edge_locations()
    """

    async def purge_cache(
        self,
        urls: list[str],
        purge_all: bool = False
    ) -> dict[str, any]:
        """
        Очистить кэш CDN для указанных URL.

        Args:
            urls: Список URL для очистки кэша
            purge_all: Если True, очистить весь кэш

        Returns:
            dict с результатом операции:
            {
                "success": bool,
                "purged_urls": list[str],
                "error": Optional[str]
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
            CDNAuthenticationError: При проблемах с аутентификацией
            CDNPurgeError: При ошибке очистки кэша
        """
        ...

    async def get_health_status(self) -> dict[str, any]:
        """
        Получить статус здоровья CDN.

        Returns:
            dict со статусом:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "last_check": datetime,
                "response_time_ms": float,
                "edge_nodes_healthy": int,
                "edge_nodes_total": int
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
        """
        ...

    async def list_edge_locations(self) -> list[dict[str, any]]:
        """
        Получить список доступных edge локаций.

        Returns:
            list[dict] с информацией о локациях:
            [
                {
                    "code": "AMS",  # IATA код города
                    "city": "Amsterdam",
                    "country": "Netherlands",
                    "region": "Europe",
                    "latitude": float,
                    "longitude": float,
                    "active": bool
                }
            ]

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
        """
        ...

    async def configure_cache_rules(
        self,
        rules: list[dict[str, any]]
    ) -> dict[str, any]:
        """
        Настроить правила кэширования для CDN.

        Args:
            rules: Список правил кэширования:
            [
                {
                    "pattern": "*.mp4",
                    "cache_ttl": 86400,  # секунды
                    "cache_key_static": True,  # игнорировать query params
                    "browser_ttl": 3600
                }
            ]

        Returns:
            dict с результатом операции:
            {
                "success": bool,
                "applied_rules": int,
                "error": Optional[str]
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
            CDNConfigurationError: При ошибке конфигурации
        """
        ...

    async def get_usage_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, any]:
        """
        Получить метрики использования CDN за период.

        Args:
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            dict с метриками:
            {
                "total_bandwidth_gb": float,
                "total_requests": int,
                "cache_hit_ratio": float,  # 0.0 - 1.0
                "average_response_time_ms": float,
                "by_region": {
                    "Europe": {...},
                    "Asia": {...}
                }
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
        """
        ...

    async def test_connection(self) -> bool:
        """
        Проверить подключение к CDN API.

        Returns:
            bool: True если подключение успешно

        Raises:
            CDNConnectionError: При ошибке подключения
        """
        ...
