"""
Unit tests for multi-tenant organization functionality.
Spec: 022-multi-tenant-architecture-organization-management

Tests cover:
- Organization model
- OrganizationUser and OrganizationRole models
- OrganizationService business logic
- Organization CRUD operations
- Member management
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.organization import Organization
from src.models.organization_user import OrganizationUser, OrganizationRole, OrganizationUserStatus
from src.models.subscription import Subscription, PlanType, SubscriptionStatus
from src.models.user import User, UserRole, UserStatus
from src.services.organization_service import OrganizationService


# ==================== ORGANIZATION MODEL TESTS ====================

def test_organization_model_init():
    """Test Organization model initialization."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        logo_url="https://example.com/logo.png",
        primary_color="#FF0000",
        secondary_color="#00FF00",
        custom_domain="test.example.com",
        is_active=True
    )
    assert org.name == "Test Organization"
    assert org.slug == "test-org"
    assert org.logo_url == "https://example.com/logo.png"
    assert org.primary_color == "#FF0000"
    assert org.secondary_color == "#00FF00"
    assert org.custom_domain == "test.example.com"
    assert org.is_active is True


def test_organization_model_defaults():
    """Test Organization model default values."""
    org = Organization(name="Default Org")
    assert org.name == "Default Org"
    assert org.slug is None
    assert org.logo_url is None
    assert org.primary_color is None
    assert org.secondary_color is None
    assert org.custom_domain is None
    assert org.is_active is True


def test_organization_model_repr():
    """Test Organization model __repr__ method."""
    org = Organization(
        id=uuid4(),
        name="Test Org",
        slug="test-org"
    )
    repr_str = repr(org)
    assert "Test Org" in repr_str
    assert "test-org" in repr_str


# ==================== ORGANIZATION ROLE MODEL TESTS ====================

def test_organization_role_model_init():
    """Test OrganizationRole model initialization."""
    org_id = uuid4()
    role = OrganizationRole(
        organization_id=org_id,
        name="Admin",
        description="Administrator role",
        permissions={"manage_organization": True, "manage_members": True},
        is_system_role=True
    )
    assert role.organization_id == org_id
    assert role.name == "Admin"
    assert role.description == "Administrator role"
    assert role.permissions == {"manage_organization": True, "manage_members": True}
    assert role.is_system_role is True


def test_organization_role_model_defaults():
    """Test OrganizationRole model default values."""
    org_id = uuid4()
    role = OrganizationRole(
        organization_id=org_id,
        name="Member"
    )
    assert role.description is None
    assert role.permissions == {}
    assert role.is_system_role is False


# ==================== ORGANIZATION USER MODEL TESTS ====================

def test_organization_user_model_init():
    """Test OrganizationUser model initialization."""
    org_id = uuid4()
    user_id = uuid4()
    role_id = uuid4()
    invited_by = uuid4()

    org_user = OrganizationUser(
        organization_id=org_id,
        user_id=user_id,
        role_id=role_id,
        status=OrganizationUserStatus.ACTIVE.value,
        invited_by=invited_by,
        joined_at=datetime.now(timezone.utc)
    )
    assert org_user.organization_id == org_id
    assert org_user.user_id == user_id
    assert org_user.role_id == role_id
    assert org_user.status == OrganizationUserStatus.ACTIVE.value
    assert org_user.invited_by == invited_by
    assert org_user.joined_at is not None


def test_organization_user_model_defaults():
    """Test OrganizationUser model default values."""
    org_id = uuid4()
    user_id = uuid4()

    org_user = OrganizationUser(
        organization_id=org_id,
        user_id=user_id
    )
    assert org_user.role_id is None
    assert org_user.status == "pending"  # Default from model
    assert org_user.invited_by is None
    assert org_user.joined_at is None


def test_organization_user_helper_methods():
    """Test OrganizationUser helper methods."""
    org_id = uuid4()
    user_id = uuid4()

    org_user = OrganizationUser(
        organization_id=org_id,
        user_id=user_id,
        status=OrganizationUserStatus.PENDING.value
    )

    # Test is_pending
    assert org_user.is_pending is True
    assert org_user.is_active is False

    # Test activate
    org_user.activate()
    assert org_user.status == OrganizationUserStatus.ACTIVE.value
    assert org_user.is_active is True
    assert org_user.is_pending is False
    assert org_user.joined_at is not None

    # Test deactivate
    org_user.deactivate()
    assert org_user.status == OrganizationUserStatus.INACTIVE.value

    # Test suspend
    org_user.suspend()
    assert org_user.status == OrganizationUserStatus.SUSPENDED.value

    # Test has_permission (no role assigned)
    assert org_user.has_permission("any_permission") is False


# ==================== ORGANIZATION SERVICE TESTS ====================

@pytest.fixture
def organization_service():
    """Fixture for OrganizationService instance."""
    return OrganizationService()


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
        name="Sample Organization",
        slug="sample-org",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    return org


@pytest.fixture
def sample_user():
    """Fixture for sample user."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hash",
        role=UserRole.USER,
        status=UserStatus.APPROVED
    )
    return user


def test_create_organization_success(organization_service, mock_db_session):
    """Test successful organization creation."""
    # Act
    result = organization_service.create_organization(
        db=mock_db_session,
        name="Test Organization",
        slug="test-org",
        logo_url="https://example.com/logo.png",
        primary_color="#FF0000",
        secondary_color="#00FF00",
        custom_domain="test.example.com"
    )

    # Assert
    assert mock_db_session.add.called
    assert mock_db_session.flush.called
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called


def test_create_organization_auto_slug(organization_service, mock_db_session):
    """Test organization creation with auto-generated slug."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act
    result = organization_service.create_organization(
        db=mock_db_session,
        name="My Test Organization!"
    )

    # Assert - slug should be auto-generated from name
    assert result is not None


def test_create_organization_duplicate_slug(organization_service, mock_db_session, sample_organization):
    """Test organization creation fails with duplicate slug."""
    # Arrange - existing organization with same slug
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.create_organization(
            db=mock_db_session,
            name="Test Organization",
            slug="sample-org"  # Duplicate slug
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in exc_info.value.detail


def test_create_organization_invalid_primary_color(organization_service, mock_db_session):
    """Test organization creation fails with invalid primary color."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.create_organization(
            db=mock_db_session,
            name="Test Organization",
            primary_color="INVALID_COLOR"  # Invalid hex format
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid primary_color format" in exc_info.value.detail


def test_create_organization_invalid_secondary_color(organization_service, mock_db_session):
    """Test organization creation fails with invalid secondary color."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.create_organization(
            db=mock_db_session,
            name="Test Organization",
            secondary_color="NOT_HEX"  # Invalid hex format
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid secondary_color format" in exc_info.value.detail


def test_get_organization_success(organization_service, mock_db_session, sample_organization):
    """Test successful organization retrieval by ID."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act
    result = organization_service.get_organization(
        db=mock_db_session,
        organization_id=sample_organization.id
    )

    # Assert
    assert result == sample_organization
    mock_db_session.query.assert_called_once()


def test_get_organization_not_found(organization_service, mock_db_session):
    """Test organization retrieval fails when not found."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.get_organization(
            db=mock_db_session,
            organization_id=uuid4()
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


def test_get_organization_by_slug_success(organization_service, mock_db_session, sample_organization):
    """Test successful organization retrieval by slug."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act
    result = organization_service.get_organization_by_slug(
        db=mock_db_session,
        slug="sample-org"
    )

    # Assert
    assert result == sample_organization


def test_update_organization_success(organization_service, mock_db_session, sample_organization):
    """Test successful organization update."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization  # For domain check

    # Act
    result = organization_service.update_organization(
        db=mock_db_session,
        organization_id=sample_organization.id,
        name="Updated Organization",
        primary_color="#0000FF"
    )

    # Assert
    assert result == sample_organization
    assert mock_db_session.commit.called


def test_deactivate_organization_success(organization_service, mock_db_session, sample_organization):
    """Test successful organization deactivation (soft delete)."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act
    result = organization_service.deactivate_organization(
        db=mock_db_session,
        organization_id=sample_organization.id
    )

    # Assert
    assert result.is_active is False
    assert mock_db_session.commit.called


def test_delete_organization_permanent(organization_service, mock_db_session, sample_organization):
    """Test permanent organization deletion."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act
    organization_service.delete_organization(
        db=mock_db_session,
        organization_id=sample_organization.id
    )

    # Assert
    mock_db_session.delete.assert_called_once_with(sample_organization)
    assert mock_db_session.commit.called


def test_add_member_success(organization_service, mock_db_session, sample_organization, sample_user):
    """Test successful member addition to organization."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        sample_organization,  # Organization query
        sample_user,  # User query
        None  # Check if already member
    ]

    # Act
    result = organization_service.add_member(
        db=mock_db_session,
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        invited_by=sample_user.id
    )

    # Assert
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


def test_add_member_already_member(organization_service, mock_db_session, sample_organization, sample_user):
    """Test adding member who is already a member fails."""
    # Arrange
    existing_membership = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        sample_organization,  # Organization query
        sample_user,  # User query
        existing_membership  # Already a member
    ]

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.add_member(
            db=mock_db_session,
            organization_id=sample_organization.id,
            user_id=sample_user.id
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already a member" in exc_info.value.detail


def test_remove_member_success(organization_service, mock_db_session, sample_organization, sample_user):
    """Test successful member removal from organization."""
    # Arrange
    membership = OrganizationUser(
        id=uuid4(),
        organization_id=sample_organization.id,
        user_id=sample_user.id
    )
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        sample_organization,  # Organization query
        membership  # Membership query
    ]

    # Act
    organization_service.remove_member(
        db=mock_db_session,
        organization_id=sample_organization.id,
        user_id=sample_user.id
    )

    # Assert
    mock_db_session.delete.assert_called_once_with(membership)
    assert mock_db_session.commit.called


def test_remove_member_not_found(organization_service, mock_db_session, sample_organization, sample_user):
    """Test removing member who is not in organization fails."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        sample_organization,  # Organization query
        None  # Not a member
    ]

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        organization_service.remove_member(
            db=mock_db_session,
            organization_id=sample_organization.id,
            user_id=sample_user.id
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_is_slug_available_true(organization_service, mock_db_session):
    """Test slug availability check returns True for available slug."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act
    result = organization_service.is_slug_available(
        db=mock_db_session,
        slug="new-org"
    )

    # Assert
    assert result is True


def test_is_slug_available_false(organization_service, mock_db_session, sample_organization):
    """Test slug availability check returns False for taken slug."""
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_organization

    # Act
    result = organization_service.is_slug_available(
        db=mock_db_session,
        slug="sample-org"
    )

    # Assert
    assert result is False


def test_generate_slug_valid(organization_service):
    """Test slug generation from valid organization name."""
    # Act
    slug = organization_service._generate_slug("My Test Organization!")

    # Assert
    assert slug == "my-test-organization"


def test_generate_slug_special_chars(organization_service):
    """Test slug generation removes special characters."""
    # Act
    slug = organization_service._generate_slug("Organization @#$% Name!")

    # Assert
    assert slug == "organization-name"


def test_generate_slug_long_name(organization_service):
    """Test slug generation truncates long names."""
    # Arrange - create a very long name
    long_name = "a" * 200

    # Act
    slug = organization_service._generate_slug(long_name)

    # Assert - should be truncated to 100 chars
    assert len(slug) <= 100


def test_is_valid_hex_color_valid(organization_service):
    """Test valid hex color validation."""
    # Act & Assert
    assert organization_service._is_valid_hex_color("#FF0000") is True
    assert organization_service._is_valid_hex_color("#00FF00") is True
    assert organization_service._is_valid_hex_color("#0000FF") is True
    assert organization_service._is_valid_hex_color("#ABCDEF") is True
    assert organization_service._is_valid_hex_color("#123456") is True


def test_is_valid_hex_color_invalid(organization_service):
    """Test invalid hex color validation."""
    # Act & Assert
    assert organization_service._is_valid_hex_color("FF0000") is False  # Missing #
    assert organization_service._is_valid_hex_color("#FFF") is False  # Too short
    assert organization_service._is_valid_hex_color("#FFFFF") is False  # Too short
    assert organization_service._is_valid_hex_color("#GGGGGG") is False  # Invalid hex
    assert organization_service._is_valid_hex_color("#00000") is False  # Too short
    assert organization_service._is_valid_hex_color("") is False  # Empty
    assert organization_service._is_valid_hex_color(None) is False  # None


def test_list_organizations_default_params(organization_service, mock_db_session):
    """Test listing organizations with default parameters."""
    # Arrange
    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
    mock_db_session.query.return_value = mock_query

    # Act
    result = organization_service.list_organizations(
        db=mock_db_session
    )

    # Assert
    assert isinstance(result, list)


def test_list_organizations_with_filters(organization_service, mock_db_session):
    """Test listing organizations with custom filters."""
    # Arrange
    mock_query = MagicMock()
    mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
    mock_db_session.query.return_value = mock_query

    # Act
    result = organization_service.list_organizations(
        db=mock_db_session,
        skip=10,
        limit=20,
        include_inactive=True
    )

    # Assert
    assert isinstance(result, list)
