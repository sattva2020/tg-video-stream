import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Telegram Broadcast API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
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
    SECRET_KEY: str = os.getenv("SECRET_KEY", JWT_SECRET) # Alias for admin panel
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
    
    # Audio Processing (rust-transcoder)
    RUST_TRANSCODER_URL: str = os.getenv("RUST_TRANSCODER_URL", "http://rust-transcoder:8090")

    # CORS
    ALLOWED_ORIGINS: list[str] = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")]

    # SAML/SSO Configuration
    SAML_ENABLED: bool = os.getenv("SAML_ENABLED", "false").lower() == "true"
    SAML_SP_ENTITY_ID: str = os.getenv("SAML_SP_ENTITY_ID", "https://your-app.com/saml/metadata")
    SAML_SP_ACS_URL: str = os.getenv("SAML_SP_ACS_URL", "https://your-app.com/api/auth/saml/acs")
    SAML_SP_SLO_URL: str = os.getenv("SAML_SP_SLO_URL", "https://your-app.com/api/auth/saml/slo")
    SAML_NAME_ID_FORMAT: str = os.getenv("SAML_NAME_ID_FORMAT", "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified")
    SAML_ASSERTION_ENCRYPTED: bool = os.getenv("SAML_ASSERTION_ENCRYPTED", "false").lower() == "true"
    SAML_SIGN_ASSERTION: bool = os.getenv("SAML_SIGN_ASSERTION", "true").lower() == "true"
    SAML_SIGN_METADATA: bool = os.getenv("SAML_SIGN_METADATA", "false").lower() == "true"

    # IP Whitelist Configuration
    IP_WHITELIST_ENABLED: bool = os.getenv("IP_WHITELIST_ENABLED", "false").lower() == "true"
    IP_WHITELIST_STRICT_MODE: bool = os.getenv("IP_WHITELIST_STRICT_MODE", "false").lower() == "true"
    IP_WHITELIST_ALLOW_LOOPBACK: bool = os.getenv("IP_WHITELIST_ALLOW_LOOPBACK", "true").lower() == "true"

    # Two-Factor Authentication (2FA) Policy Configuration
    TWO_FACTOR_ENFORCEMENT_ENABLED: bool = os.getenv("TWO_FACTOR_ENFORCEMENT_ENABLED", "false").lower() == "true"
    TWO_FACTOR_GRACE_PERIOD_HOURS: int = int(os.getenv("TWO_FACTOR_GRACE_PERIOD_HOURS", "24"))
    TWO_FACTOR_EXEMPT_ALTERNATIVE_AUTH: bool = os.getenv("TWO_FACTOR_EXEMPT_ALTERNATIVE_AUTH", "true").lower() == "true"

    # Security Policy Configuration
    SECURITY_POLICY_DEFAULT_LEVEL: str = os.getenv("SECURITY_POLICY_DEFAULT_LEVEL", "optional")  # optional, mandatory, audit_only
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_UPPERCASE: bool = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
    PASSWORD_REQUIRE_LOWERCASE: bool = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
    PASSWORD_REQUIRE_NUMBER: bool = os.getenv("PASSWORD_REQUIRE_NUMBER", "true").lower() == "true"
    PASSWORD_REQUIRE_SPECIAL: bool = os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower() == "true"
    PASSWORD_MAX_AGE_DAYS: int = int(os.getenv("PASSWORD_MAX_AGE_DAYS", "90"))

    # Session Security
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = int(os.getenv("ACCOUNT_LOCKOUT_DURATION_MINUTES", "30"))

    # Audit & Compliance Logging
    AUDIT_LOG_RETENTION_DAYS: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "365"))
    COMPLIANCE_LOG_ENABLED: bool = os.getenv("COMPLIANCE_LOG_ENABLED", "true").lower() == "true"
    AUDIT_LOG_SENSITIVE_OPERATIONS: bool = os.getenv("AUDIT_LOG_SENSITIVE_OPERATIONS", "true").lower() == "true"

    # Data Encryption at Rest
    DATA_ENCRYPTION_ENABLED: bool = os.getenv("DATA_ENCRYPTION_ENABLED", "false").lower() == "true"
    DATA_ENCRYPTION_KEY: str = os.getenv("DATA_ENCRYPTION_KEY", "")  # 32-byte key for AES-256
    FIELD_ENCRYPTION_ALGORITHM: str = os.getenv("FIELD_ENCRYPTION_ALGORITHM", "AES-GCM")

    # TLS/HTTPS Configuration
    TLS_ENABLED: bool = os.getenv("TLS_ENABLED", "false").lower() == "true"
    TLS_CERT_PATH: str = os.getenv("TLS_CERT_PATH", "/etc/ssl/certs/app.crt")
    TLS_KEY_PATH: str = os.getenv("TLS_KEY_PATH", "/etc/ssl/private/app.key")

settings = Settings()
