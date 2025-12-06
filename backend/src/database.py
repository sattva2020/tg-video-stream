from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os
from dotenv import load_dotenv
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models.
    
    Uses the modern SQLAlchemy 2.0+ DeclarativeBase pattern
    instead of the deprecated declarative_base() function.
    """
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type for PostgreSQL,
    CHAR(36) for others (SQLite, etc.)
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            # Allow either proper UUID values or arbitrary short string IDs
            # Some unit tests use human-friendly channel ids like "channel-a" —
            # don't force a UUID conversion for those values, allow them through
            # as-is ( they'll be stored as CHAR(36) )
            if isinstance(value, uuid.UUID):
                return str(value)
            if isinstance(value, str):
                try:
                    # if it's a valid UUID string, normalise it
                    return str(uuid.UUID(value))
                except ValueError:
                    # not a UUID — store original string as-is
                    return value
            # fallback — convert to str
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            # If stored value looks like a UUID, return a uuid.UUID object,
            # otherwise just return the raw value (keeps legacy string ids working)
            if isinstance(value, uuid.UUID):
                return value
            if isinstance(value, str):
                try:
                    return uuid.UUID(value)
                except ValueError:
                    return value
            return value

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("No DATABASE_URL set for SQLAlchemy")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=20,           # Increased from 10
        max_overflow=30,        # Increased from 20
        pool_pre_ping=True,
        pool_recycle=1800,      # Recycle connections after 30 min (was 1 hour)
        pool_timeout=10,        # Fail fast instead of waiting 30s
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()