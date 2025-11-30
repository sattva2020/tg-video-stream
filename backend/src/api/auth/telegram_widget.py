"""
API endpoints для авторизации через Telegram Login Widget.

Endpoints:
- POST /api/auth/telegram-widget — авторизация/регистрация через виджет
- POST /api/auth/telegram-widget/link — привязка Telegram к существующему аккаунту
- DELETE /api/auth/telegram-widget/unlink — отвязка Telegram от аккаунта
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User, UserStatus
from src.schemas.telegram_auth import (
    TelegramAuthRequest,
    TelegramAuthResponse,
    TelegramLinkRequest,
    TelegramLinkResponse,
    TelegramUnlinkResponse,
    UserResponse,
)
from src.services.telegram_widget_auth_service import telegram_widget_auth_service
from src.services.auth_service import auth_service
from src.api.auth.dependencies import get_current_user
from src.core.logging_utils import telegram_auth_logger, TelegramAuthEvent


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram-widget", tags=["Telegram Widget Auth"])


def _build_full_name(first_name: str, last_name: Optional[str]) -> str:
    """Собирает полное имя из first_name и last_name."""
    if last_name:
        return f"{first_name} {last_name}"
    return first_name


def _set_auth_cookie(response: Response, access_token: str):
    """Устанавливает JWT в HttpOnly cookie."""
    # Cookie expiration = token expiration (24h по умолчанию)
    max_age = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) * 60
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=max_age,
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "development") == "production",
        samesite="lax",
        path="/",
    )


@router.post(
    "",
    response_model=TelegramAuthResponse,
    responses={
        400: {"description": "Невалидные данные или подпись"},
        409: {"description": "Telegram уже привязан к другому аккаунту"},
        429: {"description": "Превышен лимит запросов"},
    },
)
async def telegram_auth(
    data: TelegramAuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Авторизация или регистрация через Telegram Login Widget.
    
    При первом входе создаётся новый пользователь со статусом 'pending'.
    При повторном входе обновляются данные профиля (имя, фото).
    
    JWT токен устанавливается в HttpOnly cookie.
    """
    # 1. Верифицируем данные от Telegram
    is_valid, error_message = telegram_widget_auth_service.verify(data)
    if not is_valid:
        telegram_auth_logger.warning(
            TelegramAuthEvent.LOGIN_FAILED,
            f"Telegram auth failed: {error_message}",
            telegram_id=data.id,
            ip_address=request.client.host if request.client else None,
            username=data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Невалидные данные авторизации"
        )
    
    # 2. Проверяем Turnstile CAPTCHA если токен предоставлен
    if data.turnstile_token:
        turnstile_valid = await telegram_widget_auth_service.verify_turnstile(
            data.turnstile_token,
            remote_ip=request.client.host if request.client else None
        )
        if not turnstile_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Проверка CAPTCHA не пройдена"
            )
    
    # 3. Ищем существующего пользователя по telegram_id
    user = db.query(User).filter(User.telegram_id == data.id).first()
    is_new_user = False
    
    if user:
        # Обновляем данные профиля при каждом входе
        user.full_name = _build_full_name(data.first_name, data.last_name)
        user.telegram_username = data.username
        if data.photo_url:
            user.profile_picture_url = data.photo_url
        db.commit()
        db.refresh(user)
        telegram_auth_logger.info(
            TelegramAuthEvent.LOGIN_SUCCESS,
            "Существующий пользователь вошёл через Telegram",
            telegram_id=data.id,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            username=data.username,
        )
    else:
        # Создаём нового пользователя
        user = User(
            telegram_id=data.id,
            telegram_username=data.username,
            full_name=_build_full_name(data.first_name, data.last_name),
            profile_picture_url=data.photo_url,
            email=None,  # Telegram-only пользователь
            status=UserStatus.PENDING,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new_user = True
        telegram_auth_logger.info(
            TelegramAuthEvent.REGISTRATION_SUCCESS,
            "Новый пользователь зарегистрирован через Telegram",
            telegram_id=data.id,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            username=data.username,
            extra={"status": "pending"}
        )
    
    # 4. Создаём JWT токен
    access_token = auth_service.create_jwt_for_user(user)
    
    # 5. Устанавливаем cookie
    _set_auth_cookie(response, access_token)
    
    # 6. Формируем ответ
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        profile_picture_url=user.profile_picture_url,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        status=user.status.value if hasattr(user.status, 'value') else str(user.status),
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
    )
    
    return TelegramAuthResponse(
        success=True,
        user=user_response,
        is_new_user=is_new_user,
        message="Регистрация успешна" if is_new_user else "Авторизация успешна"
    )


@router.post(
    "/link",
    response_model=TelegramLinkResponse,
    responses={
        400: {"description": "Невалидные данные или подпись"},
        401: {"description": "Не авторизован"},
        409: {"description": "Telegram уже привязан к этому или другому аккаунту"},
    },
)
async def link_telegram(
    data: TelegramLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Привязка Telegram к существующему аккаунту.
    
    Требует авторизации. Позволяет пользователю с Google/email аккаунтом
    добавить Telegram как дополнительный способ входа.
    """
    # 1. Верифицируем данные от Telegram
    auth_request = TelegramAuthRequest(
        id=data.id,
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        photo_url=data.photo_url,
        auth_date=data.auth_date,
        hash=data.hash,
        turnstile_token=None,  # Для link не требуется CAPTCHA
    )
    is_valid, error_message = telegram_widget_auth_service.verify(auth_request)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Невалидные данные авторизации"
        )
    
    # 2. Проверяем, не привязан ли уже Telegram к текущему пользователю
    if current_user.telegram_id:
        if current_user.telegram_id == data.id:
            telegram_auth_logger.warning(
                TelegramAuthEvent.LINK_CONFLICT,
                "Попытка повторной привязки того же Telegram",
                telegram_id=data.id,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Этот Telegram аккаунт уже привязан к вашему аккаунту"
            )
        else:
            telegram_auth_logger.warning(
                TelegramAuthEvent.LINK_CONFLICT,
                "Попытка привязки другого Telegram к аккаунту с уже привязанным",
                telegram_id=data.id,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                extra={"existing_telegram_id": current_user.telegram_id}
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="К вашему аккаунту уже привязан другой Telegram"
            )
    
    # 3. Проверяем, не привязан ли этот Telegram к другому пользователю
    existing_user = db.query(User).filter(User.telegram_id == data.id).first()
    if existing_user:
        telegram_auth_logger.warning(
            TelegramAuthEvent.LINK_CONFLICT,
            "Telegram уже привязан к другому пользователю",
            telegram_id=data.id,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            extra={"existing_user_id": existing_user.id}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот Telegram аккаунт уже привязан к другому пользователю"
        )
    
    # 4. Привязываем Telegram
    current_user.telegram_id = data.id
    current_user.telegram_username = data.username
    
    # Обновляем фото если его не было
    if data.photo_url and not current_user.profile_picture_url:
        current_user.profile_picture_url = data.photo_url
    
    db.commit()
    db.refresh(current_user)
    
    telegram_auth_logger.info(
        TelegramAuthEvent.LINK_SUCCESS,
        "Telegram успешно привязан к аккаунту",
        telegram_id=data.id,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        username=data.username,
    )
    
    return TelegramLinkResponse(
        success=True,
        message="Telegram успешно привязан к аккаунту",
        telegram_id=data.id,
        telegram_username=data.username,
    )


@router.delete(
    "/unlink",
    response_model=TelegramUnlinkResponse,
    responses={
        400: {"description": "Нельзя отвязать единственный способ входа"},
        401: {"description": "Не авторизован"},
        404: {"description": "Telegram не привязан к аккаунту"},
    },
)
async def unlink_telegram(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отвязка Telegram от аккаунта.
    
    Разрешена только если у пользователя есть альтернативный способ входа
    (Google OAuth или email + пароль).
    """
    # 1. Проверяем, привязан ли Telegram
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram не привязан к вашему аккаунту"
        )
    
    # 2. Проверяем наличие альтернативного способа входа
    if not current_user.has_alternative_auth():
        telegram_auth_logger.warning(
            TelegramAuthEvent.UNLINK_BLOCKED,
            "Попытка отвязки единственного способа входа",
            telegram_id=current_user.telegram_id,
            user_id=current_user.id,
            username=current_user.telegram_username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отвязать Telegram — это единственный способ входа. "
                   "Сначала привяжите email или Google аккаунт."
        )
    
    # 3. Отвязываем Telegram
    old_telegram_id = current_user.telegram_id
    old_telegram_username = current_user.telegram_username
    current_user.telegram_id = None
    current_user.telegram_username = None
    db.commit()
    
    telegram_auth_logger.info(
        TelegramAuthEvent.UNLINK_SUCCESS,
        "Telegram успешно отвязан от аккаунта",
        telegram_id=old_telegram_id,
        user_id=current_user.id,
        username=old_telegram_username,
    )
    
    return TelegramUnlinkResponse(
        success=True,
        message="Telegram успешно отвязан от аккаунта"
    )
