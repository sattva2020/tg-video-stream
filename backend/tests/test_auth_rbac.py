import pytest
from services.auth_service import auth_service
from auth import jwt

class MockUser:
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

def test_jwt_contains_role():
    """
    Test that the JWT token generated for a user includes the 'role' claim.
    This test is expected to fail initially until T007 is implemented.
    """
    user = MockUser(id="123", email="test@example.com", role="user")
    
    token = auth_service.create_jwt_for_user(user)
    payload = jwt.decode_access_token(token)
    
    assert "role" in payload
    assert payload["role"] == "user"

def test_admin_jwt_contains_admin_role():
    """
    Test that the JWT token generated for an admin includes the 'admin' role.
    """
    user = MockUser(id="456", email="admin@example.com", role="admin")
    
    token = auth_service.create_jwt_for_user(user)
    payload = jwt.decode_access_token(token)
    
    assert "role" in payload
    assert payload["role"] == "admin"
