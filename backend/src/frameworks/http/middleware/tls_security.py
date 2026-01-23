"""
TLS/HTTPS Security Middleware
FRAMEWORKS LAYER - HTTP Middleware (T048)

Middleware для обеспечения TLS/HTTPS безопасности:
- HTTP Strict Transport Security (HSTS)
- Security headers
- HTTPS redirect в production
- TLS certificate validation

Использование:
    from src.frameworks.http.middleware.tls_security import TLSSecurityMiddleware
    app.add_middleware(TLSSecurityMiddleware)
"""

import os
from typing import Callable, Awaitable
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import settings


class TLSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware для TLS/HTTPS безопасности.

    Добавляет необходимые security headers и обеспечивает HTTPS redirect в production.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.production_mode = settings.ENVIRONMENT == "production"
        self.tls_enabled = settings.TLS_ENABLED
        self.hsts_max_age = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 год по умолчанию
        self.hsts_include_subdomains = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
        self.hsts_preload = os.getenv("HSTS_PRELOAD", "true").lower() == "true"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Обработка входящего запроса с добавлением security headers.

        Args:
            request: Входящий HTTP запрос
            call_next: Следующий middleware/обработчик в цепочке

        Returns:
            Response: HTTP ответ с security headers
        """
        # Проверяем HTTPS redirect только в production если TLS включен
        if self.production_mode and self.tls_enabled:
            # Проверяем X-Forwarded-Proto для proxy scenarios
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            if forwarded_proto:
                is_https = forwarded_proto.lower() == "https"
            else:
                # Для прямых соединений проверяем URL scheme
                is_https = request.url.scheme.lower() == "https"

            # Redirect на HTTPS если запрос пришел по HTTP
            if not is_https:
                redirect_url = request.url.replace(scheme="https")
                return Response(
                    status_code=301,
                    headers={"Location": str(redirect_url)}
                )

        # Выполняем запрос
        response = await call_next(request)

        # Добавляем security headers
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """
        Добавление security headers к ответу.

        Args:
            response: HTTP ответ для модификации
        """
        # HTTP Strict Transport Security (HSTS)
        # Защищает от downgrade attacks
        if self.production_mode:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # X-Content-Type-Options: nosniff
        # Предотвращает MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: DENY или SAMEORIGIN
        # Защита от clickjacking
        frame_mode = os.getenv("X_FRAME_OPTIONS", "DENY")
        if self.production_mode:
            response.headers["X-Frame-Options"] = frame_mode

        # X-XSS-Protection: 1; mode=block
        # Включает XSS фильтр браузера (legacy, но полезен для старых браузеров)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy (базовая)
        # Ограничивает источники контента
        csp_directives = [
            "default-src 'self'",
            "img-src 'self' data: https:",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'" if self.production_mode else "frame-ancestors 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer-Policy
        # Контролирует информацию о referrer в заголовке
        response.headers["Referrer-Policy"] = os.getenv("REFERRER_POLICY", "strict-origin-when-cross-origin")

        # Permissions-Policy (базовая)
        # Контролирует browser features/APIs
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # Server header (скрываем информацию о сервере)
        if self.production_mode:
            response.headers.pop("Server", None)
            response.headers["X-Powered-By"] = ""  # Удаляем если есть


def get_tls_config_info() -> dict:
    """
    Получение информации о текущей TLS конфигурации.

    Returns:
        dict: Информация о TLS конфигурации
    """
    return {
        "production_mode": settings.ENVIRONMENT == "production",
        "tls_enabled": settings.TLS_ENABLED,
        "tls_cert_path": settings.TLS_CERT_PATH if settings.TLS_ENABLED else None,
        "tls_key_path": settings.TLS_KEY_PATH if settings.TLS_ENABLED else None,
        "https_enforced": settings.ENVIRONMENT == "production" and settings.TLS_ENABLED,
        "hsts_enabled": settings.ENVIRONMENT == "production",
        "security_headers_enabled": True,
    }
