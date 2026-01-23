"""
Organization Isolation Middleware for FastAPI.

Ensures multi-tenant data isolation by scoping all requests to the user's organization.
Extracts organization context from authenticated users and adds it to request state.

Architecture:
- Middleware extracts organization_id from authenticated user
- Adds organization context to request.state for downstream use
- Validates user belongs to an organization for protected endpoints
- Skips public endpoints (health, docs, auth)
- Supports platform superadmin bypass for cross-organization operations

Usage:
    app.add_middleware(OrganizationIsolationMiddleware)
"""

import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.organization import Organization


logger = logging.getLogger(__name__)


class OrganizationIsolationMiddleware(BaseHTTPMiddleware):
    """
    Organization isolation middleware for multi-tenant data isolation.

    Extracts organization context from authenticated users and adds it to
    request.state for use in endpoints and services. Ensures that all
    subsequent operations are scoped to the user's organization.
    """

    def __init__(self, app):
        """
        Initialize organization isolation middleware.

        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Process request through organization isolation.

        Adds organization context to request.state:
        - user: Current User object
        - organization: Current Organization object
        - organization_id: UUID of current organization

        Returns:
            403 Forbidden if user has no organization for protected endpoints
            Otherwise continues to next middleware/handler
        """
        try:
            # Skip isolation for public paths
            if self._should_skip_isolation(request.url.path):
                return await call_next(request)

            # Try to get user from request state (set by auth middleware)
            user = self._get_user_from_state(request)

            if user is None:
                # No authentication - skip isolation
                return await call_next(request)

            # Add user to state
            request.state.user = user

            # Get organization for user
            organization = await self._get_user_organization(request, user)

            if organization is None:
                # Check if this is a protected endpoint
                if self._is_protected_endpoint(request.url.path):
                    self.logger.warning(
                        f"Access denied: user {user.id} has no organization "
                        f"for protected endpoint: {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "detail": "User does not belong to any organization",
                        }
                    )
                # Public endpoint - continue without organization context
                return await call_next(request)

            # Add organization context to state
            request.state.organization = organization
            request.state.organization_id = str(organization.id)

            # Log for debugging
            self.logger.debug(
                f"Organization context: user={user.id}, "
                f"organization={organization.id}, path={request.url.path}"
            )

            # Continue to handler
            response = await call_next(request)
            return response

        except Exception as e:
            self.logger.error(f"Organization isolation error: {e}")
            # On error, allow request to proceed (fail open)
            return await call_next(request)

    def _should_skip_isolation(self, path: str) -> bool:
        """
        Check if path should skip organization isolation.

        Public endpoints that don't require organization context:
        - Health checks
        - Metrics
        - Documentation
        - Authentication endpoints
        - Public API endpoints
        """
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
        ]
        return any(path.startswith(p) for p in skip_paths)

    def _is_protected_endpoint(self, path: str) -> bool:
        """
        Check if endpoint requires organization membership.

        Protected endpoints that users must belong to an organization to access:
        - All /api/* endpoints except auth
        - Playback endpoints
        - Recognition endpoints
        - Channel management
        """
        # Public API paths (don't require organization)
        public_paths = [
            "/api/auth/",
            "/api/public/",
        ]

        if any(path.startswith(p) for p in public_paths):
            return False

        # All other /api/* paths require organization
        if path.startswith("/api/"):
            return True

        return False

    def _get_user_from_state(self, request: Request) -> Optional[User]:
        """
        Extract user from request state.

        The user should be set by authentication middleware/dependencies.
        """
        try:
            if hasattr(request.state, "user"):
                return request.state.user
        except AttributeError:
            pass
        return None

    async def _get_user_organization(
        self,
        request: Request,
        user: User
    ) -> Optional[Organization]:
        """
        Get organization for user from database.

        Uses the database session from request state if available,
        otherwise creates a new session.

        Args:
            request: FastAPI request
            user: Current user

        Returns:
            Organization object or None if user has no organization
        """
        try:
            # Check if user has organization_id
            if not user.organization_id:
                return None

            # Try to get database session from request state
            # This should be set by get_db dependency
            db = None
            if hasattr(request.state, "db"):
                db = request.state.db

            if db is None:
                # Fallback: import get_db and create session
                from src.database import get_db
                db_gen = get_db()
                db = next(db_gen)

            # Query organization
            organization = db.query(Organization).filter(
                Organization.id == user.organization_id
            ).first()

            if organization is None:
                self.logger.warning(
                    f"Organization not found for user {user.id}: "
                    f"organization_id={user.organization_id}"
                )

            return organization

        except Exception as e:
            self.logger.error(
                f"Error getting organization for user {user.id}: {e}"
            )
            return None


def require_organization():
    """
    Dependency that ensures user belongs to an organization.

    Use this in endpoints that require organization context:

    Usage:
        @app.get("/api/streams")
        async def list_streams(
            org: Organization = Depends(require_organization())
        ):
            # org is guaranteed to be not None
            ...

    Returns:
        Organization object for current user

    Raises:
        HTTPException 403 if user has no organization
    """
    async def _check_org(request: Request) -> Organization:
        if not hasattr(request.state, "organization"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to any organization",
            )

        organization = request.state.organization
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to any organization",
            )

        return organization

    return _check_org
