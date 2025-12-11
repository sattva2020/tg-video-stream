"""
Публичные endpoints для Telegram-авторизации на странице входа.
Не требуют предварительной аутентификации.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Union
from src.services.telegram_auth import telegram_auth_service, RateLimitError
from src.services.telegram_rate_limiter import rate_limiter
from src.services.encryption import encryption_service
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.telegram import TelegramAccount
from src.auth.jwt import create_access_token
import uuid
from datetime import timedelta

router = APIRouter(tags=["telegram-login"])


class PhoneRequest(BaseModel):
    phone: str


class LoginRequest(BaseModel):
    phone: str
    code: str
    password: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TwoFARequiredResponse(BaseModel):
    status: str = "2fa_required"
    message: str = "Введите пароль двухфакторной аутентификации"


def _handle_rate_limit_error(e: RateLimitError) -> HTTPException:
    """Преобразует RateLimitError в HTTPException с детальной информацией"""
    limit_info = e.limit_info
    return HTTPException(
        status_code=429,
        detail={
            "error": "rate_limit",
            "type": limit_info.type.value,
            "message": limit_info.message,
            "wait_seconds": limit_info.wait_seconds,
            "remaining_seconds": limit_info.remaining_seconds,
            "retry_after": limit_info.retry_after.isoformat() if limit_info.retry_after else None,
        },
        headers={"Retry-After": str(limit_info.remaining_seconds)} if limit_info.remaining_seconds > 0 else None
    )


@router.post("/send-code")
async def send_code_public(request: PhoneRequest):
    """
    Отправить код подтверждения на телефон (публичный endpoint).
    Используется на странице входа.
    """
    try:
        result = await telegram_auth_service.send_code(request.phone)
        return result
    except RateLimitError as e:
        raise _handle_rate_limit_error(e)
    except Exception as e:
        error_msg = str(e)
        if "FLOOD_WAIT" in error_msg or "UNAVAILABLE" in error_msg:
            limit_info = rate_limiter.parse_error(e)
            limit_info.phone = request.phone
            await rate_limiter.record_limit(request.phone, limit_info)
            raise _handle_rate_limit_error(RateLimitError(limit_info))
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/login", response_model=Union[TokenResponse, TwoFARequiredResponse])
async def login_public(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Авторизация через Telegram (публичный endpoint).
    Возвращает JWT токен при успешной авторизации.
    При необходимости 2FA возвращает status: 2fa_required.
    """
    try:
        # Авторизуемся в Telegram
        telegram_user = await telegram_auth_service.sign_in_public(
            phone=request.phone,
            code=request.code,
            password=request.password
        )
        
        if telegram_user.get("status") == "2fa_required":
            return TwoFARequiredResponse()
        
        # Получаем данные Telegram пользователя
        telegram_id = telegram_user.get("telegram_id")
        first_name = telegram_user.get("first_name", "")
        username = telegram_user.get("username")
        phone = telegram_user.get("phone")
        session_string = telegram_user.get("session_string")
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Не удалось получить данные пользователя Telegram")
        
        # Ищем или создаём пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            # Создаём нового пользователя
            user = User(
                id=uuid.uuid4(),
                email=f"telegram_{telegram_id}@sattva.local",
                full_name=first_name or username or f"User {telegram_id}",
                telegram_id=telegram_id,
                telegram_username=username,
                status="pending",  # Новые пользователи ожидают одобрения
                role="user"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Обновляем данные пользователя
            if username:
                user.telegram_username = username
            if first_name:
                user.full_name = first_name
            db.commit()
        
        # Сохраняем или обновляем TelegramAccount для стриминга
        if session_string and phone:
            encrypted_session = encryption_service.encrypt(session_string)
            
            # Ищем существующий аккаунт по telegram_id или phone
            telegram_account = db.query(TelegramAccount).filter(
                (TelegramAccount.tg_user_id == telegram_id) | 
                (TelegramAccount.phone == phone)
            ).first()
            
            if telegram_account:
                # Обновляем существующий аккаунт
                telegram_account.encrypted_session = encrypted_session
                telegram_account.phone = phone
                telegram_account.tg_user_id = telegram_id
                telegram_account.first_name = first_name
                telegram_account.username = username
                telegram_account.user_id = user.id  # Привязываем к текущему пользователю
            else:
                # Создаём новый аккаунт
                telegram_account = TelegramAccount(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    phone=phone,
                    encrypted_session=encrypted_session,
                    tg_user_id=telegram_id,
                    first_name=first_name,
                    username=username,
                )
                db.add(telegram_account)
            
            db.commit()
        
        # Создаём JWT токен с ролью пользователя
        role_value = user.role.value if hasattr(user.role, 'value') else str(user.role) if user.role else None
        access_token = create_access_token(
            data={"sub": str(user.id), "role": role_value},
            expires_delta=timedelta(minutes=30)
        )
        
        return TokenResponse(access_token=access_token)
    
    except RateLimitError as e:
        raise _handle_rate_limit_error(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        if "PHONE_CODE_EXPIRED" in error_msg:
            raise HTTPException(status_code=400, detail="Код истёк. Запросите новый код.")
        elif "PHONE_CODE_INVALID" in error_msg:
            raise HTTPException(status_code=400, detail="Неверный код. Проверьте и попробуйте снова.")
        elif "PASSWORD_HASH_INVALID" in error_msg:
            raise HTTPException(status_code=400, detail="Неверный пароль 2FA.")
        elif "FLOOD_WAIT" in error_msg:
            limit_info = rate_limiter.parse_error(e)
            limit_info.phone = request.phone
            await rate_limiter.record_limit(request.phone, limit_info)
            raise _handle_rate_limit_error(RateLimitError(limit_info))
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/limit-status/{phone}")
async def check_limit_status_public(phone: str):
    """Проверить статус лимита для номера телефона (публичный endpoint)"""
    limit_info = await rate_limiter.check_limit(phone)
    if limit_info and limit_info.is_active:
        return {
            "limited": True,
            "type": limit_info.type.value,
            "message": limit_info.message,
            "remaining_seconds": limit_info.remaining_seconds,
            "retry_after": limit_info.retry_after.isoformat() if limit_info.retry_after else None,
        }
    return {"limited": False}
