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
from services.activity_service import ActivityService

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
    logger.info(f"OAuth initialized with REDIRECT_URI: {REDIRECT_URI}")
    authorization_url, state = google.authorization_url(
        AUTHORIZATION_URL,
        access_type="offline",
        prompt="select_account",
    )
    
    # Подписываем state для безопасной проверки без session/cookie
    signed_state = sign_state(state)
    
    # Заменяем state в URL на signed_state, чтобы он вернулся от Google
    # и мы могли верифицировать его без cookie
    authorization_url_with_signed_state = authorization_url.replace(
        f"state={state}", 
        f"state={signed_state}"
    )
    
    logger.info(f"Generated Authorization URL with signed state")
    
    response = RedirectResponse(authorization_url_with_signed_state)
    return response


@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Обрабатывает callback от Google, создаёт/получает пользователя,
    генерирует JWT и перенаправляет на фронтенд.
    """
    print(f"\n\n========== CALLBACK FUNCTION CALLED ==========")
    print(f"Request URL: {request.url}")
    print(f"Request path: {request.url.path}")
    print(f"Query params: {dict(request.query_params)}")
    print(f"=========================================\n\n")
    
    frontend_url = os.getenv("FRONTEND_URL", os.getenv("FRONTEND_BASE_URL", "http://localhost:3000"))
    
    # Получаем signed_state из URL (теперь state в URL уже подписан)
    signed_state = request.query_params.get('state', '')
    
    print(f"[1] Callback received. signed_state={signed_state[:30] if signed_state else 'EMPTY'}...")
    
    # Верифицируем подписанный state напрямую из URL (без cookie)
    is_valid, original_state = verify_state(signed_state)
    
    print(f"[2] State verification: is_valid={is_valid}, original_state={original_state[:20] if original_state else 'EMPTY'}...")
    
    if not is_valid:
        print(f"[ERROR] OAuth state verification failed!")
        logger.warning(f"OAuth state verification failed. is_valid={is_valid}")
        return RedirectResponse(url=f'{frontend_url}/login?error=state_mismatch')
    
    print(f"[3] State verified successfully!")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print(f"[ERROR] Google client credentials missing!")
        logger.error("Google client credentials are not set.")
        raise ValueError("Google client credentials are not set")

    # Создаём OAuth2Session БЕЗ state чтобы отключить проверку oauthlib
    # (мы уже сами проверили signed_state выше)
    google = OAuth2Session(
        GOOGLE_CLIENT_ID,
        redirect_uri=REDIRECT_URI
    )

    print(f"[4] OAuth2Session created with REDIRECT_URI={REDIRECT_URI}")

    # Allow insecure transport for ngrok and localhost dev
    if 'localhost' in REDIRECT_URI or '127.0.0.1' in REDIRECT_URI or 'ngrok' in REDIRECT_URI:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Строим правильный URL используя REDIRECT_URI (с правильным host)
    # и query параметрами из request (но со original_state вместо signed_state)
    query_params = dict(request.query_params)
    query_params['state'] = original_state  # Заменяем signed_state на original_state
    
    # Формируем query string
    query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
    
    # Строим полный URL используя REDIRECT_URI
    original_url = f"{REDIRECT_URI}?{query_string}"
    
    print(f"[5] Constructed auth response URL: {original_url[:100]}...")
    logger.info(f"Constructed auth response URL with original_state")
    
    try:
        print(f"[6] Calling fetch_token...")
        # Передаём state=original_state для oauthlib проверки
        google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=original_url,
            state=original_state  # Явно передаём для oauthlib
        )
        print(f"[7] Successfully fetched token from Google!")
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

        # Логируем регистрацию нового пользователя через OAuth
        if created:
            activity_service = ActivityService(db)
            activity_service.log_event(
                event_type="user_registered",
                message=f"Новый пользователь зарегистрирован через Google: {user.email}",
                user_id=user.id,
                user_email=user.email,
                details={"method": "google_oauth", "status": "pending"}
            )

        # Новый пользователь — статус pending, JWT не выдаём
        # Проверяем статус: active = одобрен, pending = ожидает
        user_status = getattr(user, 'status', 'active')
        if created or user_status not in ('active', 'approved'):
            try:
                from tasks.notifications import notify_admins_async
                notify_admins_async(user.id)
            except Exception:
                logger.exception('Failed to notify admins for new OAuth user')
            # Редиректим на страницу ожидания подтверждения
            # Сохраняем временный токен для проверки статуса
            temp_token = auth_service.create_jwt_for_user(user)
            return RedirectResponse(url=f"{frontend_url}/auth/callback?token={temp_token}&status=pending")

        # Обновляем время последнего входа для одобренного пользователя
        try:
            if hasattr(user, 'update_last_login'):
                user.update_last_login()
                db.add(user)
                db.commit()
        except Exception:
            logger.exception('Failed to update last_login for OAuth user')

        jwt_token = auth_service.create_jwt_for_user(user)
        logger.info(f"Successfully processed user and generated JWT for user ID: {user.id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception(f"Error during user processing for email {user_info.get('email')}: {e}")
        return RedirectResponse(url=f'{frontend_url}/login?error=auth_process_failed&details={str(e)}')

    # Редирект на фронтенд с токеном
    frontend_callback_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback_url)
