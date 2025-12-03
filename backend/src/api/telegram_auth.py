from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from src.services.telegram_auth import telegram_auth_service, RateLimitError
from src.services.telegram_rate_limiter import rate_limiter
from src.services.encryption import encryption_service
from api.auth import get_current_user
from src.models.user import User
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.telegram import TelegramAccount
from pyrogram import Client
from typing import List, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

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


class DialogInfo(BaseModel):
    """Информация о диалоге (канал/группа/чат)"""
    id: int
    title: str
    type: str  # 'channel', 'supergroup', 'group', 'private'
    username: Optional[str] = None
    members_count: Optional[int] = None
    photo_url: Optional[str] = None
    is_creator: bool = False
    is_admin: bool = False


@router.get("/accounts/{account_id}/dialogs", response_model=List[DialogInfo])
async def get_account_dialogs(
    account_id: uuid.UUID,
    filter_type: Optional[str] = None,  # 'channels', 'groups', 'all'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список каналов и групп для указанного Telegram аккаунта.
    
    filter_type:
    - 'channels' - только каналы
    - 'groups' - только группы (включая супергруппы)
    - 'all' или None - все диалоги где пользователь может стримить
    """
    # Проверяем, что аккаунт принадлежит текущему пользователю
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    
    if not account.encrypted_session:
        raise HTTPException(status_code=400, detail="Account session not found. Please re-authenticate.")
    
    # Расшифровываем сессию
    try:
        session_string = encryption_service.decrypt(account.encrypted_session)
    except Exception as e:
        logger.error(f"Failed to decrypt session for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt session")
    
    dialogs = []
    
    try:
        # Создаём клиент из сохранённой сессии
        client = Client(
            name=f"dialogs_{account_id}",
            api_id=telegram_auth_service.api_id,
            api_hash=telegram_auth_service.api_hash,
            session_string=session_string,
            in_memory=True
        )
        
        async with client:
            async for dialog in client.get_dialogs(limit=100):
                chat = dialog.chat
                
                # Определяем тип чата
                if chat.type.value == "channel":
                    chat_type = "channel"
                elif chat.type.value == "supergroup":
                    chat_type = "supergroup"
                elif chat.type.value == "group":
                    chat_type = "group"
                else:
                    # Пропускаем личные чаты
                    continue
                
                # Применяем фильтр
                if filter_type == "channels" and chat_type != "channel":
                    continue
                if filter_type == "groups" and chat_type not in ("group", "supergroup"):
                    continue
                
                # Проверяем права администратора
                is_creator = False
                is_admin = False
                
                try:
                    # Для каналов и супергрупп проверяем права
                    if chat_type in ("channel", "supergroup"):
                        member = await client.get_chat_member(chat.id, "me")
                        is_creator = member.status.value == "owner"
                        is_admin = member.status.value in ("owner", "administrator")
                except Exception:
                    # Если не можем получить права, пропускаем
                    pass
                
                # Формируем URL фото
                photo_url = None
                if chat.photo:
                    # Можно добавить скачивание фото, но пока оставим None
                    pass
                
                dialogs.append(DialogInfo(
                    id=chat.id,
                    title=chat.title or chat.first_name or "Unknown",
                    type=chat_type,
                    username=chat.username,
                    members_count=chat.members_count,
                    photo_url=photo_url,
                    is_creator=is_creator,
                    is_admin=is_admin
                ))
        
        # Сортируем: сначала где админ, потом по названию
        dialogs.sort(key=lambda d: (not d.is_admin, d.title.lower()))
        
        return dialogs
        
    except Exception as e:
        logger.error(f"Failed to get dialogs for account {account_id}: {e}")
        error_msg = str(e)
        if "AUTH_KEY" in error_msg or "SESSION" in error_msg:
            raise HTTPException(status_code=401, detail="Session expired. Please re-authenticate your Telegram account.")
        raise HTTPException(status_code=500, detail=f"Failed to get dialogs: {error_msg}")


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
