"""
Cloudflare CDN клиент для управления кэшем и edge локациями.

Этот модуль реализует ICDNProvider port используя Cloudflare API v4.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.application.ports.i_cdn_provider import ICDNProvider, CDNHealthStatus
from src.domain.errors import (
    CDNConnectionError,
    CDNAuthenticationError,
    CDNPurgeError,
    CDNConfigurationError
)


class CloudflareCDNClient:
    """
    Cloudflare реализация ICDNProvider.

    Использует Cloudflare API v4 для управления CDN кэшем,
    purge запросами, edge локациями и метриками.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        zone_id: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        """
        Инициализация клиента.

        Args:
            api_token: Cloudflare API токен (или из env CLOUDFLARE_API_TOKEN)
            zone_id: ID зоны Cloudflare (или из env CLOUDFLARE_ZONE_ID)
            account_id: ID аккаунта Cloudflare (для некоторых операций)
        """
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN")
        self.zone_id = zone_id or os.getenv("CLOUDFLARE_ZONE_ID")
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")

        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN is required")

        if not self.zone_id:
            raise ValueError("CLOUDFLARE_ZONE_ID is required")

        # Cloudflare API v4 base URL
        self.api_url = "https://api.cloudflare.com/client/v4"

        # HTTP client session
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Enter async context manager."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """
        Получить заголовки для Cloudflare API запросов.

        Returns:
            Dict[str, str]: Заголовки с авторизацией
        """
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def _handle_api_error(self, status_code: int, response_data: Dict[str, Any]) -> None:
        """
        Обработать ошибку Cloudflare API.

        Args:
            status_code: HTTP статус код
            response_data: Ответ от API

        Raises:
            CDNAuthenticationError: При проблемах с аутентификацией
            CDNConnectionError: При ошибках подключения
            CDNPurgeError: При ошибках очистки кэша
            CDNConfigurationError: При ошибках конфигурации
        """
        errors = response_data.get("errors", [])
        if errors:
            error_message = errors[0].get("message", "Unknown error")
            error_code = errors[0].get("code", "unknown")

            # Authentication errors
            if status_code == 401 or error_code in [9103, 9104, 9105, 9106, 9107, 9109, 9111]:
                raise CDNAuthenticationError(
                    f"Cloudflare authentication failed: {error_message}"
                )

            # Permission errors
            if status_code == 403:
                raise CDNAuthenticationError(
                    f"Cloudflare permission denied: {error_message}"
                )

            # Zone not found
            if status_code == 404 or error_code == 1000:
                raise CDNConfigurationError(
                    f"Cloudflare zone not found: {self.zone_id}"
                )

            # Rate limit
            if status_code == 429 or error_code == 9108:
                raise CDNConnectionError(
                    f"Cloudflare rate limit exceeded: {error_message}"
                )

            # Generic API error
            raise CDNConnectionError(
                f"Cloudflare API error (code {error_code}): {error_message}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def purge_cache(
        self,
        urls: List[str],
        purge_all: bool = False
    ) -> Dict[str, Any]:
        """
        Очистить кэш CDN для указанных URL.

        Args:
            urls: Список URL для очистки кэша
            purge_all: Если True, очистить весь кэш

        Returns:
            Dict[str, Any]: Результат операции:
            {
                "success": bool,
                "purged_urls": List[str],
                "error": Optional[str]
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
            CDNAuthenticationError: При проблемах с аутентификацией
            CDNPurgeError: При ошибке очистки кэша
        """
        if not self.session:
            raise RuntimeError(
                "Cloudflare client not initialized. Use async context manager."
            )

        purge_url = f"{self.api_url}/zones/{self.zone_id}/purge_cache"

        headers = self._get_headers()

        # Формируем тело запроса
        if purge_all:
            payload = {"purge_everything": True}
        else:
            payload = {"files": urls}

        try:
            async with self.session.post(
                purge_url,
                json=payload,
                headers=headers
            ) as response:
                response_data = await response.json()

                if response.status == 200 and response_data.get("success"):
                    return {
                        "success": True,
                        "purged_urls": urls if not purge_all else [],
                        "error": None
                    }
                else:
                    self._handle_api_error(response.status, response_data)
                    raise CDNPurgeError(
                        f"Failed to purge cache: {response_data}"
                    )

        except (CDNAuthenticationError, CDNConfigurationError, CDNPurgeError):
            raise  # Re-raise domain errors
        except aiohttp.ClientError as e:
            raise CDNConnectionError(
                f"Cloudflare API connection error: {e}"
            ) from e
        except Exception as e:
            raise CDNPurgeError(f"Unexpected purge error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Получить статус здоровья CDN.

        Returns:
            Dict[str, Any]: Статус здоровья:
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
        if not self.session:
            raise RuntimeError(
                "Cloudflare client not initialized. Use async context manager."
            )

        # Используем zone analytics для проверки здоровья
        start_time = datetime.now()

        try:
            # Запрос к zone endpoint для проверки доступности
            zone_url = f"{self.api_url}/zones/{self.zone_id}"
            headers = self._get_headers()

            async with self.session.get(
                zone_url,
                headers=headers
            ) as response:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                response_data = await response.json()

                if response.status == 200 and response_data.get("success"):
                    # Zone доступна - считаем CDN здоровым
                    # Cloudflare не предоставляет детальную информацию о здоровье edge узлов
                    # через публичный API, поэтому используем uptime как индикатор
                    return {
                        "status": CDNHealthStatus.HEALTHY,
                        "last_check": datetime.now().isoformat(),
                        "response_time_ms": response_time,
                        "edge_nodes_healthy": 0,  # Cloudflare не предоставляет эту инфу
                        "edge_nodes_total": 0  # Cloudflare не предоставляет эту инфу
                    }
                else:
                    self._handle_api_error(response.status, response_data)
                    return {
                        "status": CDNHealthStatus.UNHEALTHY,
                        "last_check": datetime.now().isoformat(),
                        "response_time_ms": response_time,
                        "edge_nodes_healthy": 0,
                        "edge_nodes_total": 0
                    }

        except (CDNAuthenticationError, CDNConfigurationError):
            # Ошибки аутентификации/конфигурации считаем unhealthy
            return {
                "status": CDNHealthStatus.UNHEALTHY,
                "last_check": datetime.now().isoformat(),
                "response_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "edge_nodes_healthy": 0,
                "edge_nodes_total": 0
            }
        except aiohttp.ClientError as e:
            raise CDNConnectionError(
                f"Cloudflare API connection error: {e}"
            ) from e
        except Exception as e:
            return {
                "status": CDNHealthStatus.UNHEALTHY,
                "last_check": datetime.now().isoformat(),
                "response_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "edge_nodes_healthy": 0,
                "edge_nodes_total": 0
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def list_edge_locations(self) -> List[Dict[str, Any]]:
        """
        Получить список доступных edge локаций.

        Cloudflare имеет более 270+ data centers по всему миру.
        Возвращаем список основных PoP локаций.

        Returns:
            List[Dict[str, Any]]: Список edge локаций:
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
        # Cloudflare не предоставляет публичный API для получения списка PoP
        # Возвращаем статический список основных локаций на основе публичной информации
        # https://www.cloudflare.com/network/

        return [
            {
                "code": "AMS",
                "city": "Amsterdam",
                "country": "Netherlands",
                "region": "Europe",
                "latitude": 52.3676,
                "longitude": 4.9041,
                "active": True
            },
            {
                "code": "LHR",
                "city": "London",
                "country": "United Kingdom",
                "region": "Europe",
                "latitude": 51.4700,
                "longitude": -0.4543,
                "active": True
            },
            {
                "code": "FRA",
                "city": "Frankfurt",
                "country": "Germany",
                "region": "Europe",
                "latitude": 50.1155,
                "longitude": 8.5715,
                "active": True
            },
            {
                "code": "CDG",
                "city": "Paris",
                "country": "France",
                "region": "Europe",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "active": True
            },
            {
                "code": "JFK",
                "city": "New York",
                "country": "United States",
                "region": "North America",
                "latitude": 40.6413,
                "longitude": -73.7781,
                "active": True
            },
            {
                "code": "LAX",
                "city": "Los Angeles",
                "country": "United States",
                "region": "North America",
                "latitude": 33.9416,
                "longitude": -118.4085,
                "active": True
            },
            {
                "code": "SFO",
                "city": "San Francisco",
                "country": "United States",
                "region": "North America",
                "latitude": 37.6213,
                "longitude": -122.379,
                "active": True
            },
            {
                "code": "ORD",
                "city": "Chicago",
                "country": "United States",
                "region": "North America",
                "latitude": 41.9742,
                "longitude": -87.9073,
                "active": True
            },
            {
                "code": "YYZ",
                "city": "Toronto",
                "country": "Canada",
                "region": "North America",
                "latitude": 43.6777,
                "longitude": -79.6248,
                "active": True
            },
            {
                "code": "NRT",
                "city": "Tokyo",
                "country": "Japan",
                "region": "Asia",
                "latitude": 35.7720,
                "longitude": 140.3929,
                "active": True
            },
            {
                "code": "SIN",
                "city": "Singapore",
                "country": "Singapore",
                "region": "Asia",
                "latitude": 1.3644,
                "longitude": 103.9915,
                "active": True
            },
            {
                "code": "HKG",
                "city": "Hong Kong",
                "country": "Hong Kong",
                "region": "Asia",
                "latitude": 22.3080,
                "longitude": 113.9185,
                "active": True
            },
            {
                "code": "SYD",
                "city": "Sydney",
                "country": "Australia",
                "region": "Oceania",
                "latitude": -33.9399,
                "longitude": 151.1753,
                "active": True
            },
            {
                "code": "GRU",
                "city": "São Paulo",
                "country": "Brazil",
                "region": "South America",
                "latitude": -23.4356,
                "longitude": -46.4731,
                "active": True
            },
            {
                "code": "DXB",
                "city": "Dubai",
                "country": "United Arab Emirates",
                "region": "Middle East",
                "latitude": 25.2532,
                "longitude": 55.3657,
                "active": True
            }
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def configure_cache_rules(
        self,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
            Dict[str, Any]: Результат операции:
            {
                "success": bool,
                "applied_rules": int,
                "error": Optional[str]
            }

        Raises:
            CDNConnectionError: При ошибке подключения к CDN API
            CDNConfigurationError: При ошибке конфигурации
        """
        if not self.session:
            raise RuntimeError(
                "Cloudflare client not initialized. Use async context manager."
            )

        # Cloudflare использует Page Rules для управления кэшем
        # Создаём page rules для каждого паттерна
        applied_rules = 0

        try:
            for rule in rules:
                page_rule_url = f"{self.api_url}/zones/{self.zone_id}/pagerules"
                headers = self._get_headers()

                # Формируем выражение для URL pattern
                pattern = rule.get("pattern", "*")
                url_pattern = f"*://{pattern}*" if not pattern.startswith("http") else pattern

                # Формируем действия для правила
                actions = []

                # Cache level (cache everything)
                cache_ttl = rule.get("cache_ttl", 86400)
                actions.append({
                    "id": "cache_level",
                    "value": "cache_everything"
                })

                # Edge cache TTL
                actions.append({
                    "id": "edge_cache_ttl",
                    "value": cache_ttl
                })

                # Browser cache TTL
                browser_ttl = rule.get("browser_ttl", 3600)
                actions.append({
                    "id": "browser_cache_ttl",
                    "value": browser_ttl
                })

                # Ignore query string if cache_key_static is True
                if rule.get("cache_key_static", True):
                    actions.append({
                        "id": "cache_key_fields",
                        "value": {"ignore": ["url", "query_string"]}
                    })

                payload = {
                    "targets": [
                        {
                            "target": "url",
                            "constraint": {
                                "operator": "matches",
                                "value": url_pattern
                            }
                        }
                    ],
                    "actions": actions,
                    "status": "active"
                }

                async with self.session.post(
                    page_rule_url,
                    json=payload,
                    headers=headers
                ) as response:
                    response_data = await response.json()

                    if response.status == 200 and response_data.get("success"):
                        applied_rules += 1
                    else:
                        self._handle_api_error(response.status, response_data)
                        raise CDNConfigurationError(
                            f"Failed to create page rule: {response_data}"
                        )

            return {
                "success": True,
                "applied_rules": applied_rules,
                "error": None
            }

        except (CDNAuthenticationError, CDNConfigurationError):
            raise  # Re-raise domain errors
        except aiohttp.ClientError as e:
            raise CDNConnectionError(
                f"Cloudflare API connection error: {e}"
            ) from e
        except Exception as e:
            raise CDNConfigurationError(f"Unexpected configuration error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def get_usage_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Получить метрики использования CDN за период.

        Args:
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Dict[str, Any]: Метрики использования:
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
        if not self.session:
            raise RuntimeError(
                "Cloudflare client not initialized. Use async context manager."
            )

        # Cloudflare GraphQL Analytics API требуется для детальной аналитики
        # Для базовой реализации возвращаем mock данные
        # TODO: Implement GraphQL analytics query

        return {
            "total_bandwidth_gb": 0.0,
            "total_requests": 0,
            "cache_hit_ratio": 0.0,
            "average_response_time_ms": 0.0,
            "by_region": {},
            "note": "Cloudflare GraphQL Analytics API implementation required"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, CDNConnectionError))
    )
    async def test_connection(self) -> bool:
        """
        Проверить подключение к CDN API.

        Returns:
            bool: True если подключение успешно

        Raises:
            CDNConnectionError: При ошибке подключения
        """
        try:
            health_status = await self.get_health_status()
            return health_status["status"] == CDNHealthStatus.HEALTHY
        except Exception as e:
            raise CDNConnectionError(f"Connection test failed: {e}") from e
