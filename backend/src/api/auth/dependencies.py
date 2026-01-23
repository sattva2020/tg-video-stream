"""
Зависимости для аутентификации и авторизации.
"""
import os
import time
import uuid
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from src.models.user import User
from src.models.api_key import APIKey
from src.services.playback_service import PlaybackService
from src.services.api_key_service import APIKeyService
from auth import jwt

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Извлекает текущего пользователя из JWT токена.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = jwt.decode_access_token(token)
    if payload is None:
        logger.warning("Token decoding failed")
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Token payload missing 'sub'")
        raise credentials_exception
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID in token: {user_id}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
    
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость: требует роль администратора или суперадмина.
    """
    allowed_roles = {"admin", "superadmin"}
    user_role = current_user.role.lower() if current_user.role else ""
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_api_key(request: Request, db: Session = Depends(get_db)) -> APIKey:
    """
    Извлекает API ключ из заголовка X-API-Key.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )

    # Extract API key from header
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header is None:
        logger.warning("API key header missing")
        raise credentials_exception

    # Validate the API key using the service
    api_key_service = APIKeyService(db)
    api_key = api_key_service.validate_key(api_key_header)

    if api_key is None:
        logger.warning(f"API key validation failed")
        raise credentials_exception

    return api_key


def require_scope(required_scope: str):
    """
    Зависимость: требует определённый scope у API ключа.
    """
    def _scope_checker(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        if not api_key.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The API key doesn't have the required scope: {required_scope}",
            )
        return api_key
    return _scope_checker


def require_any_scope(*required_scopes: str):
    """
    Зависимость: требует хотя бы один из указанных scopes у API ключа.
    """
    def _scope_checker(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        if not api_key.has_any_scope(list(required_scopes)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The API key doesn't have any of the required scopes: {', '.join(required_scopes)}",
            )
        return api_key
    return _scope_checker


def get_playback_service(db: Session = Depends(get_db)) -> PlaybackService:
    """
    Dependency для PlaybackService.
    """
    return PlaybackService(db_session=db)


# ============================================================================
# Rate Limiting
# ============================================================================

# In-memory rate limiter (fallback когда нет Redis)
_rate_limit_storage: dict = {}
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 5))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # seconds


def _rate_limit_key(ip: str, action: str) -> str:
    return f"{action}:{ip}"


def _check_rate_limit(ip: str, action: str) -> bool:
    """
    Проверяет rate limit по IP для действия.
    Возвращает True если разрешено, False если лимит превышен.
    """
    key = _rate_limit_key(ip, action)
    now = time.time()
    entry = _rate_limit_storage.get(key, [])
    # Фильтруем timestamps в пределах окна
    entry = [t for t in entry if now - t < RATE_LIMIT_WINDOW]
    
    if len(entry) >= RATE_LIMIT_MAX:
        _rate_limit_storage[key] = entry
        return False
    
    entry.append(now)
    _rate_limit_storage[key] = entry
    return True


def make_rate_limit_dep(action: str, times: int = 5, seconds: int = 60):
    """
    Создаёт зависимость для rate limiting.
    Использует Redis если доступен, иначе in-memory fallback.
    """
    if os.getenv('REDIS_URL'):
        from fastapi_limiter.depends import RateLimiter
        return RateLimiter(times=times, seconds=seconds)

    async def _mem_limit(request: Request):
        ip = request.client.host if request.client else 'unknown'
        if not _check_rate_limit(ip, action):
            raise HTTPException(status_code=429, detail='Too many attempts, try again later.')

    return _mem_limit
