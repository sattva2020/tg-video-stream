from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from src.services.telegram_auth import telegram_auth_service
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

@router.get("/accounts", response_model=List[TelegramAccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    accounts = db.query(TelegramAccount).filter(TelegramAccount.user_id == current_user.id).all()
    return accounts

@router.post("/send-code")
async def send_code(request: PhoneRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await telegram_auth_service.send_code(request.phone)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
            raise HTTPException(status_code=429, detail="Too many attempts. Please wait a few minutes.")
        raise HTTPException(status_code=500, detail=error_msg)
