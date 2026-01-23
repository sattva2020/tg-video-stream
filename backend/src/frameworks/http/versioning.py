"""
API Versioning Middleware and Router Structure
FRAMEWORKS LAYER - HTTP (T048)

Система версионирования API для обеспечения обратной совместимости:
- Version detection from URL path or header
- Separate routers for v1 and v2
- Version deprecation warnings
- Automatic version routing

Использование:
    from src.frameworks.http.versioning import version_router, get_api_version
    app.include_router(version_router, prefix="/api")
"""

import logging
from enum import Enum
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Request
from starlette.datastructures import Headers


log = logging.getLogger(__name__)


# =============================================================================
# API Version Enum
# =============================================================================

class APIVersion(str, Enum):
    """Поддерживаемые версии API."""
    V1 = "v1"
    V2 = "v2"


# =============================================================================
# Version Detection
# =============================================================================

def extract_version_from_path(path: str) -> Optional[str]:
    """
    Извлечь версию API из URL пути.

    Args:
        path: URL путь (например, /api/v1/users)

    Returns:
        Optional[str]: Версия API (v1, v2) или None
    """
    import re

    # Ищем паттерн /api/v{digits}/
    match = re.search(r'/api/v(\d+)/', path)
    if match:
        version_num = match.group(1)
        return f"v{version_num}"

    return None


def extract_version_from_header(headers: Headers) -> Optional[str]:
    """
    Извлечь версию API из заголовка X-API-Version.

    Args:
        headers: Заголовки HTTP запроса

    Returns:
        Optional[str]: Версия API или None
    """
    return headers.get("X-API-Version")


def get_api_version(request: Request) -> APIVersion:
    """
    Определить версию API из запроса.

    Приоритет:
    1. URL path (/api/v1/, /api/v2/)
    2. Header X-API-Version
    3. Default (v1)

    Args:
        request: FastAPI запрос

    Returns:
        APIVersion: Версия API

    Raises:
        HTTPException: 400 если версия указана неверно
    """
    # 1. Проверяем URL path
    path_version = extract_version_from_path(request.url.path)
    if path_version:
        if path_version == "v1":
            return APIVersion.V1
        elif path_version == "v2":
            return APIVersion.V2
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version: {path_version}"
            )

    # 2. Проверяем заголовок
    header_version = extract_version_from_header(request.headers)
    if header_version:
        if header_version == "v1":
            return APIVersion.V1
        elif header_version == "v2":
            return APIVersion.V2
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version: {header_version}"
            )

    # 3. Default
    return APIVersion.V1


# =============================================================================
# Version Middleware
# =============================================================================

class VersioningMiddleware:
    """
    Middleware для добавления информации о версии API в ответ.

    Добавляет заголовки:
    - X-API-Version: Текущая версия
    - X-API-Deprecated: WARNING если версия устарела
    """

    # Устаревшие версии
    DEPRECATED_VERSIONS: set[str] = set()

    async def __call__(self, request: Request, call_next):
        """
        Обработка запроса с добавлением version headers.

        Args:
            request: HTTP запрос
            call_next: Следующий обработчик

        Returns:
            Response: HTTP ответ с добавленными заголовками
        """
        response = await call_next(request)

        # Определяем версию
        try:
            version = get_api_version(request)
            response.headers["X-API-Version"] = version.value

            # Добавляем предупреждение если версия устарела
            if version.value in self.DEPRECATED_VERSIONS:
                response.headers["X-API-Deprecated"] = "WARNING"

        except Exception as e:
            log.warning(f"Failed to determine API version: {e}")

        return response


# =============================================================================
# Version Routers
# =============================================================================

# Создаем отдельные роутеры для каждой версии
v1_router = APIRouter(
    prefix="/v1",
    tags=["API v1"],
)
"""
Роутер для API v1.

Использование:
    from src.frameworks.http.versioning import v1_router

    @v1_router.get("/users")
    async def list_users_v1():
        return {"version": "v1"}
"""

v2_router = APIRouter(
    prefix="/v2",
    tags=["API v2"],
)
"""
Роутер для API v2.

Использование:
    from src.frameworks.http.versioning import v2_router

    @v2_router.get("/users")
    async def list_users_v2():
        return {"version": "v2", "features": ["pagination", "filtering"]}
"""


# =============================================================================
# Version Info Endpoint
# =============================================================================

version_router = APIRouter(
    prefix="/api",
    tags=["API Versioning"],
)
"""
Главный роутер для управления версиями API.

Включает endpoint для получения информации о версиях.
"""


@version_router.get("/version")
async def get_version_info(request: Request) -> dict:
    """
    Получить информацию о версии API.

    Returns:
        dict: Информация о текущей версии, поддерживаемых версиях
    """
    version = get_api_version(request)

    return {
        "current_version": version.value,
        "supported_versions": ["v1", "v2"],
        "deprecated_versions": list(VersioningMiddleware.DEPRECATED_VERSIONS),
        "default_version": "v1",
        "documentation": {
            "v1": "/docs/v1",
            "v2": "/docs/v2",
        }
    }


@version_router.get("/versions")
async def list_versions() -> dict:
    """
    Получить список всех поддерживаемых версий API.

    Returns:
        dict: Список версий с описанием изменений
    """
    return {
        "versions": [
            {
                "version": "v1",
                "status": "stable",
                "released": "2024-01-01",
                "deprecated": False,
                "sunset_date": None,
                "features": [
                    "API Keys authentication",
                    "Webhooks",
                    "Stream management",
                    "Playlist management",
                ]
            },
            {
                "version": "v2",
                "status": "beta",
                "released": "2025-01-01",
                "deprecated": False,
                "sunset_date": None,
                "features": [
                    "Everything in v1",
                    "Improved error handling",
                    "Request/response validation",
                    "Rate limiting per API key",
                    "Webhook delivery guarantees",
                ]
            }
        ]
    }


# =============================================================================
# Version Deprecation Management
# =============================================================================

def mark_version_deprecated(version: Literal["v1", "v2"], sunset_date: Optional[str] = None):
    """
    Пометить версию API как устаревшую.

    Args:
        version: Версия для пометки
        sunset_date: Дата отключения (ISO 8601)
    """
    VersioningMiddleware.DEPRECATED_VERSIONS.add(version)
    log.warning(f"API version {version} is deprecated. Sunset: {sunset_date}")


def mark_version_supported(version: Literal["v1", "v2"]):
    """
    Убрать пометку устаревшей версии.

    Args:
        version: Версия для восстановления
    """
    VersioningMiddleware.DEPRECATED_VERSIONS.discard(version)
    log.info(f"API version {version} is now supported")


__all__ = [
    "APIVersion",
    "get_api_version",
    "version_router",
    "v1_router",
    "v2_router",
    "VersioningMiddleware",
    "mark_version_deprecated",
    "mark_version_supported",
]
