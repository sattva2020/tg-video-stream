"""
API Version Headers Middleware for FastAPI.

Adds API version information and deprecation warnings to HTTP responses.
Provides clients with visibility into API version status and sunset dates.

Architecture:
- Version Detection: Extracts API version from URL path (/api/v1/, /api/v2/)
- Header Injection: Adds X-API-Version, X-API-Deprecated, X-API-Sunset headers
- Deprecation Management: Tracks deprecated versions and sunset dates
- Documentation Links: Provides links to version-specific documentation

Headers Added:
- X-API-Version: Current API version (v1, v2)
- X-API-Deprecated: "true" if version is deprecated
- X-API-Sunset: Sunset date if deprecated (ISO 8601)
- X-API-Docs: Link to version-specific documentation

Usage:
    app.add_middleware(VersionHeadersMiddleware)
"""

import logging
from typing import Optional, Dict
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.frameworks.http.versioning import get_api_version, APIVersion


logger = logging.getLogger(__name__)


class VersionHeadersMiddleware(BaseHTTPMiddleware):
    """
    API version headers middleware.

    Adds version information and deprecation warnings to all API responses.
    Helps clients track API lifecycle and plan migrations.
    """

    # Version metadata and deprecation information
    VERSION_INFO: Dict[str, Dict[str, Optional[str]]] = {
        "v1": {
            "status": "stable",
            "sunset_date": None,
            "docs_url": "/docs",
            "migration_guide": None,
        },
        "v2": {
            "status": "beta",
            "sunset_date": None,
            "docs_url": "/docs/v2",
            "migration_guide": None,
        },
    }

    def __init__(self, app):
        """
        Initialize version headers middleware.

        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add version headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or handler in chain

        Returns:
            Response with version headers added
        """
        try:
            # Get the response from the next handler
            response = await call_next(request)

            # Skip version headers for non-API paths
            if self._should_skip_version_headers(request.url.path):
                return response

            # Extract API version from request
            version = self._extract_version(request)

            if version:
                # Add standard version header
                response.headers["X-API-Version"] = version

                # Add version-specific headers
                version_metadata = self.VERSION_INFO.get(version, {})

                # Add deprecation warning if applicable
                if version_metadata.get("status") == "deprecated":
                    response.headers["X-API-Deprecated"] = "true"

                    # Add sunset date if available
                    sunset_date = version_metadata.get("sunset_date")
                    if sunset_date:
                        response.headers["X-API-Sunset"] = sunset_date

                    # Add migration guide if available
                    migration_guide = version_metadata.get("migration_guide")
                    if migration_guide:
                        response.headers["X-API-Migration-Guide"] = migration_guide

                    self.logger.warning(
                        f"Request to deprecated API version: {version}, "
                        f"sunset: {sunset_date}"
                    )

                # Add documentation link
                docs_url = version_metadata.get("docs_url")
                if docs_url:
                    response.headers["X-API-Docs"] = docs_url

                # Add supported versions header
                supported_versions = self._get_supported_versions()
                response.headers["X-API-Supported-Versions"] = ", ".join(supported_versions)

            return response

        except Exception as e:
            self.logger.error(f"Version headers middleware error: {e}")
            # On error, return response without headers (fail silently)
            return await call_next(request)

    def _should_skip_version_headers(self, path: str) -> bool:
        """
        Check if path should skip version headers.

        Args:
            path: Request URL path

        Returns:
            bool: True if headers should be skipped
        """
        skip_paths = [
            "/health",
            "/metrics",
            "/favicon.ico",
            "/static/",
        ]

        # Skip non-API paths
        if not path.startswith("/api/"):
            return True

        # Skip specific paths
        return any(path.startswith(p) for p in skip_paths)

    def _extract_version(self, request: Request) -> Optional[str]:
        """
        Extract API version from request.

        Args:
            request: FastAPI request object

        Returns:
            Optional[str]: Version string (v1, v2) or None
        """
        try:
            # Use the existing version detection logic
            version = get_api_version(request)
            return version.value
        except Exception as e:
            self.logger.debug(f"Failed to extract API version: {e}")
            return None

    def _get_supported_versions(self) -> list[str]:
        """
        Get list of supported API versions.

        Returns:
            list[str]: List of supported version strings
        """
        supported = []
        for version, metadata in self.VERSION_INFO.items():
            status = metadata.get("status")
            if status in ["stable", "beta", "deprecated"]:
                supported.append(version)
        return sorted(supported)


def mark_version_deprecated(
    version: str,
    sunset_date: Optional[str] = None,
    migration_guide: Optional[str] = None
):
    """
    Mark an API version as deprecated.

    Args:
        version: Version to mark (e.g., "v1")
        sunset_date: Sunset date in ISO 8601 format (YYYY-MM-DD)
        migration_guide: URL to migration guide
    """
    if version in VersionHeadersMiddleware.VERSION_INFO:
        VersionHeadersMiddleware.VERSION_INFO[version]["status"] = "deprecated"
        VersionHeadersMiddleware.VERSION_INFO[version]["sunset_date"] = sunset_date
        VersionHeadersMiddleware.VERSION_INFO[version]["migration_guide"] = migration_guide

        logger.warning(
            f"API version {version} marked as deprecated. "
            f"Sunset: {sunset_date}, Migration guide: {migration_guide}"
        )


def mark_version_supported(version: str):
    """
    Mark an API version as supported (not deprecated).

    Args:
        version: Version to mark as supported
    """
    if version in VersionHeadersMiddleware.VERSION_INFO:
        VersionHeadersMiddleware.VERSION_INFO[version]["status"] = "stable"
        VersionHeadersMiddleware.VERSION_INFO[version]["sunset_date"] = None
        VersionHeadersMiddleware.VERSION_INFO[version]["migration_guide"] = None

        logger.info(f"API version {version} marked as supported")


def set_version_info(
    version: str,
    status: str,
    docs_url: Optional[str] = None,
    sunset_date: Optional[str] = None,
    migration_guide: Optional[str] = None
):
    """
    Set metadata for an API version.

    Args:
        version: Version identifier (e.g., "v1", "v2")
        status: Version status (stable, beta, deprecated)
        docs_url: URL to version-specific documentation
        sunset_date: Sunset date for deprecated versions
        migration_guide: URL to migration guide
    """
    VersionHeadersMiddleware.VERSION_INFO[version] = {
        "status": status,
        "sunset_date": sunset_date,
        "docs_url": docs_url,
        "migration_guide": migration_guide,
    }

    logger.info(
        f"API version {version} info updated: "
        f"status={status}, docs={docs_url}, sunset={sunset_date}"
    )


__all__ = [
    "VersionHeadersMiddleware",
    "mark_version_deprecated",
    "mark_version_supported",
    "set_version_info",
]
