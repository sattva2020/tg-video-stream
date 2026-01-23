"""
Unit tests for multi-tenant quota functionality.
Spec: 022-multi-tenant-architecture-organization-management

Tests cover:
- ResourceQuota model
- QuotaType enum
- QuotaService business logic
- Quota checking and enforcement
- Usage tracking (increment/decrement)
- Quota reset functionality
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.organization_quota import ResourceQuota, QuotaType
from src.models.organization import Organization
from src.services.quota_service import QuotaService


# ==================== RESOURCE QUOTA MODEL TESTS ====================

def test_resource_quota_model_init():
    """Test ResourceQuota model initialization."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=50,
        period="monthly",
        reset_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    assert quota.organization_id == org_id
    assert quota.quota_type == QuotaType.STREAMS.value
    assert quota.limit == 100
    assert quota.current_usage == 50
    assert quota.period == "monthly"
    assert quota.reset_at is not None


def test_resource_quota_model_defaults():
    """Test ResourceQuota model default values."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.USERS.value,
        limit=10
    )
    assert quota.current_usage == 0
    assert quota.period is None
    assert quota.reset_at is None


def test_quota_usage_percentage():
    """Test quota usage percentage calculation."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.API_CALLS.value,
        limit=100,
        current_usage=50
    )
    assert quota.usage_percentage == 50.0


def test_quota_usage_percentage_zero_limit():
    """Test quota usage percentage with zero limit (edge case)."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.API_CALLS.value,
        limit=0,
        current_usage=0
    )
    # Should return 0 instead of division by zero error
    assert quota.usage_percentage == 0


def test_quota_is_exceeded():
    """Test quota exceeded detection."""
    org_id = uuid4()

    # Not exceeded
    quota1 = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=50
    )
    assert quota1.is_exceeded is False

    # Exactly at limit (not exceeded)
    quota2 = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=100
    )
    assert quota2.is_exceeded is True

    # Over limit
    quota3 = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=101
    )
    assert quota3.is_exceeded is True


def test_quota_remaining():
    """Test quota remaining calculation."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=30
    )
    assert quota.remaining == 70


def test_quota_remaining_negative():
    """Test quota remaining when over limit (should return 0)."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=150
    )
    assert quota.remaining == 0


def test_quota_increment_usage():
    """Test incrementing quota usage."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.API_CALLS.value,
        limit=100,
        current_usage=10
    )
    quota.increment_usage(amount=5)
    assert quota.current_usage == 15


def test_quota_decrement_usage():
    """Test decrementing quota usage."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.API_CALLS.value,
        limit=100,
        current_usage=20
    )
    quota.decrement_usage(amount=5)
    assert quota.current_usage == 15


def test_quota_decrement_usage_below_zero():
    """Test that decrementing below zero prevents negative usage."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.API_CALLS.value,
        limit=100,
        current_usage=3
    )
    quota.decrement_usage(amount=5)
    # Should not go below zero
    assert quota.current_usage == 0


def test_quota_reset_usage():
    """Test resetting quota usage to zero."""
    org_id = uuid4()
    quota = ResourceQuota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=75
    )
    quota.reset_usage()
    assert quota.current_usage == 0


# ==================== QUOTA SERVICE TESTS ====================

@pytest.fixture
def quota_service():
    """Fixture for QuotaService instance."""
    # Create a mock DB session
    mock_db = MagicMock(spec=Session)
    return QuotaService(mock_db)


@pytest.fixture
def mock_db_session():
    """Fixture for mock database session."""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def sample_organization():
    """Fixture for sample organization."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
        is_active=True
    )
    return org


@pytest.fixture
def sample_quota():
    """Fixture for sample quota."""
    org_id = uuid4()
    quota = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=50,
        period="monthly"
    )
    return quota


def test_quota_service_init(mock_db_session):
    """Test QuotaService initialization."""
    service = QuotaService(mock_db_session)
    assert service.db == mock_db_session


def test_check_quota_not_exceeded(quota_service, sample_quota):
    """Test checking quota when not exceeded."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota

    # Act
    result = quota_service.check_quota(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result is True


def test_check_quota_exceeded(quota_service):
    """Test checking quota when exceeded."""
    # Arrange
    org_id = uuid4()
    exceeded_quota = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=100  # At limit
    )
    quota_service.db.query.return_value.filter.return_value.first.return_value = exceeded_quota

    # Act
    result = quota_service.check_quota(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result is False


def test_check_quota_not_found(quota_service):
    """Test checking quota when quota doesn't exist (assumes unlimited)."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = None

    # Act
    result = quota_service.check_quota(
        organization_id=uuid4(),
        quota_type=QuotaType.STREAMS
    )

    # Assert - should return True (unlimited)
    assert result is True


def test_get_quota_usage(quota_service, sample_quota):
    """Test getting detailed quota usage information."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota

    # Act
    result = quota_service.get_quota_usage(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result["quota_type"] == QuotaType.STREAMS.value
    assert result["limit"] == 100
    assert result["current_usage"] == 50
    assert result["remaining"] == 50
    assert result["usage_percentage"] == 50.0
    assert result["is_exceeded"] is False


def test_get_quota_usage_not_found(quota_service):
    """Test getting quota usage when quota doesn't exist."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        quota_service.get_quota_usage(
            organization_id=uuid4(),
            quota_type=QuotaType.STREAMS
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_increment_usage_success(quota_service, sample_quota):
    """Test successful usage increment."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota
    initial_usage = sample_quota.current_usage

    # Act
    result = quota_service.increment_usage(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS,
        amount=10
    )

    # Assert
    assert result.current_usage == initial_usage + 10
    assert quota_service.db.commit.called


def test_increment_usage_exceeds_quota(quota_service):
    """Test incrementing usage that would exceed quota."""
    # Arrange
    org_id = uuid4()
    quota = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=95  # Only 5 remaining
    )
    quota_service.db.query.return_value.filter.return_value.first.return_value = quota

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        quota_service.increment_usage(
            organization_id=org_id,
            quota_type=QuotaType.STREAMS,
            amount=10  # Would exceed limit
        )

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Quota exceeded" in exc_info.value.detail


def test_decrement_usage_success(quota_service, sample_quota):
    """Test successful usage decrement."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota
    initial_usage = sample_quota.current_usage

    # Act
    result = quota_service.decrement_usage(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS,
        amount=10
    )

    # Assert
    assert result.current_usage == initial_usage - 10
    assert quota_service.db.commit.called


def test_decrement_usage_below_zero_protected(quota_service):
    """Test that decrementing below zero is prevented."""
    # Arrange
    org_id = uuid4()
    quota = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=3  # Small amount
    )
    quota_service.db.query.return_value.filter.return_value.first.return_value = quota

    # Act
    result = quota_service.decrement_usage(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS,
        amount=10  # Would go below zero
    )

    # Assert - should not go below zero
    assert result.current_usage == 0
    assert quota_service.db.commit.called


def test_decrement_usage_not_found(quota_service):
    """Test decrementing usage when quota doesn't exist."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        quota_service.decrement_usage(
            organization_id=uuid4(),
            quota_type=QuotaType.STREAMS,
            amount=10
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_get_all_quotas(quota_service):
    """Test getting all quotas for an organization."""
    # Arrange
    org_id = uuid4()
    quota1 = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100
    )
    quota2 = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.USERS.value,
        limit=10
    )
    quota_service.db.query.return_value.filter.return_value.all.return_value = [quota1, quota2]

    # Act
    result = quota_service.get_all_quotas(organization_id=org_id)

    # Assert
    assert len(result) == 2
    assert quota1 in result
    assert quota2 in result


def test_can_create_resource_true(quota_service, sample_quota):
    """Test can_create_resource returns True when quota available."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota

    # Act
    result = quota_service.can_create_resource(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result is True


def test_can_create_resource_false(quota_service):
    """Test can_create_resource returns False when quota exceeded."""
    # Arrange
    org_id = uuid4()
    exceeded_quota = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=100
    )
    quota_service.db.query.return_value.filter.return_value.first.return_value = exceeded_quota

    # Act
    result = quota_service.can_create_resource(
        organization_id=org_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result is False


def test_reset_expired_quotas(quota_service):
    """Test resetting expired quotas."""
    # Arrange
    org_id = uuid4()
    past_reset = datetime.now(timezone.utc) - timedelta(days=1)
    quota1 = ResourceQuota(
        id=uuid4(),
        organization_id=org_id,
        quota_type=QuotaType.STREAMS.value,
        limit=100,
        current_usage=75,
        reset_at=past_reset
    )
    quota2 = ResourceQuota(
        id=uuid4(),
        organization_id=uuid4(),
        quota_type=QuotaType.API_CALLS.value,
        limit=1000,
        current_usage=500,
        reset_at=past_reset
    )
    quota_service.db.query.return_value.filter.return_value.all.return_value = [quota1, quota2]

    # Act
    result = quota_service.reset_expired_quotas()

    # Assert
    assert result == 2
    assert quota1.current_usage == 0
    assert quota2.current_usage == 0
    assert quota_service.db.commit.called


# ==================== QUOTA TYPE ENUM TESTS ====================

def test_quota_type_enum_values():
    """Test that QuotaType enum has expected values."""
    assert QuotaType.STREAMS.value == "streams"
    assert QuotaType.STORAGE_BYTES.value == "storage_bytes"
    assert QuotaType.BANDWIDTH_BYTES.value == "bandwidth_bytes"
    assert QuotaType.USERS.value == "users"
    assert QuotaType.API_CALLS.value == "api_calls"
    assert QuotaType.PLAYLISTS.value == "playlists"
    assert QuotaType.SCHEDULED_PLAYLISTS.value == "scheduled_playlists"


# ==================== ERROR HANDLING TESTS ====================

def test_check_quota_database_error(quota_service):
    """Test check_quota handles database errors gracefully."""
    # Arrange
    quota_service.db.query.side_effect = Exception("Database error")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        quota_service.check_quota(
            organization_id=uuid4(),
            quota_type=QuotaType.STREAMS
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_increment_usage_with_default_amount(quota_service, sample_quota):
    """Test increment_usage uses default amount of 1."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota
    initial_usage = sample_quota.current_usage

    # Act - don't specify amount (should default to 1)
    result = quota_service.increment_usage(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result.current_usage == initial_usage + 1


def test_decrement_usage_with_default_amount(quota_service, sample_quota):
    """Test decrement_usage uses default amount of 1."""
    # Arrange
    quota_service.db.query.return_value.filter.return_value.first.return_value = sample_quota
    initial_usage = sample_quota.current_usage

    # Act - don't specify amount (should default to 1)
    result = quota_service.decrement_usage(
        organization_id=sample_quota.organization_id,
        quota_type=QuotaType.STREAMS
    )

    # Assert
    assert result.current_usage == initial_usage - 1
