"""
Role-Based Access Control (RBAC) decorator for FastAPI endpoints.

This module provides decorators for enforcing role-based permissions
on API endpoints in the Telegram broadcast platform.
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Union

from fastapi import HTTPException, Request

# Import JWT decode function
from auth.jwt import decode_access_token


class UserRole(str, Enum):
    """User role enumeration for type safety."""
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"
    OPERATOR = "OPERATOR"
    USER = "USER"


def _extract_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header or cookies."""
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # Try cookies
    token = request.cookies.get("access_token")
    if token:
        # Remove "Bearer " prefix if present in cookie
        if token.startswith("Bearer "):
            return token[7:]
        return token
    
    return None


def _get_role_from_token(request: Request) -> Optional[str]:
    """Extract user role from JWT token."""
    token = _extract_token_from_request(request)
    if not token:
        return None
    
    payload = decode_access_token(token)
    if not payload:
        return None
    
    role = payload.get("role")
    if role:
        # Normalize role to uppercase for comparison
        return str(role).upper()
    return None


def require_role(required_roles: Union[str, List[str], List[UserRole]]):
    """
    Decorator to require specific user roles for endpoint access.

    Args:
        required_roles: Single role string, list of role strings, or list of UserRole enums

    Returns:
        Callable: Decorated function that checks role permissions

    Usage:
        @app.get("/admin/users")
        @require_role("ADMIN")
        async def get_users():
            pass

        @app.post("/moderate")
        @require_role(["ADMIN", "MODERATOR"])
        async def moderate_content():
            pass

        @app.get("/operator/status")
        @require_role([UserRole.ADMIN, UserRole.OPERATOR])
        async def get_status():
            pass
    """
    # Normalize required_roles to list of strings
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    elif isinstance(required_roles, UserRole):
        required_roles = [required_roles.value]
    else:
        # Handle list of mixed types
        normalized_roles = []
        for role in required_roles:
            if isinstance(role, UserRole):
                normalized_roles.append(role.value)
            else:
                normalized_roles.append(str(role))
        required_roles = normalized_roles

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request object in arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Also check kwargs
            if not request:
                request = kwargs.get('request')

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found in function arguments"
                )

            # Extract role from JWT token directly (no middleware dependency)
            user_role = _get_role_from_token(request)
            
            if not user_role:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            if user_role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required role: {', '.join(required_roles)}. Your role: {user_role}"
                )

            # Role check passed, call the function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require ADMIN role.

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function requiring ADMIN role
    """
    return require_role(UserRole.ADMIN)(func)


def require_moderator(func: Callable) -> Callable:
    """
    Decorator to require MODERATOR role or higher (ADMIN).

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function requiring MODERATOR or ADMIN role
    """
    return require_role([UserRole.ADMIN, UserRole.MODERATOR])(func)


def require_operator(func: Callable) -> Callable:
    """
    Decorator to require OPERATOR role or higher (MODERATOR, ADMIN).

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function requiring OPERATOR or higher role
    """
    return require_role([UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR])(func)


def has_role(user_role: str, required_roles: Union[str, List[str], List[UserRole]]) -> bool:
    """
    Check if a user role satisfies the required roles.

    This is a utility function for programmatic role checking.

    Args:
        user_role: The user's current role
        required_roles: Required roles to check against

    Returns:
        bool: True if user has required role, False otherwise

    Usage:
        if has_role(request.state.user_role, ["ADMIN", "MODERATOR"]):
            # User has permission
            pass
    """
    # Normalize required_roles to list of strings
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    elif isinstance(required_roles, UserRole):
        required_roles = [required_roles.value]
    else:
        # Handle list of mixed types
        normalized_roles = []
        for role in required_roles:
            if isinstance(role, UserRole):
                normalized_roles.append(role.value)
            else:
                normalized_roles.append(str(role))
        required_roles = normalized_roles

    return user_role in required_roles


def get_role_hierarchy() -> dict[str, int]:
    """
    Get the role hierarchy levels for permission checking.

    Returns:
        dict[str, int]: Mapping of role names to hierarchy levels (higher = more permissions)

    Usage:
        hierarchy = get_role_hierarchy()
        if hierarchy.get(user_role, 0) >= hierarchy.get("MODERATOR", 0):
            # User has MODERATOR level or higher permissions
            pass
    """
    return {
        UserRole.OPERATOR.value: 1,
        UserRole.MODERATOR.value: 2,
        UserRole.ADMIN.value: 3
    }


def has_minimum_role(user_role: str, minimum_role: Union[str, UserRole]) -> bool:
    """
    Check if user has at least the minimum required role in the hierarchy.

    Args:
        user_role: The user's current role
        minimum_role: Minimum required role

    Returns:
        bool: True if user has minimum role or higher, False otherwise

    Usage:
        if has_minimum_role(request.state.user_role, UserRole.MODERATOR):
            # User has MODERATOR permissions or higher
            pass
    """
    hierarchy = get_role_hierarchy()

    min_role_name = minimum_role.value if isinstance(minimum_role, UserRole) else minimum_role
    user_level = hierarchy.get(user_role, 0)
    min_level = hierarchy.get(min_role_name, 0)

    return user_level >= min_level


# Permission constants for common operations
PERMISSIONS = {
    "user_management": [UserRole.ADMIN],
    "content_moderation": [UserRole.ADMIN, UserRole.MODERATOR],
    "broadcast_control": [UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR],
    "analytics_view": [UserRole.ADMIN, UserRole.MODERATOR],
    "system_configuration": [UserRole.ADMIN]
}


def require_permission(permission: str):
    """
    Decorator to require specific permissions based on predefined permission sets.

    Args:
        permission: Permission name from PERMISSIONS dict

    Returns:
        Callable: Decorated function requiring the specified permission

    Raises:
        ValueError: If permission name is not found in PERMISSIONS

    Usage:
        @app.delete("/users/{id}")
        @require_permission("user_management")
        async def delete_user(id: int):
            pass
    """
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    required_roles = PERMISSIONS[permission]
    return require_role(required_roles)