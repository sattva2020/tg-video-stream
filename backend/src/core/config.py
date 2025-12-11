import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Telegram Broadcast API"
    VERSION: str = "0.1.0"
    
    # Stream Controller Configuration
    STREAM_CONTROLLER_TYPE: str = os.getenv("STREAM_CONTROLLER_TYPE", "systemd")
    STREAM_CONTAINER_NAME: str = os.getenv("STREAM_CONTAINER_NAME", "telegram-streamer")
    STREAM_SERVICE_NAME: str = os.getenv("STREAM_SERVICE_NAME", "tg_video_streamer")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/telegram_db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Celery / Notifications Queue
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", f"{os.getenv('REDIS_URL', 'redis://localhost:6379')}/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
    NOTIFICATIONS_QUEUE: str = os.getenv("NOTIFICATIONS_QUEUE", "notifications")
    NOTIFICATIONS_WORKER_CONCURRENCY: int = int(os.getenv("NOTIFICATIONS_WORKER_CONCURRENCY", "5"))
    NOTIFICATIONS_PREFETCH: int = int(os.getenv("NOTIFICATIONS_PREFETCH", "1"))

    # Notification delivery defaults
    NOTIF_RETRY_ATTEMPTS: int = int(os.getenv("NOTIF_RETRY_ATTEMPTS", "3"))
    NOTIF_RETRY_INTERVAL_SEC: int = int(os.getenv("NOTIF_RETRY_INTERVAL_SEC", "30"))
    NOTIF_TIMEOUT_HTTP_SEC: int = int(os.getenv("NOTIF_TIMEOUT_HTTP_SEC", "10"))
    NOTIF_TIMEOUT_SMTP_SEC: int = int(os.getenv("NOTIF_TIMEOUT_SMTP_SEC", "15"))
    NOTIF_FAILOVER_TIMEOUT_SEC: int = int(os.getenv("NOTIF_FAILOVER_TIMEOUT_SEC", "30"))
    NOTIF_TEST_TIMEOUT_SEC: int = int(os.getenv("NOTIF_TEST_TIMEOUT_SEC", "65"))
    NOTIF_STORM_BATCH_SIZE: int = int(os.getenv("NOTIF_STORM_BATCH_SIZE", "10"))
    NOTIF_STORM_WINDOW_SEC: int = int(os.getenv("NOTIF_STORM_WINDOW_SEC", "120"))
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_this_secure_jwt_secret")
    SESSION_ENCRYPTION_KEY: str = os.getenv("SESSION_ENCRYPTION_KEY", "change_this_secure_session_encryption_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Telegram API (for streamer)
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")

    # Telegram Login Widget Authentication
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "")
    TELEGRAM_AUTH_MAX_AGE: int = int(os.getenv("TELEGRAM_AUTH_MAX_AGE", "300"))
    TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR: int = int(os.getenv("TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR", "5"))
    TELEGRAM_AUTH_CAPTCHA_THRESHOLD: int = int(os.getenv("TELEGRAM_AUTH_CAPTCHA_THRESHOLD", "3"))

    # Cloudflare Turnstile CAPTCHA
    TURNSTILE_SITE_KEY: str = os.getenv("TURNSTILE_SITE_KEY", "")
    TURNSTILE_SECRET_KEY: str = os.getenv("TURNSTILE_SECRET_KEY", "")

    # Playlist
    PLAYLIST_PATH: str = os.getenv("PLAYLIST_PATH", "/app/data/playlist.txt")

settings = Settings()
