import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
import re

import os
import sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from main import app
from database import Base, get_db
from models.user import User

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    """
    Create a TestClient instance for the tests.
    """
    # Create tables before yielding the client
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Drop tables after all tests in the module are done
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def cleanup_data():
    """Clean up data in tables after each test."""
    yield
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()


def test_google_login_redirect(client):
    """
    Test that the /api/auth/google endpoint redirects correctly.
    """
    response = client.get("/api/auth/google", follow_redirects=False)
    assert response.status_code == 307 # Temporary Redirect
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth")

@patch('api.auth.OAuth2Session')
def test_google_callback_success(mock_oauth_session, client):
    """
    Test the successful authentication callback flow.
    """
    # Arrange
    # Mock the OAuth2Session instance and its methods
    mock_instance = mock_oauth_session.return_value
    # Mock the first call to get the authorization URL
    mock_instance.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/v2/auth?state=test_state", "test_state")
    # Mock the second part of the flow within the callback
    mock_instance.fetch_token.return_value = {"access_token": "fake_token"}
    
    mock_user_info = {
        "id": "12345",
        "email": "new.user@example.com",
        "name": "New User",
        "picture": "https://example.com/pic.jpg"
    }
    mock_instance.get.return_value.status_code = 200
    mock_instance.get.return_value.json.return_value = mock_user_info

    # 1. First, hit the login endpoint to get the state and set the session cookie
    login_response = client.get("/api/auth/google", follow_redirects=False)
    assert login_response.status_code == 307
    
    # The state is now set in the session cookie by the TestClient
    # We can use the state we defined in the mock
    state = "test_state"

    # 2. Now, hit the callback endpoint with the correct state
    callback_response = client.get(f"/api/auth/google/callback?state={state}&code=fake_code", follow_redirects=False)

    # Assert
    assert callback_response.status_code == 307
    assert callback_response.headers["location"].startswith("/auth/google/callback#token=")

    # Verify a user was created in the test DB
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "new.user@example.com").first()
    assert user is not None
    assert user.google_id == "12345"
    db.close()

def test_google_callback_state_mismatch(client):
    """
    Test that the callback fails if the state does not match.
    """
    # Arrange: Hit the login endpoint to set a valid session state
    client.get("/api/auth/google", follow_redirects=False)

    # Act: Hit the callback with a deliberately incorrect state
    response = client.get("/api/auth/google/callback?state=wrong_state&code=fake_code", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/login?error=state_mismatch"

def test_logout(client):
    """
    Test the /api/auth/logout endpoint.
    """
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}


def test_register_and_login_flow(client):
    # Register a new user
    payload = {"email": "new.user2@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    # Login with same credentials
    resp2 = client.post("/api/auth/login", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "access_token" in data2

    # Attempt to register again should fail
    resp3 = client.post("/api/auth/register", json=payload)
    assert resp3.status_code == 409
