from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import routers

from api import auth, users
from fastapi_limiter import FastAPILimiter
import aioredis



app = FastAPI(

    title="Telegram Broadcast API",

    description="API for handling user authentication and other features.",

    version="0.1.0",

)



# Add session middleware

# This is required for storing the OAuth state to prevent CSRF attacks

app.add_middleware(

    SessionMiddleware, secret_key=os.getenv("JWT_SECRET", "a_default_secret")

)



@app.get("/")

def read_root():

    return {"message": "Welcome to the Telegram Broadcast API"}



# Include routers

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.on_event("startup")
async def on_startup():
    # Try to initialize Redis-based rate limiter if REDIS_URL is set
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis = await aioredis.from_url(redis_url)
            await FastAPILimiter.init(redis)
        except Exception as e:
            print("Failed to initialize Redis rate limiter:", e)
