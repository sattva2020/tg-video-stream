from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
import sys
import warnings

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

# Create FastAPI application using factory pattern (T048)
from src.frameworks.http.app import create_app

app = create_app()


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
