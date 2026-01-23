"""
API module — integrates all API routers.

Mobile device management endpoints are available in mobile.py.
"""

from .mobile import router

__all__ = ["router"]
