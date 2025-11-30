"""
Email/Password аутентификация: регистрация, логин, сброс пароля, верификация email.
"""
import os
import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from src.models.user import User
from services.auth_service import auth_service, check_password_policy, is_password_pwned
from src.services.activity_service import ActivityService
from tasks.notifications import notify_admins_async
from .dependencies import make_rate_limit_dep, _check_rate_limit
from .utils import format_auth_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email/Password Auth"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str


class EmailVerifyRequest(BaseModel):
    email: EmailStr


class EmailVerifyConfirm(BaseModel):
    token: str


# ============================================================================
# Registration
# ============================================================================

@router.post("/register")
def register_user(
    request: RegisterRequest,
    fastapi_request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Регистрация нового пользователя по email/password.
    Новые пользователи получают статус 'pending' и ждут одобрения админа.
    """
    existing_user = db.query(User).filter(User.email == request.email).first()
    
    if existing_user:
        # Если есть Google-only пользователь — предлагаем связать аккаунты
        if existing_user.google_id and not existing_user.hashed_password:
            detail = format_auth_error(
                code='conflict',
                hint='link_account',
                message_key='auth.google_account_exists',
                req=fastapi_request,
            )
            detail['link_required'] = True
            raise HTTPException(status_code=409, detail=detail)
        
        detail = format_auth_error(
            code='conflict',
            hint='email_exists',
            message_key='auth.email_registered',
            req=fastapi_request,
        )
        raise HTTPException(status_code=409, detail=detail)

    hashed = auth_service.hash_password(request.password)
    new_user = User(
        google_id=None,
        email=request.email,
        hashed_password=hashed,
        status='pending'
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Логируем событие регистрации
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="user_registered",
        message=f"Новый пользователь зарегистрирован: {new_user.email}",
        user_id=new_user.id,
        user_email=new_user.email,
        details={"method": "email_password", "status": "pending"}
    )
    
    # Уведомляем админов
    try:
        notify_admins_async(new_user.id)
    except Exception:
        logger.exception("Failed to enqueue admin notification")
    
    # Генерируем токен верификации email
    verify_token = auth_service.generate_email_verification_token(new_user.email)
    
    if not os.getenv("SMTP_HOST"):
        # Dev mode: возвращаем токен для тестов
        return {
            "status": "pending",
            "message": "Account created and awaiting administrator approval",
            "dev_verification_token": verify_token
        }
    else:
        auth_service.send_email_verification(new_user.email, verify_token)
    
    return {
        "status": "pending",
        "message": "Account created and awaiting administrator approval"
    }


# ============================================================================
# Login
# ============================================================================

@router.post("/login")
async def login_user(
    fastapi_request: Request,
    db: Session = Depends(get_db),
    _rl=Depends(make_rate_limit_dep('login'))
):
    """
    Логин пользователя по email/password.
    Поддерживает JSON и form-urlencoded (OAuth2-style).
    """
    # Парсим запрос
    content_type = fastapi_request.headers.get('content-type', '')
    parsed = None
    
    try:
        if 'application/json' in content_type:
            parsed = await fastapi_request.json()
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            form = await fastapi_request.form()
            parsed = {
                'email': form.get('username') or form.get('email'),
                'password': form.get('password')
            }
        else:
            # Пробуем JSON, потом form
            try:
                parsed = await fastapi_request.json()
            except Exception:
                form = await fastapi_request.form()
                parsed = {
                    'email': form.get('username') or form.get('email'),
                    'password': form.get('password')
                }
    except Exception as e:
        raise HTTPException(status_code=422, detail='Invalid request payload')

    # Валидация через Pydantic
    try:
        login_data = LoginRequest.model_validate(parsed)
    except Exception as e:
        raise HTTPException(status_code=422, detail='Invalid login payload')

    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Проверка статуса аккаунта
    if getattr(user, 'status', 'approved') != 'approved':
        status_val = getattr(user, 'status', 'pending')
        if status_val == 'pending':
            detail = format_auth_error(
                code='pending',
                hint='contact_admin',
                message_key='auth.account_pending',
                req=fastapi_request,
            )
        else:
            detail = format_auth_error(
                code='rejected',
                hint='contact_admin',
                message_key='auth.account_rejected',
                req=fastapi_request,
            )
        raise HTTPException(status_code=403, detail=detail)
    
    if not auth_service.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


# ============================================================================
# Password Reset
# ============================================================================

@router.post("/password-reset/request")
def password_reset_request(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
    fastapi_request: Request = None,
    _rl=Depends(make_rate_limit_dep('password-reset'))
):
    """
    Запрос на сброс пароля. Отправляет email с токеном.
    """
    client_ip = "unknown"
    if fastapi_request and fastapi_request.client:
        client_ip = fastapi_request.client.host
    
    if not _check_rate_limit(client_ip, 'password-reset'):
        raise HTTPException(status_code=429, detail="Too many password reset requests, try later.")

    user = db.query(User).filter(User.email == data.email).first()
    
    # Всегда OK для предотвращения user enumeration
    if not user:
        return {"status": "ok"}

    token = auth_service.generate_password_reset_token(data.email)
    
    # DEV-mode: возвращаем токен если SMTP не настроен
    if not os.getenv("SMTP_HOST"):
        return {"status": "ok", "token": token}

    auth_service.send_password_reset_email(data.email, token)
    return {"status": "ok"}


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Подтверждение сброса пароля с новым паролем.
    """
    email = auth_service.verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Валидация сложности пароля
    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = auth_service.hash_password(data.password)
    db.commit()
    db.refresh(user)
    
    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token}


# ============================================================================
# Email Verification
# ============================================================================

@router.post("/email-verify/request")
def email_verify_request(body: EmailVerifyRequest, db: Session = Depends(get_db)):
    """
    Запрос на верификацию email.
    """
    user = db.query(User).filter(User.email == body.email).first()
    
    if not user:
        return {"status": "ok"}
    
    token = auth_service.generate_email_verification_token(body.email)
    
    if not os.getenv("SMTP_HOST"):
        return {"status": "ok", "token": token}
    
    auth_service.send_email_verification(body.email, token)
    return {"status": "ok"}


@router.post("/email-verify/confirm")
def email_verify_confirm(body: EmailVerifyConfirm, db: Session = Depends(get_db)):
    """
    Подтверждение верификации email.
    """
    email = auth_service.verify_email_verification_token(body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.email_verified = True
    db.commit()
    db.refresh(user)
    
    return {"status": "ok"}
