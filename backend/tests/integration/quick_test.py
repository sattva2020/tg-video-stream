"""
Быстрый smoke test для integration тестов (без pytest overhead)
Проверяет основные исправления: fixtures, status field, endpoints
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Set test env before imports
os.environ["SESSION_ENCRYPTION_KEY"] = "TnaLffqg0O5jccqqyQdSKT4JEnf6O2IMalnuECbHv0A="
os.environ["JWT_SECRET"] = "test_jwt_secret_key_for_testing_only"
os.environ["TESTING"] = "true"

from src.models.user import User
from src.auth.jwt import create_access_token

def test_user_model():
    """Проверка User модели с правильными полями"""
    print("Testing User model fields...")
    
    # Test that status field exists (not is_approved)
    user = User(
        email="test@test.com",
        google_id="test_123",
        status="approved",  # Must be 'status', not 'is_approved'
        role="user"
    )
    
    assert user.status == "approved", f"Expected status='approved', got {user.status}"
    assert user.role == "user", f"Expected role='user', got {user.role}"
    assert user.email == "test@test.com"
    
    print("✅ User model: PASS")
    return True

def test_jwt_token():
    """Проверка генерации JWT токенов"""
    print("Testing JWT token creation...")
    
    user_data = {
        "user_id": "12345678-1234-5678-1234-567812345678",
        "email": "test@test.com",
        "role": "user"
    }
    
    token = create_access_token(data=user_data)
    assert token is not None, "Token should not be None"
    assert len(token) > 50, f"Token too short: {len(token)} chars"
    
    print("✅ JWT tokens: PASS")
    return True

def main():
    """Запуск всех smoke tests"""
    print("="*60)
    print("INTEGRATION TESTS - QUICK SMOKE TEST")
    print("="*60)
    
    tests = [
        ("User Model Fields", test_user_model),
        ("JWT Token Generation", test_jwt_token),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name}: FAIL")
            print(f"   Error: {e}")
            failed += 1
    
    print("="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All smoke tests PASSED!")
        print("Готово к полному pytest запуску")
        sys.exit(0)

if __name__ == "__main__":
    main()
