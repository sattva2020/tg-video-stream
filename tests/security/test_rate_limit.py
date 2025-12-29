import pytest
import requests
import os
import time

TARGET_URL = os.getenv("TEST_TARGET_URL", "http://localhost")
API_URL = f"{TARGET_URL}/api/health"

def is_responsive(url):
    try:
        requests.get(url, timeout=2)
        return True
    except:
        return False

@pytest.mark.skipif(not is_responsive(TARGET_URL), reason=f"Target {TARGET_URL} is not reachable")
def test_api_rate_limiting():
    """
    Test that sending requests faster than the limit triggers 503/429.
    Config: rate=10r/s, burst=20 nodelay.
    """
    session = requests.Session()
    blocked = False
    
    # Send 50 requests as fast as possible
    for _ in range(50):
        response = session.get(API_URL)
        if response.status_code in [503, 429]:
            blocked = True
            break
    
    assert blocked, "Should have been rate limited after exceeding burst"

@pytest.mark.skipif(not is_responsive(TARGET_URL), reason=f"Target {TARGET_URL} is not reachable")
def test_login_rate_limiting():
    """
    Test login endpoint rate limiting.
    Config: rate=5r/m, burst=2 nodelay.
    """
    login_url = f"{TARGET_URL}/api/auth/login"
    session = requests.Session()
    blocked = False
    
    # Send 10 requests
    for _ in range(10):
        # We expect 405 Method Not Allowed or 422 Validation Error if we GET/POST wrong data,
        # but Nginx rate limit happens BEFORE backend processing.
        # So we should get 503/429 eventually.
        response = session.post(login_url, json={"username": "test", "password": "test"})
        if response.status_code in [503, 429]:
            blocked = True
            break
            
    assert blocked, "Login endpoint should be strictly rate limited"
