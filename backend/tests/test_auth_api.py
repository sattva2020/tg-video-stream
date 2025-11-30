import pytest
from unittest.mock import patch
import os
import sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import api.auth as api_auth
from src.models.user import User

@pytest.fixture(autouse=True)
def cleanup_data(db_session):
    """Clean up data in tables before/after each test."""
    # Ensure rate limiter storage is clean at test start
    try:
        # rate limiter lives in api.auth.dependencies
        import api.auth.dependencies as deps
        deps._rate_limit_storage.clear()
    except Exception:
        pass
    yield
    # Reset in-memory rate limit storage between tests to avoid cross-test pollution
    try:
        import api.auth.dependencies as deps
        deps._rate_limit_storage.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def mock_notifications():
    """Mock the notification system to prevent DB access during tests."""
    with patch('api.auth.notify_admins_async') as mock_notify:
        mock_notify.return_value = True
        yield mock_notify

def test_google_login_redirect(client):
    """
    Test that the /api/auth/google endpoint redirects correctly.
    """
    response = client.get("/api/auth/google", follow_redirects=False)
    assert response.status_code == 307 # Temporary Redirect
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth")

@patch('api.auth.oauth.OAuth2Session')
def test_google_callback_success(mock_oauth_session, client, db_session):
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

    # Assert — for a newly created OAuth user we expect the app to redirect to login indicating pending
    assert callback_response.status_code == 307
    loc = callback_response.headers.get("location", "")
    assert "/login" in loc and "status=pending" in loc

    # Verify a user was created with status == 'pending'
    user = db_session.query(User).filter(User.email == "new.user@example.com").first()
    assert user is not None
    assert user.google_id == "12345"
    assert getattr(user, 'status', 'approved') == 'pending'

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
    assert response.headers["location"].endswith("/login?error=state_mismatch")


def test_google_callback_existing_approved_user_gets_jwt(monkeypatch, client, db_session):
    # Create an approved user with Google ID first
    u = User(google_id='g-777', email='exists@example.com', status='approved')
    db_session.add(u); db_session.commit(); db_session.refresh(u)

    # Make OAuth flow return same user info
    from unittest.mock import patch
    with patch('api.auth.oauth.OAuth2Session') as mock_oauth_session:
        mock_instance = mock_oauth_session.return_value
        mock_instance.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/v2/auth?state=test_state", "test_state")
        mock_instance.fetch_token.return_value = {"access_token": "fake_token"}
        mock_instance.get.return_value.status_code = 200
        mock_instance.get.return_value.json.return_value = {"id": "g-777", "email": "exists@example.com", "name": "Existing", "picture": ""}

        login_response = client.get("/api/auth/google", follow_redirects=False)
        assert login_response.status_code == 307

        state = 'test_state'
        # Make session state work
        callback_response = client.get(f"/api/auth/google/callback?state={state}&code=fake_code", follow_redirects=False)
        # Now the existing approved user should be issued a token and redirected to frontend callback
        assert callback_response.status_code == 307
        loc = callback_response.headers.get('location', '')
        assert '/auth/callback' in loc and 'token=' in loc

def test_logout(client):
    """
    Test the /api/auth/logout endpoint.
    """
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}


def test_register_and_login_flow(client, db_session):
    # Register a new user
    payload = {"email": "new.user2@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # New behavior: status is pending, no access_token
    assert data["status"] == "pending"
    assert "access_token" not in data

    # Approve user manually - need to expire cache first
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None, "User not found in database after registration"
    user.status = "approved"
    db_session.commit()

    # Login with same credentials
    resp2 = client.post("/api/auth/login", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "access_token" in data2

    # Attempt to register again should fail
    resp3 = client.post("/api/auth/register", json=payload)
    assert resp3.status_code == 409


def test_login_with_form_urlencoded(client, db_session):
    # Register a new user
    payload = {"email": "form.user@example.com", "password": "FormPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200

    # Approve user manually
    user = db_session.query(User).filter(User.email == payload["email"]).first()
    user.status = "approved"
    db_session.commit()

    # Login using form-urlencoded body (username/password) to support legacy clients
    form_resp = client.post("/api/auth/login", data={"username": payload["email"], "password": payload["password"]})
    assert form_resp.status_code == 200
    assert "access_token" in form_resp.json()


def test_link_account_flow(client, db_session):
    # Setup: create a Google-only user directly in DB
    g_user = User(google_id="g-123", email="link.user@example.com", status="approved")
    db_session.add(g_user)
    db_session.commit()
    db_session.refresh(g_user)

    # Ensure SMTP not set
    import os
    os.environ.pop("SMTP_HOST", None)

    # Request link token (dev mode should return token)
    resp = client.post("/api/auth/link-account/request", json={"email": "link.user@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "token" in data
    token = data["token"]

    # Confirm link with a weak password should fail
    resp2 = client.post("/api/auth/link-account/confirm", json={"token": token, "password": "short"})
    assert resp2.status_code == 400

    # Confirm with strong password
    resp3 = client.post("/api/auth/link-account/confirm", json={"token": token, "password": "NewGoodPassword123!"})
    assert resp3.status_code == 200
    assert "access_token" in resp3.json()

    # Now login with new password
    resp4 = client.post("/api/auth/login", json={"email": "link.user@example.com", "password": "NewGoodPassword123!"})
    assert resp4.status_code == 200
    assert "access_token" in resp4.json()


def test_password_reset_request_and_confirm(client, db_session):
    # Ensure SMTP is not set so dev-mode returns token
    import os
    os.environ.pop("SMTP_HOST", None)

    email = "reset.user@example.com"
    payload = {"email": email, "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200

    # Approve user manually
    user = db_session.query(User).filter(User.email == email).first()
    user.status = "approved"
    db_session.commit()

    # Request reset should return token in dev mode
    resp2 = client.post("/api/auth/password-reset/request", json={"email": email})
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "ok"
    assert "token" in data
    token = data["token"]

    # Confirm reset with weak password should fail
    weak_payload = {"token": token, "password": "short"}
    resp3 = client.post("/api/auth/password-reset/confirm", json=weak_payload)
    assert resp3.status_code == 400

    # Confirm with good password
    pw_payload = {"token": token, "password": "NewGoodPassword123!"}
    resp4 = client.post("/api/auth/password-reset/confirm", json=pw_payload)
    assert resp4.status_code == 200
    assert "access_token" in resp4.json()

    # Verify that the new password works for login
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "NewGoodPassword123!"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_rate_limit(client, db_session):
    # Create a user
    payload = {"email": "rl.user@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200

    # Approve user manually
    user = db_session.query(User).filter(User.email == payload["email"]).first()
    user.status = "approved"
    db_session.commit()

    # Attempt more than RATE_LIMIT_MAX times incorrect password
    # Ensure rate limit storage is empty at start
    max_attempts = int(os.getenv("RATE_LIMIT_MAX", 5))
    for i in range(max_attempts):
        r = client.post("/api/auth/login", json={"email": payload["email"], "password": "WrongPassword"})
        # invalid credentials until limit reached
        if i < max_attempts - 1:
            assert r.status_code == 401
    # Next attempt should be rate limited
    r2 = client.post("/api/auth/login", json={"email": payload["email"], "password": "WrongPassword"})
    assert r2.status_code == 429








def test_email_verification_flow(client, db_session):
    import os
    os.environ.pop("SMTP_HOST", None)
    email = "verify.user@example.com"
    payload = {"email": email, "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200

    # Request verification token
    r = client.post("/api/auth/email-verify/request", json={"email": email})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "token" in data
    token = data["token"]

    # Confirm token
    r2 = client.post("/api/auth/email-verify/confirm", json={"token": token})
    assert r2.status_code == 200

    # Check DB
    user = db_session.query(User).filter(User.email == email).first()
    assert user.email_verified


