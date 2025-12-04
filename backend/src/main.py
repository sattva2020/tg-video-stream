from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
import sys
import warnings
from contextlib import asynccontextmanager

# Add current directory (src) to sys.path to allow absolute imports from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FastAPI 0.115+ помечает on_event как deprecated — подавляем предупреждение, чтобы pytest не падал.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="typing_extensions",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*on_event is deprecated.*",
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Initialize Sentry for error tracking (before importing other modules)
try:
    from src.instrumentation.sentry import init_sentry
    init_sentry()
except ImportError:
    pass  # Sentry SDK not installed, continue without it

# Import routers (loaded after .env so environment variables are available to modules)
from api.auth import router as auth_router  # noqa: E402
from api import users, playlist, admin, telegram_auth, channels, files, websocket, schedule  # noqa: E402
from src.api.routes import playback as playback_routes  # noqa: E402
from api.health import router as health_router  # noqa: E402
from api.system import router as system_router  # noqa: E402
from api.telegram_login import router as telegram_login_router  # noqa: E402
from api.queue import router as queue_router  # noqa: E402
from api.metrics import router as metrics_router  # noqa: E402
from database import engine, Base


@asynccontextmanager
async def app_lifespan(fastapi_app: FastAPI):
    """FastAPI lifespan hook вместо устаревших on_event."""
    try:
        from src.admin import setup_admin
        await setup_admin(fastapi_app, engine)
    except Exception as e:  # pragma: no cover - не критично для тестов
        print(f"Failed to setup admin panel: {e}")
    yield


app = FastAPI(

    title="Telegram Broadcast API",

    description="API for handling user authentication and other features.",

    version="0.1.0",
    lifespan=app_lifespan,

)



# Add session middleware

# This is required for storing the OAuth state to prevent CSRF attacks

from fastapi.middleware.cors import CORSMiddleware

# Разрешённые origins для CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://flowbooster.xyz",
    "http://flowbooster.xyz:80",
    "https://flowbooster.xyz",
    "http://sattva-streamer.top",
    "https://sattva-streamer.top",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-New-Token"],  # Для sliding session
)

# Session middleware с настройками для proxy
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET", "a_default_secret"),
    same_site="lax",  # Позволяет cookies при редиректах
    https_only=False,  # Для dev, в prod поставить True
)



@app.get("/")

def read_root():

    return {"message": "Welcome to the Telegram Broadcast API"}



# Include routers

app.include_router(health_router, tags=["Health"])  # Health endpoints без prefix
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(playlist.router, prefix="/api/playlist", tags=["Playlist"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(telegram_auth.router, prefix="/api/auth/telegram", tags=["Telegram Auth"])
app.include_router(telegram_login_router, prefix="/api/auth/telegram-login", tags=["Telegram Login"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(schedule.router, prefix="/api", tags=["Schedule"])
app.include_router(system_router, prefix="/api/system", tags=["System Monitoring"])
app.include_router(queue_router, prefix="/api/v1", tags=["Queue"])
app.include_router(metrics_router, tags=["Metrics"])  # /metrics и /api/v1/metrics/*
app.include_router(playback_routes.router)


# Setup Prometheus middleware
from src.middleware.prometheus import PrometheusMiddleware
app.add_middleware(PrometheusMiddleware)

# Setup sliding session middleware (auto-refresh JWT tokens)
from src.middleware.sliding_session import SlidingSessionMiddleware
app.add_middleware(SlidingSessionMiddleware)
print("✓ Sliding session middleware initialized")

# Setup rate limiter middleware
from src.middleware.rate_limiter import RateLimiterMiddleware
try:
    import redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    app.add_middleware(RateLimiterMiddleware, redis_client=redis_client)
    print(f"✓ Rate limiter middleware initialized (Redis: {redis_url})")
except Exception as e:
    print(f"⚠ Rate limiter middleware disabled: {e}")


# @app.on_event("startup")
# async def on_startup_redis():
#     # Create tables
#     Base.metadata.create_all(bind=engine)

#     # Try to initialize Redis-based rate limiter if REDIS_URL is set
#     redis_url = os.getenv("REDIS_URL")
#     if redis_url:
#         try:
#             # Lazy-import redis/fastrate dependencies so app can still run when
#             # Redis or fastapi-limiter is not available in developer environments.
#             import redis.asyncio as redis  # type: ignore
#             from fastapi_limiter import FastAPILimiter  # type: ignore

#             redis_connection = await redis.from_url(redis_url)
#             await FastAPILimiter.init(redis_connection)
#         except Exception as e:
#             # Fail gracefully — we still want the app to boot for local dev so tests
#             # can run even without a Redis-based limiter.
#             print("Failed to initialize Redis rate limiter:", e)
