import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.models import User, TelegramAccount
import src.services.telegram_auth

def test_telegram_auth_flow(client, db_session):
    # 1. Create and login a user
    email = "tg.user@example.com"
    password = "GoodPassword123!"
    
    # Register
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200 or resp.status_code == 409
    
    # Approve user
    user = db_session.query(User).filter(User.email == email).first()
    if user:
        user.status = "approved"
        db_session.commit()
        
    # Login
    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Mock dependencies in TelegramAuthService
    # We mock Client and redis inside the module where they are used
    with patch("src.services.telegram_auth.Client") as MockClient, \
         patch("src.services.telegram_auth.redis.from_url", new_callable=AsyncMock) as mock_redis_from_url, \
         patch("src.services.telegram_auth.SessionLocal") as MockSessionLocal:
        
        # Setup Redis mock
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.get.return_value = "phone_code_hash_123" # Return hash for sign_in
        
        # Setup Client mock
        mock_client_instance = MockClient.return_value
        mock_client_instance.connect = AsyncMock()
        mock_client_instance.disconnect = AsyncMock()
        mock_client_instance.send_code = AsyncMock(return_value=MagicMock(phone_code_hash="phone_code_hash_123"))
        
        mock_tg_user = MagicMock()
        mock_tg_user.id = 123456789
        mock_tg_user.first_name = "Test"
        mock_tg_user.username = "testuser"
        mock_tg_user.photo = None
        mock_client_instance.sign_in = AsyncMock(return_value=mock_tg_user)
        mock_client_instance.export_session_string = AsyncMock(return_value="session_string")
        
        # Setup SessionLocal to return our test db_session
        # We need to handle the context manager behavior if used, or just return the session
        # The service does: db = SessionLocal(); try... finally: db.close()
        # We don't want db.close() to actually close our test session.
        db_session.close = MagicMock()
        MockSessionLocal.return_value = db_session
        
        # 3. Send code
        # URL: /api/auth/telegram/send-code
        resp = client.post("/api/auth/telegram/send-code", json={"phone": "+1234567890"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["phone_code_hash"] == "phone_code_hash_123"
        
        # 4. Sign in
        # URL: /api/auth/telegram/login
        # Payload: phone, code, password (optional)
        resp = client.post("/api/auth/telegram/login", json={
            "phone": "+1234567890",
            "code": "12345",
            "password": "password"
        }, headers=headers)
        
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        
        # 5. Verify account in DB
        # Since we used the real service logic (with mocked external calls) and injected db_session,
        # the account should be in the DB.
        account = db_session.query(TelegramAccount).filter(TelegramAccount.user_id == user.id).first()
        assert account is not None
        assert account.phone == "+1234567890"
        assert account.tg_user_id == 123456789
