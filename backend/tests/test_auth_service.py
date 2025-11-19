import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

# Add src to path to allow imports
import os
import sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.auth_service import auth_service
from models.user import User

@pytest.fixture
def mock_db_session():
    """Pytest fixture for a mock SQLAlchemy session."""
    db_session = MagicMock()
    # Configure the query method to return a mock query object
    db_session.query.return_value.filter.return_value.first.return_value = None
    return db_session

@pytest.fixture
def sample_user_info():
    """Sample user info dictionary from Google."""
    return {
        "id": "1234567890",
        "email": "test.user@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }

@pytest.fixture
def existing_user():
    """A sample existing user object."""
    return User(
        id="a-uuid",
        google_id="1234567890",
        email="test.user@example.com",
        full_name="Test User",
    )

def test_get_or_create_user_creates_new_user(mock_db_session, sample_user_info):
    """
    Test that a new user is created when no existing user is found.
    """
    # Arrange: No user exists with the google_id or email
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act
    user = auth_service.get_or_create_user(mock_db_session, sample_user_info)

    # Assert
    assert user is not None
    assert user.google_id == sample_user_info["id"]
    assert user.email == sample_user_info["email"]
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

def test_get_or_create_user_retrieves_existing_user(mock_db_session, sample_user_info, existing_user):
    """
    Test that an existing user is retrieved if their google_id matches.
    """
    # Arrange: A user with the google_id exists
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_user

    # Act
    user = auth_service.get_or_create_user(mock_db_session, sample_user_info)

    # Assert
    assert user is not None
    assert user.id == existing_user.id
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once() # Called for update
    mock_db_session.refresh.assert_called_once()

def test_get_or_create_user_handles_email_conflict(mock_db_session, sample_user_info, existing_user):
    """
    Test that an exception is raised if the email exists but the google_id does not.
    """
    # Arrange: No user with google_id, but one with the same email
    # This requires the mock to return None on the first call (google_id) and the user on the second (email)
    mock_query = mock_db_session.query.return_value.filter
    mock_query.side_effect = [
        MagicMock(first=MagicMock(return_value=None)), # google_id query
        MagicMock(first=MagicMock(return_value=existing_user)) # email query
    ]


    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_or_create_user(mock_db_session, sample_user_info)
    
    assert exc_info.value.status_code == 409
    assert "An account with this email already exists" in exc_info.value.detail

@patch('services.auth_service.jwt.create_access_token')
def test_create_jwt_for_user(mock_create_access_token, existing_user):
    """
    Test that the JWT creation function is called with the correct user ID.
    """
    # Arrange
    mock_create_access_token.return_value = "test_jwt_token"

    # Act
    token = auth_service.create_jwt_for_user(existing_user)

    # Assert
    assert token == "test_jwt_token"
    mock_create_access_token.assert_called_once_with(data={"sub": str(existing_user.id)})


def test_password_hash_and_verify():
    password = "CorrectHorseBatteryStaple123!"
    hashed = auth_service.hash_password(password)
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpassword", hashed)


def test_password_reset_token_roundtrip():
    email = "reset.user@example.com"
    token = auth_service.generate_password_reset_token(email)
    assert token is not None
    # Immediately verify should succeed
    assert auth_service.verify_password_reset_token(token) == email
