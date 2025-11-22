from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
import sys

# Add current directory (src) to sys.path to allow absolute imports from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import routers (loaded after .env so environment variables are available to modules)
from api import auth, users, playlist  # noqa: E402
from database import engine, Base



app = FastAPI(

    title="Telegram Broadcast API",

    description="API for handling user authentication and other features.",

    version="0.1.0",

)



# Add session middleware

# This is required for storing the OAuth state to prevent CSRF attacks

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("JWT_SECRET", "a_default_secret")
)



@app.get("/")

def read_root():

    return {"message": "Welcome to the Telegram Broadcast API"}



# Include routers

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(playlist.router, prefix="/api/playlist", tags=["Playlist"])


@app.on_event("startup")
async def on_startup():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Try to initialize Redis-based rate limiter if REDIS_URL is set
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            # Lazy-import redis/fastrate dependencies so app can still run when
            # Redis or fastapi-limiter is not available in developer environments.
            import redis.asyncio as redis  # type: ignore
            from fastapi_limiter import FastAPILimiter  # type: ignore

            redis_connection = await redis.from_url(redis_url)
            await FastAPILimiter.init(redis_connection)
        except Exception as e:
            # Fail gracefully — we still want the app to boot for local dev so tests
            # can run even without a Redis-based limiter.
            print("Failed to initialize Redis rate limiter:", e)
