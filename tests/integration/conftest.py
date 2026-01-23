"""
Configuration and fixtures for integration tests.

Integration tests verify end-to-end workflows across multiple components:
- Database models and migrations
- API endpoints and services
- Redis state management
- External service integration (streamer, Celery)
"""
import pytest
import sys
import os

# Ensure backend/src is in path
backend_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
src_root = os.path.join(backend_root, 'src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

# Import backend conftest for shared fixtures
# This gives us access to: db_session, client, admin_user, etc.
from backend.tests.conftest import *
