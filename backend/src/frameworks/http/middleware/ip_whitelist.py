"""
IP Whitelist Middleware for FastAPI.

Enforces network-based access control by restricting API access to whitelisted IP addresses and CIDR ranges.
Provides enterprise-grade security by allowing only trusted networks to access the system.

Architecture:
- IP Validation: Extracts client IP from request (handles X-Forwarded-For for proxies)
- Database Check: Queries IP whitelist entries to verify if client IP is allowed
- Fallback Strategy: Configurable strict mode (deny all vs allow all) when whitelist is empty
- Loopback Handling: Always allows localhost/127.0.0.1 for development (configurable)
- CIDR Support: Supports both single IPs and CIDR ranges (IPv4 and IPv6)

Usage:
    app.add_middleware(IPWhitelistMiddleware)
"""

import logging
from typing import Optional

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.config import settings
from src.database import SessionLocal
from src.services.ip_whitelist_service import ip_whitelist_service


logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP whitelist middleware for network access control.

    Restricts API access to whitelisted IP addresses and CIDR ranges.
    Configurable via environment variables for strict mode and loopback handling.
    """

    def __init__(self, app):
        """
        Initialize IP whitelist middleware.

        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.enabled = settings.IP_WHITELIST_ENABLED
        self.strict_mode = settings.IP_WHITELIST_STRICT_MODE
        self.allow_loopback = settings.IP_WHITELIST_ALLOW_LOOPBACK
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Process request through IP whitelist.

        Returns:
            403 Forbidden if IP not whitelisted and strict mode is enabled
            Otherwise continues to next middleware/handler
        """
        try:
            # Skip IP whitelist check if feature is disabled
            if not self.enabled:
                return await call_next(request)

            # Skip IP whitelist for certain paths
            if self._should_skip_whitelist(request.url.path):
                return await call_next(request)

            # Get client IP address
            client_ip = self._get_client_ip(request)
            if not client_ip:
                self.logger.warning("Could not determine client IP")
                if self.strict_mode:
                    return self._create_forbidden_response("Unable to determine client IP")
                return await call_next(request)

            # Check if IP is whitelisted
            is_allowed = self._check_ip_allowed(client_ip)

            if not is_allowed:
                self.logger.warning(
                    f"IP whitelist blocked request: ip={client_ip}, "
                    f"path={request.url.path}, method={request.method}"
                )
                return self._create_forbidden_response(
                    f"Access denied from IP: {client_ip}"
                )

            # IP is allowed, continue to handler
            return await call_next(request)

        except Exception as e:
            self.logger.error(f"IP whitelist middleware error: {e}")
            # On error, follow strict mode setting
            if self.strict_mode:
                return self._create_forbidden_response("Access control error")
            # Fail open if not in strict mode
            return await call_next(request)

    def _should_skip_whitelist(self, path: str) -> bool:
        """
        Check if path should skip IP whitelist checking.

        Args:
            path: Request path

        Returns:
            bool: True if path should skip whitelist
        """
        # Always allow health check and metrics
        skip_paths = [
            "/health",
            "/metrics",
            "/api/health",
            "/api/auth/login",  # Allow login endpoint
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        return any(path.startswith(p) for p in skip_paths)

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.

        Handles X-Forwarded-For header for requests through proxies/load balancers.

        Args:
            request: FastAPI request

        Returns:
            Client IP address or None
        """
        # Check X-Forwarded-For header (for requests through proxies)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one (original client)
            client_ip = x_forwarded_for.split(",")[0].strip()
            return client_ip

        # Check X-Real-IP header (alternative to X-Forwarded-For)
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()

        # Fall back to direct connection IP
        if request.client and request.client.host:
            return request.client.host

        return None

    def _check_ip_allowed(self, ip: str) -> bool:
        """
        Check if IP address is allowed to access the system.

        Args:
            ip: IP address to check

        Returns:
            bool: True if IP is allowed, False otherwise
        """
        # Always allow loopback addresses if configured
        if self.allow_loopback and self._is_loopback(ip):
            self.logger.debug(f"Allowing loopback IP: {ip}")
            return True

        # Check database whitelist
        try:
            db = SessionLocal()
            is_whitelisted = ip_whitelist_service.is_ip_whitelisted(
                db=db,
                ip=ip,
                check_active_only=True
            )
            db.close()

            if is_whitelisted:
                self.logger.debug(f"IP {ip} found in whitelist")
                return True

            # IP not in whitelist
            self.logger.debug(f"IP {ip} not in whitelist")

            # If strict mode is disabled, allow all IPs
            if not self.strict_mode:
                self.logger.debug(f"Strict mode disabled, allowing IP: {ip}")
                return True

            # Strict mode enabled, deny access
            return False

        except Exception as e:
            self.logger.error(f"Error checking IP whitelist: {e}")
            # On error, follow strict mode setting
            if self.strict_mode:
                return False
            # Fail open if not in strict mode
            return True

    def _is_loopback(self, ip: str) -> bool:
        """
        Check if IP address is a loopback address.

        Args:
            ip: IP address to check

        Returns:
            bool: True if IP is loopback
        """
        loopback_addresses = [
            "127.0.0.1",
            "::1",
            "localhost",
        ]

        # Check exact match
        if ip in loopback_addresses:
            return True

        # Check if starts with 127. (IPv4 loopback range)
        if ip.startswith("127."):
            return True

        # Check if starts with :: (IPv6 loopback range)
        if ip.startswith("::"):
            return True

        return False

    def _create_forbidden_response(self, detail: str) -> JSONResponse:
        """
        Create a 403 Forbidden response.

        Args:
            detail: Error message

        Returns:
            JSONResponse with 403 status
        """
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": detail,
                "error_type": "ip_whitelist_restricted"
            }
        )
