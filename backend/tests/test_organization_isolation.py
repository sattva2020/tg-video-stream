"""
Unit tests for organization isolation middleware.
Spec: 022-multi-tenant-architecture-organization-management

Tests cover:
- OrganizationIsolationMiddleware
- require_organization dependency
- Organization context extraction from requests
- Protected endpoint detection
- Public path skipping
- Multi-tenant data isolation enforcement
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from starlette.responses import Response
from sqlalchemy.orm import Session

from src.middleware.organization_isolation import (
    OrganizationIsolationMiddleware,
    require_organization
)
from src.models.user import User, UserRole, UserStatus
from src.models.organization import Organization


# ==================== MIDDLEWARE INITIALIZATION TESTS ====================

def test_middleware_init():
    """Test OrganizationIsolationMiddleware initialization."""
    # Arrange
    mock_app = MagicMock()

    # Act
    middleware = OrganizationIsolationMiddleware(mock_app)

    # Assert
    assert middleware.app == mock_app
    assert middleware.logger is not None


# ==================== PUBLIC PATH SKIPPING TESTS ====================

@pytest.mark.asyncio
async def test_middleware_skips_health_check():
    """Test middleware skips /health endpoint."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/health"

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert - should call next without adding organization context
    call_next.assert_called_once_with(request)
    assert not hasattr(request.state, "organization")


@pytest.mark.asyncio
async def test_middleware_skips_metrics():
    """Test middleware skips /metrics endpoint."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/metrics"

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_skips_docs():
    """Test middleware skips /docs endpoint."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/docs"

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_skips_openapi():
    """Test middleware skips /openapi.json endpoint."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/openapi.json"

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_skips_auth_endpoints():
    """Test middleware skips authentication endpoints."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    auth_paths = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
    ]

    for path in auth_paths:
        request = MagicMock(spec=Request)
        request.url.path = path

        call_next = AsyncMock(return_value=Response())

        # Act
        response = await middleware.dispatch(request, call_next)

        # Assert
        call_next.assert_called_once_with(request)


# ==================== ORGANIZATION CONTEXT EXTRACTION TESTS ====================

@pytest.mark.asyncio
async def test_middleware_adds_organization_context_for_authenticated_user():
    """Test middleware adds organization context for authenticated user with organization."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    org_id = uuid4()
    user_id = uuid4()

    organization = Organization(
        id=org_id,
        name="Test Organization",
        slug="test-org",
        is_active=True
    )

    user = User(
        id=user_id,
        email="user@example.com",
        hashed_password="hash",
        role=UserRole.USER,
        status=UserStatus.APPROVED,
        organization_id=org_id
    )

    request = MagicMock(spec=Request)
    request.url.path = "/api/some-protected-endpoint"
    request.state.user = user

    # Mock database session
    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.return_value = organization
    request.state.db = mock_db

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert
    assert hasattr(request.state, "organization")
    assert request.state.organization == organization
    assert hasattr(request.state, "organization_id")
    assert request.state.organization_id == str(org_id)
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_allows_protected_endpoint_without_organization_for_public_api():
    """Test middleware allows access to public API without organization."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hash",
        role=UserRole.USER,
        status=UserStatus.APPROVED,
        organization_id=None  # No organization
    )

    request = MagicMock(spec=Request)
    request.url.path = "/api/public/endpoint"
    request.state.user = user

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert - should continue without organization context
    call_next.assert_called_once_with(request)
    assert not hasattr(request.state, "organization")


@pytest.mark.asyncio
async def test_middleware_blocks_protected_endpoint_without_organization():
    """Test middleware blocks protected endpoint when user has no organization."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hash",
        role=UserRole.USER,
        status=UserStatus.APPROVED,
        organization_id=None  # No organization
    )

    request = MagicMock(spec=Request)
    request.url.path = "/api/streams"  # Protected endpoint
    request.state.user = user

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert - should return 403
    assert response.status_code == status.HTTP_403_FORBIDDEN
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_continues_without_authentication():
    """Test middleware continues when no user is authenticated."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/api/some-endpoint"
    # No user in request.state

    call_next = AsyncMock(return_value=Response())

    # Act
    response = await middleware.dispatch(request, call_next)

    # Assert - should continue without organization context
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_middleware_handles_exception_gracefully():
    """Test middleware handles exceptions and continues (fail open)."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    # Trigger exception by setting problematic user
    request.state.user = MagicMock()
    request.state.user.organization_id = uuid4()

    call_next = AsyncMock(return_value=Response())

    # Mock database to raise exception
    mock_db = MagicMock(spec=Session)
    mock_db.query.side_effect = Exception("Database error")

    # Simulate get_db from request.state
    with patch('src.middleware.organization_isolation.get_db') as mock_get_db:
        mock_get_db.side_effect = Exception("DB error")

        # Act - should not raise exception, but continue
        response = await middleware.dispatch(request, call_next)

        # Assert - should continue to next handler (fail open)
        call_next.assert_called_once_with(request)


# ==================== PROTECTED ENDPOINT DETECTION TESTS ====================

def test_is_protected_endpoint_with_api_path():
    """Test _is_protected_endpoint detects /api/* paths as protected."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    # Act & Assert
    assert middleware._is_protected_endpoint("/api/streams") is True
    assert middleware._is_protected_endpoint("/api/playlists") is True
    assert middleware._is_protected_endpoint("/api/queues") is True
    assert middleware._is_protected_endpoint("/api/channels") is True


def test_is_protected_endpoint_with_auth_api():
    """Test _is_protected_endpoint allows /api/auth/* paths."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    # Act & Assert
    assert middleware._is_protected_endpoint("/api/auth/login") is False
    assert middleware._is_protected_endpoint("/api/auth/register") is False
    assert middleware._is_protected_endpoint("/api/auth/verify") is False


def test_is_protected_endpoint_with_public_api():
    """Test _is_protected_endpoint allows /api/public/* paths."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    # Act & Assert
    assert middleware._is_protected_endpoint("/api/public/info") is False
    assert middleware._is_protected_endpoint("/api/public/status") is False


def test_is_protected_endpoint_with_non_api_path():
    """Test _is_protected_endpoint returns False for non-API paths."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    # Act & Assert
    assert middleware._is_protected_endpoint("/playback") is False
    assert middleware._is_protected_endpoint("/recognize") is False
    assert middleware._is_protected_endpoint("/static/file.txt") is False


# ==================== REQUIRE ORGANIZATION DEPENDENCY TESTS ====================

@pytest.mark.asyncio
async def test_require_organization_success():
    """Test require_organization dependency returns organization when present."""
    # Arrange
    org_id = uuid4()
    organization = Organization(
        id=org_id,
        name="Test Org",
        slug="test-org"
    )

    request = MagicMock(spec=Request)
    request.state.organization = organization

    dependency = require_organization()

    # Act
    result = await dependency(request)

    # Assert
    assert result == organization


@pytest.mark.asyncio
async def test_require_organization_missing_attribute():
    """Test require_organization raises 403 when organization attribute missing."""
    # Arrange
    request = MagicMock(spec=Request)
    # Don't set organization attribute

    dependency = require_organization()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependency(request)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "does not belong to any organization" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_organization_none_value():
    """Test require_organization raises 403 when organization is None."""
    # Arrange
    request = MagicMock(spec=Request)
    request.state.organization = None

    dependency = require_organization()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await dependency(request)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "does not belong to any organization" in exc_info.value.detail


# ==================== USER EXTRACTION TESTS ====================

def test_get_user_from_state_success():
    """Test _get_user_from_state extracts user successfully."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hash"
    )

    request = MagicMock(spec=Request)
    request.state.user = user

    # Act
    result = middleware._get_user_from_state(request)

    # Assert
    assert result == user


def test_get_user_from_state_no_attribute():
    """Test _get_user_from_state returns None when attribute missing."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    # Don't set user attribute

    # Act
    result = middleware._get_user_from_state(request)

    # Assert
    assert result is None


def test_get_user_from_state_attribute_error():
    """Test _get_user_from_state handles AttributeError gracefully."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    request = MagicMock(spec=Request)
    # Make hasattr return False
    delattr(request, 'state')

    # Act
    result = middleware._get_user_from_state(request)

    # Assert
    assert result is None


# ==================== ORGANIZATION RETRIEVAL TESTS ====================

@pytest.mark.asyncio
async def test_get_user_organization_success():
    """Test _get_user_organization retrieves organization successfully."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    org_id = uuid4()
    user_id = uuid4()

    organization = Organization(
        id=org_id,
        name="Test Org",
        slug="test-org"
    )

    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hash",
        organization_id=org_id
    )

    request = MagicMock(spec=Request)

    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.return_value = organization
    request.state.db = mock_db

    # Act
    result = await middleware._get_user_organization(request, user)

    # Assert
    assert result == organization
    mock_db.query.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_organization_no_organization_id():
    """Test _get_user_organization returns None when user has no organization_id."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        organization_id=None  # No organization
    )

    request = MagicMock(spec=Request)

    # Act
    result = await middleware._get_user_organization(request, user)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_user_organization_not_found():
    """Test _get_user_organization returns None when organization not found in DB."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    org_id = uuid4()
    user_id = uuid4()

    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hash",
        organization_id=org_id
    )

    request = MagicMock(spec=Request)

    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    request.state.db = mock_db

    # Act
    result = await middleware._get_user_organization(request, user)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_user_organization_database_error():
    """Test _get_user_organization handles database errors gracefully."""
    # Arrange
    mock_app = MagicMock()
    middleware = OrganizationIsolationMiddleware(mock_app)

    org_id = uuid4()

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        organization_id=org_id
    )

    request = MagicMock(spec=Request)

    mock_db = MagicMock(spec=Session)
    mock_db.query.side_effect = Exception("Database error")
    request.state.db = mock_db

    # Act
    result = await middleware._get_user_organization(request, user)

    # Assert - should return None on error
    assert result is None
