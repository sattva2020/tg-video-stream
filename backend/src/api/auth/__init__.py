"""
Auth модуль — объединяет все sub-routers и экспортирует зависимости.
"""
import logging

from fastapi import APIRouter, Response

from .oauth import router as oauth_router
from .email_password import router as email_password_router
from .linking import router as linking_router
from .telegram_widget import router as telegram_widget_router

# Re-export dependencies for external usage
from .dependencies import (
    get_current_user,
    require_admin,
    oauth2_scheme,
    make_rate_limit_dep,
)
from .utils import format_auth_error
from requests_oauthlib import OAuth2Session

logger = logging.getLogger(__name__)

# Главный роутер auth модуля
router = APIRouter()

# Включаем sub-routers
router.include_router(oauth_router)           # /google, /google/callback
router.include_router(email_password_router)  # /register, /login, /password-reset/*, /email-verify/*
router.include_router(linking_router)         # /link-account/*
router.include_router(telegram_widget_router) # /telegram-widget, /telegram-widget/link, /telegram-widget/unlink


@router.post("/logout")
async def logout(response: Response):
    """
    Выход из системы.
    
    Очищает cookie с токеном. Работает для всех способов авторизации:
    - Google OAuth
    - Email/Password
    - Telegram Login Widget
    """
    # Очищаем cookie с токеном
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
    
    logger.info("Logout: access_token cookie cleared")
    return {"message": "Logout successful"}


async def notify_admins_async(*args, **kwargs):
    """Compatibility stub for tests — real implementation can notify admins when needed.
    Tests patch this symbol, so keeping a no-op async function here avoids import errors.
    """
    return True


__all__ = [
    'router',
    'get_current_user',
    'require_admin',
    'oauth2_scheme',
    'make_rate_limit_dep',
    'format_auth_error',
    'notify_admins_async',
    'OAuth2Session',
]
