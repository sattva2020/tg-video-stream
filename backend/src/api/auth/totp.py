"""
TOTP (2FA) эндпоинты для админов.
"""
import os

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from src.models.user import User
from api.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/totp", tags=["2FA"])


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPDisableRequest(BaseModel):
    code: str | None = None


def _get_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret)


@router.post("/setup", response_model=TOTPSetupResponse)
def setup_totp(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Выдаёт секрет и otpauth URI. До верификации 2FA не активируется."""
    secret = pyotp.random_base32()
    issuer = os.getenv("TOTP_ISSUER", "TelegramBroadcast")
    label = current_user.email or str(current_user.id)
    otpauth_url = _get_totp(secret).provisioning_uri(name=label, issuer_name=issuer)

    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"secret": secret, "otpauth_url": otpauth_url}


@router.post("/verify")
def verify_totp(
    payload: TOTPVerifyRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Активирует 2FA после успешного ввода кода."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP is not initialized")

    totp = _get_totp(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"status": "enabled"}


@router.post("/disable")
def disable_totp(
    payload: TOTPDisableRequest | None = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Отключает 2FA. Опционально можно потребовать текущий код."""
    if current_user.totp_enabled and payload and payload.code:
        totp = _get_totp(current_user.totp_secret)
        if not totp.verify(payload.code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"status": "disabled"}
