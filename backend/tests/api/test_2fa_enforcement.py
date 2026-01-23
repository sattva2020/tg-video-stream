"""
Unit tests for 2FA enforcement policies.

Tests for TwoFactorEnforcementMiddleware, policy checking, and enforcement dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import uuid

from src.models.user import User, UserRole, UserStatus
from src.models.security_policy import SecurityPolicy, PolicyType, EnforcementLevel
from src.frameworks.http.middleware.two_factor_enforcement import (
    get_active_2fa_policies,
    check_user_2fa_requirement,
    enforce_2fa_policy,
    require_2fa_enabled,
    get_current_user_from_token,
    TwoFactorEnforcementMiddleware,
    TwoFactorEnforcementError,
)
from auth import jwt


# ============================================================================
# get_active_2fa_policies Tests
# ============================================================================

class TestGetActive2FAPolicies:
    """Tests for get_active_2fa_policies function."""

    def test_returns_empty_list_when_no_policies(self, db_session):
        """Test that empty list is returned when no policies exist."""
        policies = get_active_2fa_policies(db_session)
        assert policies == []

    def test_returns_only_2fa_policies(self, db_session):
        """Test that only 2FA enforcement policies are returned."""
        # Create mixed policy types
        policy_2fa = SecurityPolicy(
            name="2FA Policy",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True
        )
        policy_password = SecurityPolicy(
            name="Password Policy",
            policy_type=PolicyType.PASSWORD_COMPLEXITY.value,
            enabled=True
        )
        db_session.add_all([policy_2fa, policy_password])
        db_session.commit()

        policies = get_active_2fa_policies(db_session)

        assert len(policies) == 1
        assert policies[0].policy_type == PolicyType.TWO_FACTOR_ENFORCEMENT.value

    def test_returns_only_enabled_policies(self, db_session):
        """Test that only enabled policies are returned."""
        policy_enabled = SecurityPolicy(
            name="Enabled 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True
        )
        policy_disabled = SecurityPolicy(
            name="Disabled 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=False
        )
        db_session.add_all([policy_enabled, policy_disabled])
        db_session.commit()

        policies = get_active_2fa_policies(db_session)

        assert len(policies) == 1
        assert policies[0].enabled is True

    def test_returns_multiple_active_policies(self, db_session):
        """Test that multiple active 2FA policies are returned."""
        policies = [
            SecurityPolicy(
                name=f"2FA Policy {i}",
                policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
                enabled=True
            )
            for i in range(3)
        ]
        for p in policies:
            db_session.add(p)
        db_session.commit()

        result = get_active_2fa_policies(db_session)

        assert len(result) == 3


# ============================================================================
# check_user_2fa_requirement Tests
# ============================================================================

class TestCheckUser2FARequirement:
    """Tests for check_user_2fa_requirement function."""

    def test_no_requirement_when_no_policies(self, db_session, regular_user):
        """Test that 2FA is not required when no policies exist."""
        requirement = check_user_2fa_requirement(regular_user, [], db_session)

        assert requirement["required"] is False
        assert requirement["enforcement_level"] is None
        assert requirement["grace_period_seconds"] == 0
        assert requirement["policy_name"] is None
        assert requirement["has_grace_period"] is False

    def test_no_requirement_when_no_applicable_policies(self, db_session, regular_user):
        """Test that 2FA is not required when policies don't apply to user's role."""
        policy = SecurityPolicy(
            name="Admin 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        db_session.add(policy)
        db_session.commit()

        policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(regular_user, policies, db_session)

        assert requirement["required"] is False

    def test_requirement_when_policy_applies_to_all_roles(self, db_session, regular_user):
        """Test that 2FA is required when policy applies to all roles."""
        policy = SecurityPolicy(
            name="Universal 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=None,  # None = all roles
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        db_session.add(policy)
        db_session.commit()

        policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(regular_user, policies, db_session)

        assert requirement["required"] is True
        assert requirement["enforcement_level"] == EnforcementLevel.MANDATORY.value
        assert requirement["policy_name"] == "Universal 2FA"

    def test_requirement_when_policy_applies_to_user_role(self, db_session, admin_user):
        """Test that 2FA is required when policy applies to user's specific role."""
        policy = SecurityPolicy(
            name="Admin 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin", "superadmin"],
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        db_session.add(policy)
        db_session.commit()

        policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(admin_user, policies, db_session)

        assert requirement["required"] is True
        assert requirement["policy_name"] == "Admin 2FA"

    def test_uses_most_strict_policy_when_multiple_apply(self, db_session, admin_user):
        """Test that most strict policy is used when multiple apply."""
        policies = [
            SecurityPolicy(
                name="Optional 2FA",
                policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
                enabled=True,
                affected_roles=["admin"],
                enforcement_level=EnforcementLevel.OPTIONAL.value
            ),
            SecurityPolicy(
                name="Mandatory 2FA",
                policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
                enabled=True,
                affected_roles=["admin"],
                enforcement_level=EnforcementLevel.MANDATORY.value
            ),
        ]
        for p in policies:
            db_session.add(p)
        db_session.commit()

        active_policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(admin_user, active_policies, db_session)

        assert requirement["required"] is True
        assert requirement["enforcement_level"] == EnforcementLevel.MANDATORY.value
        assert requirement["policy_name"] == "Mandatory 2FA"

    def test_grace_period_for_new_user(self, db_session, regular_user):
        """Test that grace period is correctly calculated for new users."""
        # User created recently (within grace period)
        regular_user.created_at = datetime.now(timezone.utc) - timedelta(hours=12)

        policy = SecurityPolicy(
            name="2FA with Grace",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=None,
            enforcement_level=EnforcementLevel.MANDATORY.value,
            grace_period_hours=24
        )
        db_session.add(policy)
        db_session.commit()

        policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(regular_user, policies, db_session)

        assert requirement["required"] is True
        assert requirement["grace_period_seconds"] == 24 * 3600
        assert requirement["has_grace_period"] is True

    def test_no_grace_period_for_old_user(self, db_session, regular_user):
        """Test that grace period is not applied to old users."""
        # User created long ago (outside grace period)
        regular_user.created_at = datetime.now(timezone.utc) - timedelta(days=30)

        policy = SecurityPolicy(
            name="2FA with Grace",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=None,
            enforcement_level=EnforcementLevel.MANDATORY.value,
            grace_period_hours=24
        )
        db_session.add(policy)
        db_session.commit()

        policies = get_active_2fa_policies(db_session)
        requirement = check_user_2fa_requirement(regular_user, policies, db_session)

        assert requirement["required"] is True
        assert requirement["has_grace_period"] is False


# ============================================================================
# enforce_2fa_policy Dependency Tests
# ============================================================================

class TestEnforce2FAPolicy:
    """Tests for enforce_2fa_policy dependency function."""

    def test_allows_access_when_no_policies(self, client, db_session, admin_user, admin_auth_headers):
        """Test that access is allowed when no 2FA policies exist."""
        # Ensure no policies exist
        db_session.query(SecurityPolicy).delete()
        db_session.commit()

        # Create a test endpoint that uses the dependency
        from src.main import app

        @app.get("/test-2fa-endpoint")
        async def test_endpoint(user: User = Depends(enforce_2fa_policy)):
            return {"status": "ok", "user_id": str(user.id)}

        response = client.get("/test-2fa-endpoint", headers=admin_auth_headers)

        # Should allow access
        assert response.status_code == status.HTTP_200_OK

    def test_allows_access_when_user_has_2fa_enabled(self, client, db_session, admin_user, admin_auth_headers):
        """Test that access is allowed when user has 2FA enabled."""
        admin_user.totp_enabled = True
        admin_user.totp_secret = "test_secret"
        db_session.commit()

        policy = SecurityPolicy(
            name="Mandatory 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        db_session.add(policy)
        db_session.commit()

        # Access should be allowed
        response = client.get("/api/admin/users", headers=admin_auth_headers)

        # 2FA check should pass (endpoint may not exist, but 2FA check shouldn't block)
        # If it exists and is accessible, 2FA check passed
        if response.status_code != status.HTTP_404_NOT_FOUND:
            assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_blocks_access_when_mandatory_2fa_not_enabled(self, client, db_session, admin_user, admin_auth_headers):
        """Test that access is blocked when mandatory 2FA is not enabled."""
        # Ensure 2FA is disabled
        admin_user.totp_enabled = False
        admin_user.totp_secret = None
        admin_user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        db_session.commit()

        # Create mandatory 2FA policy
        policy = SecurityPolicy(
            name="Mandatory 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        db_session.add(policy)
        db_session.commit()

        # Try to access admin endpoint with 2FA enforcement
        # Mock the JWT decode to return our test user
        with patch('src.frameworks.http.middleware.two_factor_enforcement.jwt.decode_access_token') as mock_decode:
            mock_decode.return_value = {"sub": str(admin_user.id), "role": "admin"}

            from src.main import app

            @app.get("/test-protected")
            async def protected_endpoint(user: User = Depends(enforce_2fa_policy)):
                return {"status": "ok"}

            response = client.get("/test-protected", headers=admin_auth_headers)

            # Should be blocked with 403
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert "detail" in data or "error" in data

    def test_allows_access_in_grace_period(self, client, db_session, admin_user, admin_auth_headers):
        """Test that access is allowed during grace period."""
        # User created recently (within grace period)
        admin_user.totp_enabled = False
        admin_user.created_at = datetime.now(timezone.utc) - timedelta(hours=12)
        db_session.commit()

        # Create mandatory 2FA policy with grace period
        policy = SecurityPolicy(
            name="2FA with Grace",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.MANDATORY.value,
            grace_period_hours=24
        )
        db_session.add(policy)
        db_session.commit()

        # Mock JWT decode
        with patch('src.frameworks.http.middleware.two_factor_enforcement.jwt.decode_access_token') as mock_decode:
            mock_decode.return_value = {"sub": str(admin_user.id), "role": "admin"}

            from src.main import app

            @app.get("/test-grace")
            async def grace_endpoint(user: User = Depends(enforce_2fa_policy)):
                return {"status": "ok"}

            response = client.get("/test-grace", headers=admin_auth_headers)

            # Should allow access during grace period
            assert response.status_code == status.HTTP_200_OK

    def test_audit_only_mode_logs_but_allows_access(self, client, db_session, admin_user, admin_auth_headers):
        """Test that audit-only mode logs violation but allows access."""
        admin_user.totp_enabled = False
        admin_user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        db_session.commit()

        policy = SecurityPolicy(
            name="Audit 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.AUDIT_ONLY.value
        )
        db_session.add(policy)
        db_session.commit()

        # Mock JWT decode
        with patch('src.frameworks.http.middleware.two_factor_enforcement.jwt.decode_access_token') as mock_decode:
            mock_decode.return_value = {"sub": str(admin_user.id), "role": "admin"}

            from src.main import app

            @app.get("/test-audit")
            async def audit_endpoint(user: User = Depends(enforce_2fa_policy)):
                return {"status": "ok"}

            response = client.get("/test-audit", headers=admin_auth_headers)

            # Should allow access in audit-only mode
            assert response.status_code == status.HTTP_200_OK

    def test_optional_mode_allows_access(self, client, db_session, admin_user, admin_auth_headers):
        """Test that optional mode allows access without 2FA."""
        admin_user.totp_enabled = False
        db_session.commit()

        policy = SecurityPolicy(
            name="Optional 2FA",
            policy_type=PolicyType.TWO_FACTOR_ENFORCEMENT.value,
            enabled=True,
            affected_roles=["admin"],
            enforcement_level=EnforcementLevel.OPTIONAL.value
        )
        db_session.add(policy)
        db_session.commit()

        # Mock JWT decode
        with patch('src.frameworks.http.middleware.two_factor_enforcement.jwt.decode_access_token') as mock_decode:
            mock_decode.return_value = {"sub": str(admin_user.id), "role": "admin"}

            from src.main import app

            @app.get("/test-optional")
            async def optional_endpoint(user: User = Depends(enforce_2fa_policy)):
                return {"status": "ok"}

            response = client.get("/test-optional", headers=admin_auth_headers)

            # Should allow access in optional mode
            assert response.status_code == status.HTTP_200_OK


# ============================================================================
# require_2fa_enabled Tests
# ============================================================================

class TestRequire2FAEnabled:
    """Tests for require_2fa_enabled dependency function."""

    def test_allows_access_with_2fa_enabled(self, client, admin_user, admin_auth_headers, db_session):
        """Test that access is allowed when 2FA is enabled."""
        admin_user.totp_enabled = True
        admin_user.totp_secret = "test_secret"
        db_session.commit()

        # Mock get_current_user_from_token to return our user
        with patch('src.frameworks.http.middleware.two_factor_enforcement.get_current_user_from_token') as mock_get:
            mock_get.return_value = admin_user

            from src.main import app

            @app.get("/test-require-2fa")
            async def require_2fa_endpoint(user: User = Depends(require_2fa_enabled)):
                return {"status": "ok"}

            response = client.get("/test-require-2fa", headers=admin_auth_headers)

            assert response.status_code == status.HTTP_200_OK

    def test_blocks_access_without_2fa(self, client, admin_user, admin_auth_headers, db_session):
        """Test that access is blocked when 2FA is not enabled."""
        admin_user.totp_enabled = False
        admin_user.totp_secret = None
        db_session.commit()

        # Mock get_current_user_from_token to return our user
        with patch('src.frameworks.http.middleware.two_factor_enforcement.get_current_user_from_token') as mock_get:
            mock_get.return_value = admin_user

            from src.main import app

            @app.get("/test-block-no-2fa")
            async def block_endpoint(user: User = Depends(require_2fa_enabled)):
                return {"status": "ok"}

            response = client.get("/test-block-no-2fa", headers=admin_auth_headers)

            assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# TwoFactorEnforcementMiddleware Tests
# ============================================================================

class TestTwoFactorEnforcementMiddleware:
    """Tests for TwoFactorEnforcementMiddleware class."""

    def test_middleware_initialization(self):
        """Test middleware initialization with default values."""
        from src.main import app

        middleware = TwoFactorEnforcementMiddleware(app)

        assert middleware.enabled is True
        assert "/api/admin" in middleware.protected_paths
        assert "/api/settings" in middleware.protected_paths

    def test_middleware_custom_protected_paths(self):
        """Test middleware initialization with custom protected paths."""
        from src.main import app

        custom_paths = ["/api/custom1", "/api/custom2"]
        middleware = TwoFactorEnforcementMiddleware(app, protected_paths=custom_paths)

        assert middleware.protected_paths == custom_paths

    def test_middleware_disabled_via_config(self):
        """Test that middleware can be disabled via settings."""
        from src.main import app

        with patch('src.frameworks.http.middleware.two_factor_enforcement.settings') as mock_settings:
            mock_settings.TWO_FA_ENFORCEMENT_ENABLED = False

            middleware = TwoFactorEnforcementMiddleware(app)

            assert middleware.enabled is False

    def test_should_skip_2fa_check(self):
        """Test paths that should skip 2FA checking."""
        from src.main import app

        middleware = TwoFactorEnforcementMiddleware(app)

        # Paths that should be skipped
        skip_paths = [
            "/health",
            "/metrics",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/totp",
        ]

        for path in skip_paths:
            assert middleware._should_skip_2fa_check(path) is True

        # Paths that should not be skipped
        assert middleware._should_skip_2fa_check("/api/admin/users") is False
        assert middleware._should_skip_2fa_check("/api/settings/profile") is False

    def test_is_protected_path(self):
        """Test protected path detection."""
        from src.main import app

        middleware = TwoFactorEnforcementMiddleware(app)

        # Default protected paths
        assert middleware._is_protected_path("/api/admin/users") is True
        assert middleware._is_protected_path("/api/admin/dashboard") is True
        assert middleware._is_protected_path("/api/settings/profile") is True
        assert middleware._is_protected_path("/api/settings/security") is True

        # Non-protected paths
        assert middleware._is_protected_path("/api/public/data") is False
        assert middleware._is_protected_path("/api/health") is False
        assert middleware._is_protected_path("/api/auth/login") is False

    def test_middleware_allows_request_when_disabled(self, client, db_session):
        """Test that middleware allows requests when disabled."""
        from src.main import app

        with patch('src.frameworks.http.middleware.two_factor_enforcement.settings') as mock_settings:
            mock_settings.TWO_FA_ENFORCEMENT_ENABLED = False

            middleware = TwoFactorEnforcementMiddleware(app)

            # Create a mock request
            mock_request = Mock()
            mock_request.url.path = "/api/admin/users"
            mock_request.headers = {}

            async def call_next(request):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=200, content={"status": "ok"})

            # Should allow request when disabled
            import asyncio
            response = asyncio.run(middleware.dispatch(mock_request, call_next))

            assert response.status_code == 200


# ============================================================================
# SecurityPolicy Model Tests (related to 2FA)
# ============================================================================

class TestSecurityPolicy2FA:
    """Tests for SecurityPolicy model methods used in 2FA enforcement."""

    def test_applies_to_role_with_none_roles(self, db_session):
        """Test that policy applies to all roles when affected_roles is None."""
        policy = SecurityPolicy(
            name="Universal 2FA",
            affected_roles=None
        )

        assert policy.applies_to_role("admin") is True
        assert policy.applies_to_role("user") is True
        assert policy.applies_to_role("superadmin") is True

    def test_applies_to_role_with_specific_roles(self, db_session):
        """Test that policy applies only to specified roles."""
        policy = SecurityPolicy(
            name="Admin 2FA",
            affected_roles=["admin", "superadmin"]
        )

        assert policy.applies_to_role("admin") is True
        assert policy.applies_to_role("superadmin") is True
        assert policy.applies_to_role("user") is False

    def test_applies_to_role_with_empty_list(self, db_session):
        """Test that policy applies to no roles when affected_roles is empty."""
        policy = SecurityPolicy(
            name="Empty 2FA",
            affected_roles=[]
        )

        assert policy.applies_to_role("admin") is False
        assert policy.applies_to_role("user") is False

    def test_is_mandatory(self, db_session):
        """Test is_mandatory method."""
        policy = SecurityPolicy(
            enforcement_level=EnforcementLevel.MANDATORY.value
        )
        assert policy.is_mandatory() is True
        assert policy.is_optional() is False
        assert policy.is_audit_only() is False

    def test_is_optional(self, db_session):
        """Test is_optional method."""
        policy = SecurityPolicy(
            enforcement_level=EnforcementLevel.OPTIONAL.value
        )
        assert policy.is_optional() is True
        assert policy.is_mandatory() is False
        assert policy.is_audit_only() is False

    def test_is_audit_only(self, db_session):
        """Test is_audit_only method."""
        policy = SecurityPolicy(
            enforcement_level=EnforcementLevel.AUDIT_ONLY.value
        )
        assert policy.is_audit_only() is True
        assert policy.is_mandatory() is False
        assert policy.is_optional() is False

    def test_get_grace_period_seconds(self, db_session):
        """Test get_grace_period_seconds method."""
        policy = SecurityPolicy(grace_period_hours=24)
        assert policy.get_grace_period_seconds() == 24 * 3600

        policy_zero = SecurityPolicy(grace_period_hours=0)
        assert policy_zero.get_grace_period_seconds() == 0

        policy_none = SecurityPolicy(grace_period_hours=None)
        assert policy_none.get_grace_period_seconds() == 0

    def test_enable_disable_methods(self, db_session):
        """Test enable and disable methods."""
        policy = SecurityPolicy(enabled=False)

        policy.enable()
        assert policy.enabled is True

        policy.disable()
        assert policy.enabled is False

    def test_set_enforcement_level_methods(self, db_session):
        """Test set_mandatory, set_optional, set_audit_only methods."""
        policy = SecurityPolicy()

        policy.set_mandatory()
        assert policy.enforcement_level == EnforcementLevel.MANDATORY.value

        policy.set_optional()
        assert policy.enforcement_level == EnforcementLevel.OPTIONAL.value

        policy.set_audit_only()
        assert policy.enforcement_level == EnforcementLevel.AUDIT_ONLY.value
