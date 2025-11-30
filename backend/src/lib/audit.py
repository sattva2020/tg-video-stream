"""
Audit logging decorator for the Telegram broadcast platform.

This module provides decorators for automatically logging operations
to the AuditLog table with request IP, user agent, and other metadata.
"""

import functools
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog


def audit_log(
    action: str,
    resource_type: str,
    resource_id_param: Optional[str] = None
):
    """
    Decorator to automatically log operations to the audit log.

    Args:
        action: The action being performed (CREATE, UPDATE, DELETE, etc.)
        resource_type: The type of resource being acted upon
        resource_id_param: Parameter name containing the resource ID (optional)

    Returns:
        Callable: Decorated function that logs audit events

    Usage:
        @app.post("/videos")
        @audit_log("CREATE", "VIDEO")
        async def create_video(video_data: dict, request: Request, session: AsyncSession):
            # Function implementation
            pass

        @app.put("/videos/{video_id}")
        @audit_log("UPDATE", "VIDEO", "video_id")
        async def update_video(video_id: int, video_data: dict, request: Request, session: AsyncSession):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and session from parameters
            request = None
            session = None

            # Find Request and AsyncSession in args
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, AsyncSession):
                    session = arg

            # Check kwargs if not found in args
            if not request:
                request = kwargs.get('request')
            if not session:
                session = kwargs.get('session')

            # Extract resource ID if specified
            resource_id = None
            if resource_id_param:
                # Check function parameters
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())

                if resource_id_param in param_names:
                    param_index = param_names.index(resource_id_param)
                    if param_index < len(args):
                        resource_id = args[param_index]
                    elif resource_id_param in kwargs:
                        resource_id = kwargs[resource_id_param]

            # Extract user info from request state
            user_id = None
            user_email = None
            user_role = None

            if request and hasattr(request.state, 'user_id'):
                user_id = request.state.user_id
                user_email = getattr(request.state, 'user_email', None)
                user_role = getattr(request.state, 'user_role', None)

            # Extract request metadata
            ip_address = None
            user_agent = None

            if request:
                # Get client IP (handle X-Forwarded-For for proxies)
                ip_address = request.headers.get('X-Forwarded-For', request.client.host)
                if ip_address and ',' in ip_address:
                    # Take first IP if multiple (proxy chain)
                    ip_address = ip_address.split(',')[0].strip()

                user_agent = request.headers.get('User-Agent')

            # Create audit log entry
            audit_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "user_email": user_email,
                    "user_role": user_role,
                    "endpoint": str(request.url) if request else None,
                    "method": request.method if request else None,
                    "function": f"{func.__module__}.{func.__name__}"
                },
                created_at=datetime.now(timezone.utc)
            )

            # Add to session if available
            if session:
                session.add(audit_entry)
                # Note: We don't commit here - let the business logic handle transaction

            # Call the original function
            try:
                result = await func(*args, **kwargs)
                # Success - audit entry will be committed with the transaction
                return result
            except Exception as e:
                # Log the error in metadata if session is available
                if session and audit_entry:
                    audit_entry.metadata = audit_entry.metadata or {}
                    audit_entry.metadata["error"] = str(e)
                    audit_entry.metadata["error_type"] = type(e).__name__
                # Re-raise the exception
                raise

        return wrapper

    return decorator


# Convenience decorators for common operations
def audit_create(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for CREATE operations."""
    return audit_log("CREATE", resource_type, resource_id_param)


def audit_read(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for READ operations."""
    return audit_log("READ", resource_type, resource_id_param)


def audit_update(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for UPDATE operations."""
    return audit_log("UPDATE", resource_type, resource_id_param)


def audit_delete(resource_type: str, resource_id_param: Optional[str] = None):
    """Decorator for DELETE operations."""
    return audit_log("DELETE", resource_type, resource_id_param)


def audit_login():
    """Decorator for LOGIN operations."""
    return audit_log("LOGIN", "USER")


def audit_logout():
    """Decorator for LOGOUT operations."""
    return audit_log("LOGOUT", "USER")


# Utility functions for manual audit logging
async def log_audit_event(
    session: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """
    Manually log an audit event.

    Args:
        session: Database session
        user_id: ID of the user performing the action
        action: The action being performed
        resource_type: Type of resource being acted upon
        resource_id: ID of the specific resource (optional)
        ip_address: Client IP address (optional)
        user_agent: User agent string (optional)
        metadata: Additional metadata (optional)
        request: FastAPI request object to extract metadata from (optional)

    Returns:
        AuditLog: The created audit log entry
    """
    # Extract additional info from request if provided
    if request:
        if not ip_address:
            ip_address = request.headers.get('X-Forwarded-For', request.client.host)
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

    # Create audit log entry
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc)
    )

    # Add to session
    session.add(audit_entry)

    return audit_entry


# Context manager for audit logging (alternative to decorators)
class AuditContext:
    """Context manager for audit logging."""

    def __init__(
        self,
        session: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[Any] = None,
        request: Optional[Request] = None
    ):
        """
        Initialize audit context.

        Args:
            session: Database session
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
        """Enter the audit context."""
        # Extract user info if not provided
        if self.user_id is None and self.request and hasattr(self.request.state, 'user_id'):
            self.user_id = self.request.state.user_id

        # Create audit entry
        self.audit_entry = await log_audit_event(
            session=self.session,
            user_id=self.user_id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            request=self.request
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the audit context."""
        if exc_val and self.audit_entry:
            # Log error information
            self.audit_entry.metadata = self.audit_entry.metadata or {}
            self.audit_entry.metadata["error"] = str(exc_val)
            self.audit_entry.metadata["error_type"] = exc_type.__name__ if exc_type else None

        # Audit entry will be committed/rolled back with the session transaction


# Helper function to get audit trail for a resource
async def get_audit_trail(
    session: AsyncSession,
    resource_type: str,
    resource_id: Any,
    limit: int = 50
) -> list[AuditLog]:
    """
    Get audit trail for a specific resource.

    Args:
        session: Database session
        resource_type: Type of resource
        resource_id: Resource ID
        limit: Maximum number of entries to return

    Returns:
        list[AuditLog]: List of audit log entries
    """
    from sqlalchemy import select, desc

    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())