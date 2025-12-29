import pytest
import requests
import os

TARGET_URL = os.getenv("TEST_TARGET_URL", "http://localhost")

def is_responsive(url):
    try:
        response = requests.get(url, timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

@pytest.mark.skipif(not is_responsive(TARGET_URL), reason=f"Target {TARGET_URL} is not reachable")
class TestSecurityHeaders:
    def test_csp_header(self):
        response = requests.get(TARGET_URL)
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_hsts_header(self):
        response = requests.get(TARGET_URL)
        # HSTS is usually only respected over HTTPS, but Nginx 'always' sends it
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    def test_x_frame_options(self):
        response = requests.get(TARGET_URL)
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options(self):
        response = requests.get(TARGET_URL)
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_referrer_policy(self):
        response = requests.get(TARGET_URL)
        assert "Referrer-Policy" in response.headers
        assert "strict-origin-when-cross-origin" in response.headers["Referrer-Policy"]

    def test_permissions_policy(self):
        response = requests.get(TARGET_URL)
        assert "Permissions-Policy" in response.headers
        assert "geolocation=()" in response.headers["Permissions-Policy"]
