"""
Database session management for the Telegram broadcast platform.

This module provides SQLAlchemy session management with connection pooling,
transaction helpers, and lifecycle management for the PostgreSQL database.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Define the base class for all models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class DatabaseManager:
    """Manages database connections and sessions with connection pooling."""

    def __init__(self) -> None:
        """Initialize the database manager with connection pooling settings."""
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Convert to async URL if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            database_url,
            # Connection pool settings
            pool_size=10,  # Maximum number of connections in pool
            max_overflow=20,  # Maximum overflow connections
            pool_timeout=30,  # Timeout for getting connection from pool
            pool_recycle=1800,  # Recycle connections after 30 minutes
            pool_pre_ping=True,  # Verify connections before use
            # Statement execution settings
            echo=False,  # Set to True for SQL query logging in development
        )

        # Create async session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects loaded after commit
        )

    async def create_tables(self) -> None:
        """Create all database tables defined in SQLAlchemy models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution, mainly for testing)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.

        Provides automatic session cleanup and error handling.
        Usage:
            async with db_manager.session() as session:
                # Use session for database operations
                pass
        """
        session = self.async_session()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.

        Returns:
            bool: True if database is accessible, False otherwise
        """
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[Any, None]:
    """
    FastAPI dependency for getting database sessions.

    This function is used as a dependency in FastAPI route handlers.
    It provides a database session that is automatically cleaned up.

    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            # Use session for database operations
            pass
    """
    async with get_db_manager().session() as session:
        yield session


# Transaction helper functions
async def run_in_transaction(func, *args, **kwargs):
    """
    Run a function within a database transaction.

    Automatically commits on success, rolls back on exception.

    Args:
        func: The function to run within the transaction
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func

    Raises:
        Exception: Any exception raised by func (transaction is rolled back)
    """
    async with get_db_manager().session() as session:
        try:
            result = await func(session, *args, **kwargs)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def run_in_transaction_with_retry(func, max_retries=3, *args, **kwargs):
    """
    Run a function within a database transaction with retry logic.

    Useful for handling transient database errors.

    Args:
        func: The function to run within the transaction
        max_retries: Maximum number of retry attempts
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func

    Raises:
        Exception: Any exception raised by func after all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await run_in_transaction(func, *args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                # Could add exponential backoff here if needed
                continue
            break

    raise last_exception


# Database lifecycle management for FastAPI
async def init_db() -> None:
    """Initialize the database on application startup."""
    db_manager = get_db_manager()
    await db_manager.create_tables()


async def close_db() -> None:
    """Close database connections on application shutdown."""
    if _db_manager and _db_manager.engine:
        await _db_manager.engine.dispose()