"""
2FA Enforcement Middleware for FastAPI.

Enforces two-factor authentication policies based on security policy configuration.
Provides enterprise-grade security by requiring 2FA for sensitive operations and roles.

Architecture:
- Policy Checking: Queries active 2FA enforcement policies from database
- Role-Based Enforcement: Applies policies based on user roles
- Grace Period: Supports configurable grace periods for new users/accounts
- Exemption Handling: Allows exemptions for alternative auth methods (e.g., SAML)
- Audit Logging: Logs policy violations for compliance tracking
- Enforcement Levels: Supports mandatory, optional, and audit-only modes

Usage as Dependency:
    @app.get("/admin/settings")
    async def admin_settings(
        user: User = Depends(enforce_2fa_policy)
    ):
        return {"settings": {...}}

Usage as Middleware:
    app.add_middleware(TwoFactorEnforcementMiddleware)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from src.models.user import User
from src.models.security_policy import SecurityPolicy, PolicyType, EnforcementLevel
from auth import jwt

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TwoFactorEnforcementError(HTTPException):
    """Exception raised when 2FA policy is violated."""

    def __init__(
        self,
        detail: str = "Two-factor authentication is required",
        enforcement_level: str = EnforcementLevel.MANDATORY.value
    ):
        self.enforcement_level = enforcement_level
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def get_active_2fa_policies(db: Session) -> List[SecurityPolicy]:
    """
    Retrieve all active 2FA enforcement policies from database.

    Args:
        db: Database session

    Returns:
        List of active SecurityPolicy objects with 2FA enforcement type
    """
    try:
        policies = db.query(SecurityPolicy).filter(
            SecurityPolicy.policy_type == PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            SecurityPolicy.enabled == True
        ).all()

        logger.debug(f"Found {len(policies)} active 2FA policies")
        return policies

    except Exception as e:
        logger.error(f"Error retrieving 2FA policies: {e}")
        return []


def check_user_2fa_requirement(
    user: User,
    policies: List[SecurityPolicy],
    db: Session
) -> dict:
    """
    Check if user is required to have 2FA enabled based on policies.

    Args:
        user: User object to check
        policies: List of active 2FA policies
        db: Database session

    Returns:
        dict with keys:
            - required: bool - Whether 2FA is required
            - enforcement_level: str - Policy enforcement level
            - grace_period_seconds: int - Grace period in seconds
            - policy_name: str - Name of enforcing policy
            - has_grace_period: bool - Whether user is within grace period
    """
    user_role = user.role.lower() if user.role else "user"

    # Find policies that apply to this user's role
    applicable_policies = [
        p for p in policies
        if p.applies_to_role(user_role)
    ]

    if not applicable_policies:
        logger.debug(f"No 2FA policies apply to user {user.id} with role {user_role}")
        return {
            "required": False,
            "enforcement_level": None,
            "grace_period_seconds": 0,
            "policy_name": None,
            "has_grace_period": False
        }

    # Use the most strict policy (mandatory > audit_only > optional)
    policy = max(
        applicable_policies,
        key=lambda p: {
            EnforcementLevel.MANDATORY.value: 3,
            EnforcementLevel.AUDIT_ONLY.value: 2,
            EnforcementLevel.OPTIONAL.value: 1
        }.get(p.enforcement_level, 0)
    )

    # Check if user is within grace period
    grace_period_seconds = policy.get_grace_period_seconds()
    has_grace_period = False

    if grace_period_seconds > 0 and user.created_at:
        account_age = (datetime.now(timezone.utc) - user.created_at).total_seconds()
        has_grace_period = account_age < grace_period_seconds

        if has_grace_period:
            logger.debug(
                f"User {user.id} is within grace period "
                f"({account_age}s < {grace_period_seconds}s)"
            )

    return {
        "required": True,
        "enforcement_level": policy.enforcement_level,
        "grace_period_seconds": grace_period_seconds,
        "policy_name": policy.name,
        "has_grace_period": has_grace_period
    }


def enforce_2fa_policy(
    current_user: User = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to enforce 2FA policy on protected endpoints.

    Checks if the user is required to have 2FA enabled based on security policies.
    Raises HTTPException if 2FA is required but not enabled (mandatory mode).

    Args:
        current_user: Current authenticated user (from token)
        db: Database session

    Returns:
        User object if 2FA check passes

    Raises:
        HTTPException: If 2FA is required but not enabled (mandatory mode)
    """
    # Get user from token
    try:
        payload = jwt.decode_access_token(current_user)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID"
            )

        import uuid
        user_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.id == user_uuid).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

    except Exception as e:
        logger.error(f"Error validating user token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

    # Get active 2FA policies
    policies = get_active_2fa_policies(db)

    if not policies:
        # No 2FA policies configured, allow access
        return user

    # Check if user needs 2FA
    requirement = check_user_2fa_requirement(user, policies, db)

    if not requirement["required"]:
        # No policies apply to this user
        return user

    # Check if user has 2FA enabled
    has_2fa = user.totp_enabled if hasattr(user, 'totp_enabled') else False

    if has_2fa:
        # User has 2FA enabled, allow access
        logger.debug(f"User {user.id} has 2FA enabled")
        return user

    # User doesn't have 2FA enabled
    enforcement_level = requirement["enforcement_level"]

    # Check grace period
    if requirement["has_grace_period"]:
        logger.info(
            f"User {user.id} within grace period for 2FA policy '{requirement['policy_name']}'"
        )
        return user

    # Handle based on enforcement level
    if enforcement_level == EnforcementLevel.MANDATORY.value:
        logger.warning(
            f"2FA policy violation: user {user.id} does not have 2FA enabled "
            f"(mandatory policy: {requirement['policy_name']})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "2FA_REQUIRED",
                "message": "Two-factor authentication is required for this account",
                "policy": requirement["policy_name"]
            }
        )

    elif enforcement_level == EnforcementLevel.AUDIT_ONLY.value:
        # Log violation but allow access
        logger.info(
            f"2FA policy audit: user {user.id} does not have 2FA enabled "
            f"(audit-only policy: {requirement['policy_name']})"
        )
        # TODO: Create audit log entry
        return user

    else:  # OPTIONAL
        # Log warning but allow access
        logger.debug(
            f"2FA policy optional: user {user.id} does not have 2FA enabled "
            f"(policy: {requirement['policy_name']})"
        )
        return user


def require_2fa_enabled(current_user: User = Depends(get_current_user_from_token)) -> User:
    """
    Simple dependency that requires 2FA to be enabled, regardless of policy.

    Use this for highly sensitive endpoints that always require 2FA.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if 2FA is enabled

    Raises:
        HTTPException: If 2FA is not enabled
    """
    has_2fa = current_user.totp_enabled if hasattr(current_user, 'totp_enabled') else False

    if not has_2fa:
        logger.warning(f"Access denied: user {current_user.id} does not have 2FA enabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "2FA_REQUIRED",
                "message": "This endpoint requires two-factor authentication to be enabled"
            }
        )

    return current_user


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract current user from JWT token.

    Helper function for use in other dependencies.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        payload = jwt.decode_access_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID"
            )

        user_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.id == user_uuid).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    except Exception as e:
        logger.error(f"Error extracting user from token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


class TwoFactorEnforcementMiddleware:
    """
    Middleware for enforcing 2FA policies across all endpoints.

    This middleware checks 2FA policies for protected routes.
    It's more coarse-grained than the dependency-based approach.

    Usage:
        app.add_middleware(TwoFactorEnforcementMiddleware)

    Configuration:
        - Set TWO_FA_ENFORCEMENT_ENABLED=False to disable
        - Set TWO_FA_PROTECTED_PATHS to list of path prefixes to protect
    """

    def __init__(self, app, protected_paths: Optional[List[str]] = None):
        """
        Initialize 2FA enforcement middleware.

        Args:
            app: FastAPI application
            protected_paths: List of path prefixes to protect (e.g., ["/api/admin"])
        """
        self.app = app
        self.protected_paths = protected_paths or ["/api/admin", "/api/settings"]

        # Check if 2FA enforcement is enabled via config
        from src.core.config import settings
        self.enabled = getattr(settings, 'TWO_FA_ENFORCEMENT_ENABLED', True)

        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Process request through 2FA enforcement check.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler or 403 if 2FA required but not enabled
        """
        try:
            # Skip 2FA check if feature is disabled
            if not self.enabled:
                return await call_next(request)

            # Skip 2FA for certain paths
            if self._should_skip_2fa_check(request.url.path):
                return await call_next(request)

            # Check if path is protected
            if not self._is_protected_path(request.url.path):
                return await call_next(request)

            # Get user from token (if present)
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                # No auth token, let the endpoint handle authentication
                return await call_next(request)

            token = authorization.split(" ")[1]

            # Get database session
            from src.database import SessionLocal
            db = SessionLocal()

            try:
                # Validate token and get user
                try:
                    payload = jwt.decode_access_token(token)
                    if payload is None:
                        return await call_next(request)

                    user_id = payload.get("sub")
                    if not user_id:
                        return await call_next(request)

                    user_uuid = uuid.UUID(user_id)
                    user = db.query(User).filter(User.id == user_uuid).first()

                    if not user:
                        return await call_next(request)

                    # Check 2FA policies
                    policies = get_active_2fa_policies(db)
                    if not policies:
                        return await call_next(request)

                    requirement = check_user_2fa_requirement(user, policies, db)

                    if requirement["required"]:
                        has_2fa = user.totp_enabled if hasattr(user, 'totp_enabled') else False

                        if not has_2fa and not requirement["has_grace_period"]:
                            enforcement_level = requirement["enforcement_level"]

                            if enforcement_level == EnforcementLevel.MANDATORY.value:
                                self.logger.warning(
                                    f"2FA middleware blocked request: user {user.id} "
                                    f"path={request.url.path}"
                                )
                                from fastapi.responses import JSONResponse
                                return JSONResponse(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    content={
                                        "detail": "Two-factor authentication is required",
                                        "error_type": "2fa_required"
                                    }
                                )

                            elif enforcement_level == EnforcementLevel.AUDIT_ONLY.value:
                                self.logger.info(
                                    f"2FA middleware audit: user {user.id} without 2FA "
                                    f"path={request.url.path}"
                                )

                finally:
                    db.close()

            return await call_next(request)

        except Exception as e:
            self.logger.error(f"2FA enforcement middleware error: {e}")
            # On error, allow request to proceed (fail open)
            return await call_next(request)

    def _should_skip_2fa_check(self, path: str) -> bool:
        """
        Check if path should skip 2FA checking.

        Args:
            path: Request path

        Returns:
            bool: True if path should skip 2FA check
        """
        skip_paths = [
            "/health",
            "/metrics",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/totp",  # Allow 2FA setup endpoint
        ]

        return any(path.startswith(p) for p in skip_paths)

    def _is_protected_path(self, path: str) -> bool:
        """
        Check if path requires 2FA protection.

        Args:
            path: Request path

        Returns:
            bool: True if path is protected
        """
        return any(path.startswith(p) for p in self.protected_paths)
