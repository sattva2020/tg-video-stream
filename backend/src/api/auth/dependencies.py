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
from src.models.organization import Organization
from src.models.organization_user import OrganizationUser
from src.services.playback_service import PlaybackService
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


def get_current_organization(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Organization:
    """
    Извлекает текущую организацию пользователя.
    """
    if current_user.organization_id is None:
        logger.warning(f"User {current_user.id} does not have an organization")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any organization",
        )

    organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if organization is None:
        logger.warning(f"Organization not found for ID: {current_user.organization_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found",
        )

    return organization


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


def require_org_admin(
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость: требует роль администратора в организации.
    Проверяет, имеет ли пользователь роль с именем 'admin' или 'owner' в организации.
    """
    if current_user.organization_id != current_organization.id:
        logger.warning(f"User {current_user.id} does not belong to organization {current_organization.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to this organization",
        )

    org_user = db.query(OrganizationUser).filter(
        OrganizationUser.user_id == current_user.id,
        OrganizationUser.organization_id == current_organization.id
    ).first()

    if org_user is None:
        logger.warning(f"User {current_user.id} is not a member of organization {current_organization.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )

    if org_user.role is None:
        logger.warning(f"User {current_user.id} does not have a role in organization {current_organization.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have required privileges in this organization",
        )

    # Проверяем имя роли (admin, owner)
    allowed_role_names = {"admin", "owner"}
    role_name = org_user.role.name.lower() if org_user.role.name else ""
    if role_name not in allowed_role_names:
        logger.warning(f"User {current_user.id} has role '{role_name}' which is not admin in organization {current_organization.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges in this organization",
        )

    return current_user


def require_org_role(
    required_permission: str = None,
    required_role_name: str = None
):
    """
    Зависимость: требует определённой роли или права в организации.

    Args:
        required_permission: Требуемое право (например, 'manage_streams', 'view_analytics')
        required_role_name: Требуемое название роли (например, 'admin', 'editor')

    Можно указать либо required_permission, либо required_role_name, либо оба.
    """
    async def _check_role(
        current_user: User = Depends(get_current_user),
        current_organization: Organization = Depends(get_current_organization),
        db: Session = Depends(get_db)
    ) -> User:
        if current_user.organization_id != current_organization.id:
            logger.warning(f"User {current_user.id} does not belong to organization {current_organization.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to this organization",
            )

        org_user = db.query(OrganizationUser).filter(
            OrganizationUser.user_id == current_user.id,
            OrganizationUser.organization_id == current_organization.id
        ).first()

        if org_user is None:
            logger.warning(f"User {current_user.id} is not a member of organization {current_organization.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this organization",
            )

        if org_user.role is None:
            logger.warning(f"User {current_user.id} does not have a role in organization {current_organization.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have required privileges in this organization",
            )

        # Проверяем название роли, если указано
        if required_role_name is not None:
            role_name = org_user.role.name.lower() if org_user.role.name else ""
            if role_name != required_role_name.lower():
                logger.warning(f"User {current_user.id} has role '{role_name}' but required '{required_role_name}' in organization {current_organization.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have the required role '{required_role_name}' in this organization",
                )

        # Проверяем право, если указано
        if required_permission is not None:
            if not org_user.role.has_permission(required_permission):
                logger.warning(f"User {current_user.id} does not have permission '{required_permission}' in organization {current_organization.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have the required permission '{required_permission}' in this organization",
                )

        return current_user

    return _check_role


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
