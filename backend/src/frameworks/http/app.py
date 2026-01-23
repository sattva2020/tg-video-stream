"""
FastAPI Application Factory
FRAMEWORKS LAYER - HTTP (T048)

Фабрика для создания FastAPI приложения с полной конфигурацией:
- Routers
- Middleware
- Lifespan hooks
- CORS
- Error handlers

Использование:
    from src.frameworks.http.app import create_app
    app = create_app()
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from src.core.config import settings
from database import engine


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI) -> AsyncGenerator:
    """FastAPI lifespan hook вместо устаревших on_event."""
    # Initialize Redis-based rate limiter if REDIS_URL is set
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            from fastapi_limiter import FastAPILimiter
            
            redis_connection = await aioredis.from_url(
                redis_url, 
                encoding="utf-8", 
                decode_responses=True
            )
            await FastAPILimiter.init(redis_connection)
            print(f"FastAPILimiter initialized with Redis: {redis_url}")
        except Exception as e:
            print(f"Failed to initialize Redis rate limiter: {e}")
    
    # Setup admin panel
    try:
        from src.frameworks.admin import setup_admin
        await setup_admin(fastapi_app, engine)
    except Exception as e:  # pragma: no cover
        print(f"Failed to setup admin panel: {e}")
    
    yield


def create_app() -> FastAPI:
    """
    Создать и сконфигурировать FastAPI приложение.
    
    Returns:
        FastAPI: Полностью сконфигурированное приложение
    """
    app = FastAPI(
        title="Telegram Broadcast API",
        description="API for handling user authentication and other features.",
        version="0.1.0",
        lifespan=app_lifespan,
    )
    
    # =============================================================================
    # Middleware
    # =============================================================================
    
    # Session middleware (для OAuth state и Admin Panel)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="admin_session",
        max_age=3600 * 24,
        same_site="lax",
        https_only=settings.ENVIRONMENT == "production"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-New-Token"],  # Для sliding session
    )
    
    # Session middleware с настройками для proxy (дубликат? TODO: проверить нужность)
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("JWT_SECRET", "a_default_secret"),
        same_site="lax",
        https_only=False,  # Для dev, в prod поставить True
    )
    
    # Prometheus middleware
    from src.frameworks.http.middleware.prometheus import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
    
    # Sliding session middleware (auto-refresh JWT)
    from src.frameworks.http.middleware.sliding_session import SlidingSessionMiddleware
    app.add_middleware(SlidingSessionMiddleware)
    print("[OK] Sliding session middleware initialized")
    
    # Rate limiter middleware
    from src.frameworks.http.middleware.rate_limiter import RateLimiterMiddleware
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url)
        app.add_middleware(RateLimiterMiddleware, redis_client=redis_client)
        print(f"[OK] Rate limiter middleware initialized (Redis: {redis_url})")
    except Exception as e:
        print(f"[WARN] Rate limiter middleware disabled: {e}")
    
    # Базовые метрики FastAPI/Starlette
    Instrumentator(
        excluded_handlers={"/metrics", "/health", "/api/health", "/healthz"}
    ).instrument(app)
    
    # =============================================================================
    # Routers - Migrated to frameworks/http/controllers/
    # =============================================================================
    
    from src.frameworks.http.controllers import (
        auth_router,
        health_router,
        metrics_router,
        system_router,
    )
    
    # TODO: Migrate these to frameworks/http/controllers/ (остальные T045)
    from api import (
        users, 
        playlist, 
        admin, 
        telegram_auth, 
        channels, 
        files, 
        websocket, 
        schedule
    )
    from src.api import media, media_gdrive, ai_settings
    from src.api.routes import playback as playback_routes
    from src.api.routes import (
        notifications_channels,
        notifications_templates,
        notifications_recipients,
        notifications_rules,
        notifications_events,
        notifications_logs
    )
    from src.api.routes import stream_quality as stream_quality_routes
    from src.api.routes import cdn as cdn_routes
    from src.api.routes import playlists as user_playlists_router
    from api.telegram_login import router as telegram_login_router
    from api.queue import router as queue_router
    from src.api.analytics import router as analytics_router, internal_router as analytics_internal_router
    from src.api.internal import router as internal_router
    from src.api.audio import router as audio_router
    from src.api.incidents import router as incidents_router, solutions_router
    from src.api.settings import router as settings_router
    
    # Root endpoint
    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Telegram Broadcast API"}
    
    # Include migrated routers
    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(system_router, prefix="/api/system", tags=["System Monitoring"])
    app.include_router(metrics_router, tags=["Metrics"])
    
    # Include non-migrated routers (TODO: migrate in future)
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(playlist.router, prefix="/api/playlist", tags=["Playlist"])
    app.include_router(user_playlists_router.router, prefix="/api/playlists", tags=["User Playlists"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    app.include_router(ai_settings.router, prefix="/api/admin", tags=["AI Settings"])
    app.include_router(stream_quality_routes.router, prefix="/api/admin/stream-quality", tags=["Stream Quality"])
    app.include_router(cdn_routes.router)
    app.include_router(telegram_auth.router, prefix="/api/auth/telegram", tags=["Telegram Auth"])
    app.include_router(telegram_login_router, prefix="/api/auth/telegram-login", tags=["Telegram Login"])
    app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
    app.include_router(files.router, prefix="/api/files", tags=["Files"])
    app.include_router(media.router, prefix="/api", tags=["Media"])
    app.include_router(media_gdrive.router, prefix="/api", tags=["Media"])
    app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])
    app.include_router(schedule.router, prefix="/api", tags=["Schedule"])
    app.include_router(queue_router, prefix="/api/v1", tags=["Queue"])
    app.include_router(playback_routes.router)
    app.include_router(notifications_channels.router)
    app.include_router(notifications_templates.router)
    app.include_router(notifications_recipients.router)
    app.include_router(notifications_rules.router)
    app.include_router(notifications_events.router)
    app.include_router(notifications_logs.router)
    app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
    app.include_router(analytics_internal_router, prefix="/api", tags=["Internal"])
    app.include_router(internal_router, prefix="/api", tags=["Internal Streamer"])
    app.include_router(audio_router, prefix="/api/v1", tags=["Audio Processing"])
    app.include_router(incidents_router, prefix="/api", tags=["Incidents"])
    app.include_router(solutions_router, prefix="/api", tags=["Solutions"])
    app.include_router(settings_router, prefix="/api/admin", tags=["Settings"])
    
    return app
