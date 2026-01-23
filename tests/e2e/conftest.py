"""
Pytest configuration for E2E SDK tests.

These tests verify SDK functionality against real API endpoints.
"""
import os
import sys
from pathlib import Path

# ==================== CRITICAL: Set env variables FIRST ====================
# This MUST be BEFORE any other imports
os.environ["SESSION_ENCRYPTION_KEY"] = "TnaLffqg0O5jccqqyQdSKT4JEnf6O2IMalnuECbHv0A="
os.environ["JWT_SECRET"] = "test_jwt_secret_key_for_testing_only"
os.environ["TESTING"] = "true"

# Force-disable external Redis to avoid async limiter in tests
os.environ.pop("REDIS_URL", None)
# ============================================================================

# Add paths to sys.path
project_root = Path(__file__).parent.parent.parent
backend_src = project_root / "backend" / "src"
python_sdk = project_root / "sdks" / "python"
backend_root = project_root / "backend"

# Add to sys.path
for path in [backend_src, python_sdk, backend_root, project_root]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
