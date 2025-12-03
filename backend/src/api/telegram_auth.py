from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from src.services.telegram_auth import telegram_auth_service, RateLimitError
from src.services.telegram_rate_limiter import rate_limiter
from api.auth import get_current_user
from src.models.user import User
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.telegram import TelegramAccount
from typing import List
import uuid

router = APIRouter()

class PhoneRequest(BaseModel):
    phone: str

class LoginRequest(BaseModel):
    phone: str
    code: str
    password: str | None = None

class TelegramAccountResponse(BaseModel):
    id: uuid.UUID
    phone: str
    first_name: str | None
    username: str | None
    photo_url: str | None

    model_config = ConfigDict(from_attributes=True)


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


@router.get("/accounts", response_model=List[TelegramAccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    accounts = db.query(TelegramAccount).filter(TelegramAccount.user_id == current_user.id).all()
    return accounts


@router.get("/limit-status/{phone}")
async def check_limit_status(phone: str, current_user: User = Depends(get_current_user)):
    """Проверить статус лимита для номера телефона"""
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


@router.get("/limit-stats")
async def get_limit_stats(current_user: User = Depends(get_current_user)):
    """Получить статистику лимитов (для админов)"""
    # TODO: Добавить проверку прав админа
    return await rate_limiter.get_global_status()


@router.post("/send-code")
async def send_code(request: PhoneRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await telegram_auth_service.send_code(request.phone)
        return result
    except RateLimitError as e:
        raise _handle_rate_limit_error(e)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/resend-code")
async def resend_code(request: PhoneRequest, current_user: User = Depends(get_current_user)):
    """Resend code via alternative method (SMS/call instead of app notification)"""
    try:
        result = await telegram_auth_service.resend_code(request.phone)
        return result
    except RateLimitError as e:
        raise _handle_rate_limit_error(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        if "FLOOD_WAIT" in error_msg or "UNAVAILABLE" in error_msg:
            # Попробуем распарсить как лимит
            limit_info = rate_limiter.parse_error(e)
            limit_info.phone = request.phone
            await rate_limiter.record_limit(request.phone, limit_info)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit",
                    "type": limit_info.type.value,
                    "message": limit_info.message,
                    "wait_seconds": limit_info.wait_seconds,
                }
            )
        raise HTTPException(status_code=400, detail=error_msg)

@router.post("/login")
async def login(request: LoginRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await telegram_auth_service.sign_in(
            user_id=current_user.id,
            phone=request.phone,
            code=request.code,
            password=request.password
        )
        return result
    except RateLimitError as e:
        raise _handle_rate_limit_error(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        # Handle specific Telegram errors with user-friendly messages
        if "PHONE_CODE_EXPIRED" in error_msg:
            raise HTTPException(status_code=400, detail="Code expired. Please request a new code.")
        elif "PHONE_CODE_INVALID" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid code. Please check and try again.")
        elif "FLOOD_WAIT" in error_msg:
            limit_info = rate_limiter.parse_error(e)
            limit_info.phone = request.phone
            await rate_limiter.record_limit(request.phone, limit_info)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit",
                    "type": limit_info.type.value,
                    "message": limit_info.message,
                    "wait_seconds": limit_info.wait_seconds,
                }
            )
        raise HTTPException(status_code=500, detail=error_msg)
