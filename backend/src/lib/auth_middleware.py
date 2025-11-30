"""
Authentication middleware for FastAPI.

This module provides middleware for JWT token verification, user extraction,
and request context injection for the Telegram broadcast platform.
"""

from typing import Optional, Any

from fastapi import HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..lib.db import get_db_session
from ..models.user import User
from .schemas import CurrentUser
from ..services.auth_service import get_auth_service


class AuthMiddleware:
    """Middleware for handling JWT authentication in requests."""

    def __init__(self) -> None:
        """Initialize the auth middleware."""
        self.auth_service = get_auth_service()

    async def __call__(self, request: Request, call_next) -> Response:
        """
        Process the request through authentication middleware.

        Extracts JWT token from cookies, validates it, and injects user info
        into request state for use by endpoints.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain

        Returns:
            Response: FastAPI response object
        """
        # Extract token from cookies
        token = self.auth_service.get_token_from_cookies(request.cookies)

        if token:
            # Decode and validate token
            payload = self.auth_service.decode_token(token)

            if payload and payload.get("type") == "access":
                # Token is valid, extract user info
                user_id = payload.get("user_id")
                email = payload.get("email")
                role = payload.get("role")

                if user_id and email and role:
                    # Inject user info into request state
                    request.state.user_id = user_id
                    request.state.user_email = email
                    request.state.user_role = role
                    request.state.is_authenticated = True
                else:
                    request.state.is_authenticated = False
            else:
                request.state.is_authenticated = False
        else:
            request.state.is_authenticated = False

        # Continue processing the request
        response = await call_next(request)

        return response


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db_session)) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.

    Loads the full User object from database using the user_id from request state.

    Args:
        request: FastAPI request object
        session: Database session (injected by FastAPI)

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If user is not authenticated or not found
    """
    if not getattr(request.state, 'is_authenticated', False):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    # Load user from database
    from sqlalchemy import select
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )

    # Convert SQLAlchemy User -> Pydantic CurrentUser DTO to avoid exposing ORM objects
    return CurrentUser(
        id=str(user.id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


async def require_auth(request: Request) -> None:
    """
    FastAPI dependency that requires authentication.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If user is not authenticated
    """
    if not getattr(request.state, 'is_authenticated', False):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )


def require_role(required_roles: list[str]):
    """
    Factory function to create role-based authorization dependency.

    Args:
        required_roles: List of role names that are allowed access

    Returns:
        Callable: FastAPI dependency function

    Usage:
        @app.get("/admin-only")
        async def admin_endpoint(request: Request = Depends(require_role(["ADMIN"]))):
            pass
    """
    async def role_checker(request: Request) -> None:
        # First check if authenticated
        await require_auth(request)

        # Check if user has required role
        user_role = getattr(request.state, 'user_role', None)
        if not user_role or user_role not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {', '.join(required_roles)}"
            )

    return role_checker


async def optional_auth(request: Request) -> Optional[dict]:
    """
    Optional authentication dependency.

    Returns user info if authenticated, None if not.

    Args:
        request: FastAPI request object

    Returns:
        Optional[dict]: User info dict if authenticated, None otherwise
    """
    if getattr(request.state, 'is_authenticated', False):
        return {
            "user_id": request.state.user_id,
            "email": request.state.user_email,
            "role": request.state.user_role
        }
    return None


# Global middleware instance
_auth_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware() -> AuthMiddleware:
    """Get the global auth middleware instance."""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware()
    return _auth_middleware