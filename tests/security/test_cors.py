import pytest
import requests
import os

TARGET_URL = os.getenv("TEST_TARGET_URL", "http://localhost")
API_URL = f"{TARGET_URL}/api/health"

def is_responsive(url):
    try:
        requests.get(url, timeout=2)
        return True
    except:
        return False

@pytest.mark.skipif(not is_responsive(TARGET_URL), reason=f"Target {TARGET_URL} is not reachable")
class TestCORS:
    def test_allowed_origin(self):
        # Assuming http://localhost:3000 is in ALLOWED_ORIGINS
        origin = "http://localhost:3000"
        headers = {"Origin": origin}
        response = requests.get(API_URL, headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == origin
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_disallowed_origin(self):
        origin = "http://evil-attacker.com"
        headers = {"Origin": origin}
        response = requests.get(API_URL, headers=headers)
        
        # If disallowed, FastAPI/Starlette usually doesn't send the header
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        assert allow_origin != origin
