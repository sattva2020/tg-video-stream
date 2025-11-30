"""
Связывание Google и Email/Password аккаунтов.
"""
import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from src.models.user import User
from services.auth_service import auth_service, check_password_policy, is_password_pwned

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/link-account", tags=["Account Linking"])


class LinkAccountRequest(BaseModel):
    email: EmailStr


class LinkAccountConfirm(BaseModel):
    token: str
    password: str


@router.post("/request")
def link_account_request(body: LinkAccountRequest, db: Session = Depends(get_db)):
    """
    Запрос на связывание аккаунтов.
    Для пользователей, зарегистрированных через Google, которые хотят добавить пароль.
    """
    user = db.query(User).filter(User.email == body.email).first()
    
    # Не раскрываем информацию о существовании email
    if not user or not user.google_id or user.hashed_password:
        return {"status": "ok"}

    token = auth_service.generate_link_account_token(body.email)

    # Dev-mode: возвращаем токен если SMTP не настроен
    if not os.getenv("SMTP_HOST"):
        return {"status": "ok", "token": token}

    auth_service.send_account_link_email(body.email, token)
    return {"status": "ok"}


@router.post("/confirm")
def link_account_confirm(body: LinkAccountConfirm, db: Session = Depends(get_db)):
    """
    Подтверждение связывания аккаунтов — установка пароля для Google-аккаунта.
    """
    email = auth_service.verify_link_account_token(body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Валидация политики паролей
    if not check_password_policy(body.password):
        raise HTTPException(
            status_code=400,
            detail="Password does not meet complexity requirements"
        )

    # Проверка на утечки паролей (если включено)
    if os.getenv("HIBP_ENABLED", "false").lower() == "true":
        if is_password_pwned(body.password):
            raise HTTPException(
                status_code=400,
                detail="Password is found in data leaks (choose another one)"
            )

    user.hashed_password = auth_service.hash_password(body.password)
    db.commit()
    db.refresh(user)

    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token}
