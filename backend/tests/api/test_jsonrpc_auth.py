"""
Unit tests for JSON-RPC JWT authentication.
"""
import pytest
from unittest.mock import Mock
from src.api.jsonrpc.auth import validate_websocket_token, get_token_payload


class TestGetTokenPayload:
    """Test get_token_payload function"""

    def test_valid_token_returns_payload(self, valid_jwt_token):
        """Test that valid JWT token returns payload"""
        payload = get_token_payload(valid_jwt_token)
        assert payload is not None
        assert 'sub' in payload or 'user_id' in payload

    def test_none_token_returns_none(self):
        """Test that None token returns None"""
        payload = get_token_payload(None)
        assert payload is None

    def test_empty_token_returns_none(self):
        """Test that empty string token returns None"""
        payload = get_token_payload("")
        assert payload is None

    def test_invalid_token_returns_none(self):
        """Test that invalid token returns None"""
        payload = get_token_payload("not.a.valid.token")
        assert payload is None

    def test_expired_token_returns_none(self, expired_jwt_token):
        """Test that expired token returns None"""
        payload = get_token_payload(expired_jwt_token)
        assert payload is None


class TestValidateWebsocketToken:
    """Test validate_websocket_token function"""

    def test_valid_token_returns_user(self, db_session, valid_jwt_token, test_user):
        """Test that valid token returns user object"""
        user = validate_websocket_token(valid_jwt_token, db_session)
        assert user is not None
        assert user.id == test_user.id

    def test_none_token_returns_none(self, db_session):
        """Test that None token returns None"""
        user = validate_websocket_token(None, db_session)
        assert user is None

    def test_empty_token_returns_none(self, db_session):
        """Test that empty string token returns None"""
        user = validate_websocket_token("", db_session)
        assert user is None

    def test_invalid_token_returns_none(self, db_session):
        """Test that invalid token returns None"""
        user = validate_websocket_token("invalid.token", db_session)
        assert user is None

    def test_token_with_invalid_uuid_returns_none(self, db_session, invalid_uuid_token):
        """Test that token with invalid UUID returns None"""
        user = validate_websocket_token(invalid_uuid_token, db_session)
        assert user is None

    def test_token_for_nonexistent_user_returns_none(self, db_session, token_for_nonexistent_user):
        """Test that token for nonexistent user returns None"""
        user = validate_websocket_token(token_for_nonexistent_user, db_session)
        assert user is None

    def test_token_without_sub_or_user_id_returns_none(self, db_session):
        """Test that token without 'sub' or 'user_id' claim returns None"""
        from src.auth.jwt import create_access_token
        # Create token without sub or user_id
        token = create_access_token({"role": "admin"})
        user = validate_websocket_token(token, db_session)
        assert user is None
