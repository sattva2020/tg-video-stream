"""
Google OAuth 2.0 аутентификация.
"""
import os
import logging
import hashlib
import hmac
import time

# ВАЖНО: Разрешить OAuth через HTTP (для разработки без SSL)
# В production ОБЯЗАТЕЛЬНО используйте HTTPS и удалите эту строку!
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import RedirectResponse
from requests_oauthlib import OAuth2Session
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db
from services.auth_service import auth_service

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google", tags=["OAuth"])

# Google OAuth config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret")

# OAuth 2.0 scopes
SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# State signing helpers
def sign_state(state: str) -> str:
    """Подписываем state с timestamp для проверки"""
    timestamp = str(int(time.time()))
    message = f"{state}:{timestamp}"
    signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{state}:{timestamp}:{signature}"

def verify_state(signed_state: str, max_age: int = 600) -> tuple[bool, str]:
    """Проверяем подпись state и возвращаем (valid, original_state)"""
    try:
        parts = signed_state.split(":")
        if len(parts) != 3:
            return False, ""
        state, timestamp, signature = parts
        
        # Проверяем время
        if int(time.time()) - int(timestamp) > max_age:
            logger.warning("State expired")
            return False, ""
        
        # Проверяем подпись
        message = f"{state}:{timestamp}"
        expected_sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("State signature mismatch")
            return False, ""
        
        return True, state
    except Exception as e:
        logger.error(f"State verification error: {e}")
        return False, ""


@router.get("")
async def google_login(request: Request):
    """
    Перенаправляет пользователя на страницу авторизации Google.
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID is not set.")
        raise ValueError("GOOGLE_CLIENT_ID is not set")

    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = google.authorization_url(
        AUTHORIZATION_URL,
        access_type="offline",
        prompt="select_account",
    )

    # Подписываем state для безопасной проверки без session
    signed_state = sign_state(state)
    
    # Определяем secure на основе redirect URI
    is_secure = REDIRECT_URI.startswith("https://")
    
    # Извлекаем домен из REDIRECT_URI для cookie
    from urllib.parse import urlparse
    parsed = urlparse(REDIRECT_URI)
    cookie_domain = parsed.hostname  # flowbooster.xyz
    
    # Сохраняем signed state в cookie
    response = RedirectResponse(authorization_url)
    response.set_cookie(
        key="oauth_state",
        value=signed_state,
        max_age=600,  # 10 минут
        httponly=True,
        samesite="lax",
        secure=is_secure,  # True для HTTPS (ngrok/production)
        domain=cookie_domain,  # Устанавливаем домен для работы между портами
    )
    
    logger.info(f"Redirecting user to Google. Cookie domain={cookie_domain}, secure={is_secure}")
    return response


@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Обрабатывает callback от Google, создаёт/получает пользователя,
    генерирует JWT и перенаправляет на фронтенд.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Получаем state из callback и из cookie
    callback_state = request.query_params.get('state', '')
    cookie_signed_state = request.cookies.get('oauth_state', '')
    
    # Проверяем подписанный state из cookie
    is_valid, original_state = verify_state(cookie_signed_state)
    
    if not is_valid or original_state != callback_state:
        logger.warning(f"OAuth state mismatch. Cookie valid: {is_valid}, States match: {original_state == callback_state}")
        return RedirectResponse(url=f'{frontend_url}/login?error=state_mismatch')

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google client credentials are not set.")
        raise ValueError("Google client credentials are not set")

    google = OAuth2Session(
        GOOGLE_CLIENT_ID,
        state=callback_state,
        redirect_uri=REDIRECT_URI
    )

    # Allow insecure transport for ngrok and localhost dev
    if 'localhost' in REDIRECT_URI or '127.0.0.1' in REDIRECT_URI or 'ngrok' in REDIRECT_URI:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    try:
        google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
        logger.info("Successfully fetched token from Google.")
    except Exception as e:
        logger.error(f"Error fetching token from Google: {e}", exc_info=True)
        return RedirectResponse(url=f'{frontend_url}/login?error=token_fetch_failed')

    # Получаем информацию о пользователе
    user_info_response = google.get("https://www.googleapis.com/oauth2/v1/userinfo")
    if user_info_response.status_code != 200:
        logger.error(f"Error fetching user info from Google. Status: {user_info_response.status_code}")
        return RedirectResponse(url=f'{frontend_url}/login?error=user_info_failed')

    user_info = user_info_response.json()
    logger.info(f"Successfully fetched user info for email: {user_info.get('email')}")

    # Создаём или получаем пользователя и генерируем JWT
    try:
        result = auth_service.get_or_create_user(db, user_info=user_info)
        if isinstance(result, tuple):
            user, created = result
        else:
            user, created = result, False

        # Новый пользователь — статус pending, JWT не выдаём
        if created or getattr(user, 'status', 'approved') != 'approved':
            try:
                from tasks.notifications import notify_admins_async
                notify_admins_async(user.id)
            except Exception:
                logger.exception('Failed to notify admins for new OAuth user')
            return RedirectResponse(url=f"{frontend_url}/login?status=pending")

        jwt_token = auth_service.create_jwt_for_user(user)
        logger.info(f"Successfully processed user and generated JWT for user ID: {user.id}")
    except Exception as e:
        logger.error(f"Error during user processing for email {user_info.get('email')}: {e}")
        return RedirectResponse(url=f'{frontend_url}/login?error=auth_process_failed')

    # Редирект на фронтенд с токеном
    frontend_callback_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback_url)
