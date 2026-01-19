"""
HTTP Controllers - FastAPI route handlers

Мигрированные контроллеры из src/api/ согласно Clean Architecture (Phase 5):
- auth_controller: Authentication endpoints
- health_controller: Health checks and probes
- metrics_controller: Prometheus metrics
- system_controller: System monitoring
- stream_controller: Stream management endpoints
"""

from .auth_controller import router as auth_router
from .health_controller import router as health_router
from .metrics_controller import router as metrics_router
from .stream_controller import router as stream_router
from .system_controller import router as system_router

__all__ = [
    "auth_router",
    "health_router", 
    "metrics_router",
    "stream_router",
    "system_router",
]
