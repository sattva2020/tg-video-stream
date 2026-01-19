"""
FastAPI Dependency Injection Configuration
FRAMEWORKS LAYER - HTTP (T049)

Централизованное место для DI конфигурации:
- Database sessions
- Repository instances  
- Use case instances
- Authentication dependencies

Использование в controllers:
    from src.frameworks.http.dependencies import get_current_user, get_db
    
    @router.get("/me")
    async def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        ...
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database import SessionLocal

# OAuth2 scheme для JWT токенов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения database session.
    
    Yields:
        Session: SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# TODO: Migrate these from src.api.auth.dependencies after Phase 6 (T056-T063)
# For now, re-export from old location for backward compatibility

try:
    from src.api.auth.dependencies import (
        get_current_user,
        require_admin,
        make_rate_limit_dep,
    )
except ImportError:
    # Fallback stubs если старые dependencies не доступны
    async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        """Get current authenticated user (stub)."""
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (dependency not migrated yet)",
        )
    
    async def require_admin(current_user = Depends(get_current_user)):
        """Require admin role (stub)."""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required (dependency not migrated yet)",
        )
    
    def make_rate_limit_dep(*args, **kwargs):
        """Rate limit dependency factory (stub)."""
        async def rate_limit_stub():
            pass
        return rate_limit_stub


# Export all dependencies
__all__ = [
    "get_db",
    "get_current_user",
    "require_admin",
    "make_rate_limit_dep",
    "oauth2_scheme",
]
