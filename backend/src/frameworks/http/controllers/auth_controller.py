"""
Authentication Controllers
FRAMEWORKS LAYER
Dependencies: Infrastructure ✅, Application ✅

Объединяет все authentication endpoints:
- OAuth (Google)
- Email/Password
- Account linking
- Telegram Widget
- TOTP (2FA)

Clean Architecture DTOs:
- AuthenticateUserRequest/Response - для логина
- RegisterUserRequest/Response - для регистрации

TODO: Мигрировать sub-routers на использование DTOs:
- src/api/auth/oauth.py
- src/api/auth/email_password.py
- src/api/auth/linking.py
- src/api/auth/telegram_widget.py
- src/api/auth/totp.py
"""

import logging
from fastapi import APIRouter, Response

# Clean Architecture DTOs (для будущей миграции)
from src.application.dtos.auth import (
    AuthenticateUserRequest,
    AuthenticateUserResponse,
    RegisterUserRequest,
    RegisterUserResponse,
)

# Temporary imports from old location until full migration
from src.api.auth.oauth import router as oauth_router
from src.api.auth.email_password import router as email_password_router
from src.api.auth.linking import router as linking_router
from src.api.auth.telegram_widget import router as telegram_widget_router
from src.api.auth.totp import router as totp_router

logger = logging.getLogger(__name__)

# Main auth router
router = APIRouter()

# Include sub-routers
router.include_router(oauth_router)           # /google, /google/callback
router.include_router(email_password_router)  # /register, /login, /password-reset/*, /email-verify/*
router.include_router(linking_router)         # /link-account/*
router.include_router(telegram_widget_router) # /telegram-widget, /telegram-widget/link, /telegram-widget/unlink
router.include_router(totp_router)            # /totp/*


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
    """Compatibility stub for tests."""
    return True


# ========================
# Helper functions for DTO conversion
# ========================

def _create_auth_request_dto(email: str, password: str) -> AuthenticateUserRequest:
    """
    Создаёт DTO для аутентификации.
    
    Используется при миграции legacy handlers.
    
    Args:
        email: Email пользователя
        password: Пароль
        
    Returns:
        AuthenticateUserRequest DTO
    """
    return AuthenticateUserRequest(email=email, password=password)


def _create_register_request_dto(
    email: str, 
    username: str, 
    password: str
) -> RegisterUserRequest:
    """
    Создаёт DTO для регистрации.
    
    Используется при миграции legacy handlers.
    
    Args:
        email: Email пользователя
        username: Имя пользователя
        password: Пароль
        
    Returns:
        RegisterUserRequest DTO
    """
    return RegisterUserRequest(email=email, username=username, password=password)
