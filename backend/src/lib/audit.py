"""
Audit logging decorator for the Telegram broadcast platform.

This module provides decorators for automatically logging operations
to the AdminAuditLog table with request IP, user agent, and other metadata.
Supports both sync and async sessions.
"""

import functools
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from ..models.audit_log import AdminAuditLog


# Type alias for session
SessionType = Union[SyncSession, AsyncSession]


def audit_log(
    action: str,
    resource_type: str,
    resource_id_param: Optional[str] = None
):
    """
    Decorator to automatically log operations to the audit log.
    Supports both sync and async functions.

    Args:
        action: The action being performed (CREATE, UPDATE, DELETE, etc.)
        resource_type: The type of resource being acted upon
        resource_id_param: Parameter name containing the resource ID (optional)

    Returns:
        Callable: Decorated function that logs audit events

    Usage:
        @app.post("/videos")
        @audit_log("create", "video")
        def create_video(video_data: dict, request: Request, session: Session):
            # Function implementation
            pass

        @app.put("/videos/{video_id}")
        @audit_log("update", "video", "video_id")
        def update_video(video_id: int, video_data: dict, request: Request, session: Session):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _audit_wrapper(func, args, kwargs, action, resource_type, resource_id_param, is_async=True)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _sync_audit_wrapper(func, args, kwargs, action, resource_type, resource_id_param)

        # Return appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _extract_request_and_session(args, kwargs, func):
    """Extract Request and Session from function arguments."""
    request = None
    session = None

    # Find Request and Session in args
    for arg in args:
        if isinstance(arg, Request):
            request = arg
        elif isinstance(arg, (SyncSession, AsyncSession)):
            session = arg

    # Check kwargs if not found in args
    if not request:
        request = kwargs.get('request') or kwargs.get('fastapi_request')
    if not session:
        session = kwargs.get('session') or kwargs.get('db')

    return request, session


def _extract_resource_id(args, kwargs, func, resource_id_param):
    """Extract resource ID from function arguments."""
    if not resource_id_param:
        return None

    # Check function parameters
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())

    if resource_id_param in param_names:
        param_index = param_names.index(resource_id_param)
        if param_index < len(args):
            resource_id = args[param_index]
            # Convert UUID to string if needed
            if hasattr(resource_id, '__str__'):
                return str(resource_id)
            return resource_id
        elif resource_id_param in kwargs:
            resource_id = kwargs[resource_id_param]
            if hasattr(resource_id, '__str__'):
                return str(resource_id)
            return resource_id

    return None


def _create_audit_entry(request, action, resource_type, resource_id):
    """Create an AdminAuditLog entry."""
    # Extract user info from request state
    user_id = None
    user_email = None
    user_role = None

    if request and hasattr(request.state, 'user'):
        # For OAuth2PasswordRequestForm style dependencies
        user = getattr(request.state, 'user', None)
        if user:
            user_id = getattr(user, 'id', None)
            user_email = getattr(user, 'email', None)
            user_role = getattr(user, 'role', None)

    # Also check for direct user_id in state
    if request and hasattr(request.state, 'user_id'):
        user_id = request.state.user_id
        user_email = getattr(request.state, 'user_email', None)
        user_role = getattr(request.state, 'user_role', None)

    # Extract request metadata
    ip_address = None
    user_agent = None

    if request:
        # Get client IP (handle X-Forwarded-For for proxies)
        ip_address = request.headers.get('X-Forwarded-For', request.client.host if request.client else None)
        if ip_address and ',' in ip_address:
            # Take first IP if multiple (proxy chain)
            ip_address = ip_address.split(',')[0].strip()

        user_agent = request.headers.get('User-Agent')

    # Convert resource_id to string for storage
    resource_id_str = str(resource_id) if resource_id is not None else None

    # Create audit log entry
    audit_entry = AdminAuditLog(
        user_id=user_id,
        action=action.lower(),
        resource_type=resource_type.lower(),
        resource_id=resource_id_str,
        ip_address=ip_address,
        user_agent=user_agent,
        details=None  # Will be populated with metadata
    )

    return audit_entry, user_id, user_email, user_role


def _audit_wrapper(func, args, kwargs, action, resource_type, resource_id_param, is_async):
    """Internal wrapper for async functions."""
    import asyncio

    async def _wrapper():
        request, session = _extract_request_and_session(args, kwargs, func)
        resource_id = _extract_resource_id(args, kwargs, func, resource_id_param)

        audit_entry, user_id, user_email, user_role = _create_audit_entry(
            request, action, resource_type, resource_id
        )

        # Build details
        details = {
            "user_email": user_email,
            "user_role": user_role,
            "endpoint": str(request.url) if request else None,
            "method": request.method if request else None,
            "function": f"{func.__module__}.{func.__name__}"
        }

        # Convert to JSON string for details field
        import json
        audit_entry.details = json.dumps(details)

        # Add to session if available
        if session:
            session.add(audit_entry)

        # Call the original function
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            # Log the error in details if session is available
            if session and audit_entry:
                details["error"] = str(e)
                details["error_type"] = type(e).__name__
                audit_entry.details = json.dumps(details)
            raise

    return _wrapper()


def _sync_audit_wrapper(func, args, kwargs, action, resource_type, resource_id_param):
    """Internal wrapper for sync functions."""
    request, session = _extract_request_and_session(args, kwargs, func)
    resource_id = _extract_resource_id(args, kwargs, func, resource_id_param)

    audit_entry, user_id, user_email, user_role = _create_audit_entry(
        request, action, resource_type, resource_id
    )

    # Build details
    import json
    details = {
        "user_email": user_email,
        "user_role": user_role,
        "endpoint": str(request.url) if request else None,
        "method": request.method if request else None,
        "function": f"{func.__module__}.{func.__name__}"
    }

    # Convert to JSON string for details field
    audit_entry.details = json.dumps(details)

    # Add to session if available
    if session:
        session.add(audit_entry)

    # Call the original function
    try:
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        # Log the error in details if session is available
        if session and audit_entry:
            details["error"] = str(e)
            details["error_type"] = type(e).__name__
            audit_entry.details = json.dumps(details)
        raise


# Convenience decorators for common operations
def audit_create(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for create operations."""
    return audit_log("create", resource_type, resource_id_param)


def audit_read(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for read operations."""
    return audit_log("read", resource_type, resource_id_param)


def audit_update(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for update operations."""
    return audit_log("update", resource_type, resource_id_param)


def audit_delete(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for delete operations."""
    return audit_log("delete", resource_type, resource_id_param)


def audit_login():
    """Decorator for login operations."""
    return audit_log("login", "user")


def audit_logout():
    """Decorator for logout operations."""
    return audit_log("logout", "user")


def audit_approve(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for approve operations."""
    return audit_log("approve", resource_type, resource_id_param)


def audit_reject(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for reject operations."""
    return audit_log("reject", resource_type, resource_id_param)


def audit_export(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for export operations."""
    return audit_log("export", resource_type, resource_id_param)


# Utility functions for manual audit logging
def log_audit_event(
    session: SessionType,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None
) -> AdminAuditLog:
    """
    Manually log an audit event.

    Args:
        session: Database session (sync or async)
        user_id: ID of the user performing the action
        action: The action being performed
        resource_type: Type of resource being acted upon
        resource_id: ID of the specific resource (optional)
        ip_address: Client IP address (optional)
        user_agent: User agent string (optional)
        metadata: Additional metadata (optional)
        request: FastAPI request object to extract metadata from (optional)

    Returns:
        AdminAuditLog: The created audit log entry
    """
    import json

    # Extract additional info from request if provided
    if request:
        if not ip_address:
            ip_address = request.headers.get('X-Forwarded-For', request.client.host if request.client else None)
            if ip_address and ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

        if not user_agent:
            user_agent = request.headers.get('User-Agent')

        # Add request info to metadata
        if not metadata:
            metadata = {}
        metadata.update({
            "endpoint": str(request.url),
            "method": request.method,
            "user_email": getattr(request.state, 'user_email', None),
            "user_role": getattr(request.state, 'user_role', None)
        })

    # Convert resource_id to string for storage
    resource_id_str = str(resource_id) if resource_id is not None else None

    # Create audit log entry
    audit_entry = AdminAuditLog(
        user_id=user_id,
        action=action.lower(),
        resource_type=resource_type.lower(),
        resource_id=resource_id_str,
        ip_address=ip_address,
        user_agent=user_agent,
        details=json.dumps(metadata) if metadata else None
    )

    # Add to session
    session.add(audit_entry)

    return audit_entry


# Context manager for audit logging (alternative to decorators)
class AuditContext:
    """Context manager for audit logging. Supports sync and async sessions."""

    def __init__(
        self,
        session: SessionType,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[Any] = None,
        request: Optional[Request] = None
    ):
        """
        Initialize audit context.

        Args:
            session: Database session (sync or async)
            action: Audit action
            resource_type: Resource type
            user_id: User ID (optional, extracted from request if not provided)
            resource_id: Resource ID (optional)
            request: FastAPI request (optional)
        """
        self.session = session
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.request = request
        self.user_id = user_id
        self.audit_entry = None

    async def __aenter__(self):
        """Enter the audit context (async)."""
        # Extract user info if not provided
        if self.user_id is None and self.request and hasattr(self.request.state, 'user_id'):
            self.user_id = self.request.state.user_id

        # Create audit entry
        self.audit_entry = log_audit_event(
            session=self.session,
            user_id=self.user_id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            request=self.request
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the audit context (async)."""
        if exc_val and self.audit_entry:
            # Log error information
            import json
            try:
                details = json.loads(self.audit_entry.details) if self.audit_entry.details else {}
            except:
                details = {}
            details["error"] = str(exc_val)
            details["error_type"] = exc_type.__name__ if exc_type else None
            self.audit_entry.details = json.dumps(details)

        # Audit entry will be committed/rolled back with the session transaction

    def __enter__(self):
        """Enter the audit context (sync)."""
        # Extract user info if not provided
        if self.user_id is None and self.request and hasattr(self.request.state, 'user_id'):
            self.user_id = self.request.state.user_id

        # Create audit entry
        self.audit_entry = log_audit_event(
            session=self.session,
            user_id=self.user_id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            request=self.request
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the audit context (sync)."""
        if exc_val and self.audit_entry:
            # Log error information
            import json
            try:
                details = json.loads(self.audit_entry.details) if self.audit_entry.details else {}
            except:
                details = {}
            details["error"] = str(exc_val)
            details["error_type"] = exc_type.__name__ if exc_type else None
            self.audit_entry.details = json.dumps(details)

        # Audit entry will be committed/rolled back with the session transaction


def get_audit_trail(
    session: SessionType,
    resource_type: str,
    resource_id: Any,
    limit: int = 50
) -> list[AdminAuditLog]:
    """
    Get audit trail for a specific resource.

    Args:
        session: Database session (sync or async)
        resource_type: Type of resource
        resource_id: Resource ID
        limit: Maximum number of entries to return

    Returns:
        list[AdminAuditLog]: List of audit log entries
    """
    from sqlalchemy import select, desc

    stmt = (
        select(AdminAuditLog)
        .where(
            AdminAuditLog.resource_type == resource_type.lower(),
            AdminAuditLog.resource_id == str(resource_id)
        )
        .order_by(desc(AdminAuditLog.timestamp))
        .limit(limit)
    )

    if isinstance(session, AsyncSession):
        import asyncio
        result = asyncio.run(session.execute(stmt))
    else:
        result = session.execute(stmt)

    return list(result.scalars().all())