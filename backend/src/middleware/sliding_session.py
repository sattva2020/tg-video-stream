"""
Sliding Session Middleware.

Автоматически продлевает JWT токен при каждом запросе,
если до истечения осталось меньше заданного порога.
"""
import os
import logging
from datetime import datetime, timezone, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth.jwt import decode_access_token, create_access_token

logger = logging.getLogger(__name__)

# Порог для обновления токена (по умолчанию 24 часа)
# Если до истечения осталось меньше этого времени — выдаём новый токен
TOKEN_REFRESH_THRESHOLD_HOURS = int(os.getenv("TOKEN_REFRESH_THRESHOLD_HOURS", 24))


class SlidingSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware для реализации sliding session.
    
    При каждом запросе:
    1. Проверяет наличие валидного JWT токена
    2. Если до истечения осталось < TOKEN_REFRESH_THRESHOLD_HOURS часов:
       - Создаёт новый токен с полным сроком действия
       - Добавляет его в заголовок ответа X-New-Token
       - Обновляет cookie access_token
    """
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Пропускаем публичные эндпоинты
        if self._is_public_endpoint(request.url.path):
            return response
        
        # Получаем токен из заголовка или cookie
        token = self._extract_token(request)
        if not token:
            return response
        
        # Декодируем токен
        payload = decode_access_token(token)
        if not payload:
            return response
        
        # Проверяем, нужно ли обновить токен
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return response
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_until_expiry = exp_datetime - now
        
        # Если до истечения меньше порога — выдаём новый токен
        threshold = timedelta(hours=TOKEN_REFRESH_THRESHOLD_HOURS)
        if time_until_expiry < threshold and time_until_expiry > timedelta(0):
            # Создаём новый токен с теми же данными (sub, role)
            new_token_data = {
                "sub": payload.get("sub"),
                "role": payload.get("role"),
            }
            new_token = create_access_token(data=new_token_data)
            
            # Добавляем новый токен в заголовок ответа
            response.headers["X-New-Token"] = new_token
            
            # Обновляем cookie
            access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))
            response.set_cookie(
                key="access_token",
                value=f"Bearer {new_token}",
                max_age=access_token_expire_minutes * 60,
                httponly=True,
                samesite="lax",
                secure=os.getenv("ENVIRONMENT", "development") == "production",
            )
            
            logger.info(
                f"Token refreshed for user {payload.get('sub')}, "
                f"was expiring in {time_until_expiry.total_seconds() / 3600:.1f}h"
            )
        
        return response
    
    def _extract_token(self, request: Request) -> str | None:
        """Извлекает JWT токен из заголовка Authorization или cookie."""
        # Сначала проверяем заголовок Authorization
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Затем проверяем cookie
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            if cookie_token.startswith("Bearer "):
                return cookie_token[7:]
            return cookie_token
        
        return None
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Проверяет, является ли эндпоинт публичным (не требует авторизации)."""
        public_paths = [
            "/",
            "/health",
            "/api/auth/google",
            "/api/auth/google/callback",
            "/api/auth/telegram-widget",
            "/api/auth/telegram-login",
            "/api/auth/logout",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        
        # Точное совпадение
        if path in public_paths:
            return True
        
        # Начинается с публичного пути
        for public_path in public_paths:
            if path.startswith(public_path + "/"):
                return True
        
        return False
