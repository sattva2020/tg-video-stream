"""
Telegram Sessions API endpoints.

Эндпоинты для управления Telegram сессиями:
- Просмотр списка сессий и их здоровья
- Ручной refresh сессий
- Бэкап и восстановление сессий
- Проверка здоровья сессий
- Настройка TOTP 2FA для автоматического refresh
- Отправка тестовых алертов для проверки webhook интеграций

Создано в рамках Session Management Automation (spec 002).
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.telegram import TelegramAccount, SessionHealthStatus
from api.auth import get_current_user
from src.services.telegram_session_service import get_telegram_session_service
from src.services.telegram_session_monitor import get_telegram_session_monitor
from src.services.encryption import encryption_service
from src.celery_app import celery_app
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram/sessions", tags=["Telegram Sessions"])


# =============================================================================
# Pydantic Models
# =============================================================================

class TelegramSessionResponse(BaseModel):
    """Модель ответа для Telegram сессии."""
    id: uuid.UUID
    user_id: uuid.UUID
    phone: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    tg_user_id: Optional[int] = None
    is_active: bool

    # Session health fields
    session_health_status: Optional[str] = None
    last_health_check: Optional[datetime] = None
    session_expires_at: Optional[datetime] = None
    auto_refresh_enabled: bool
    refresh_before_expires_hours: int
    last_refreshed_at: Optional[datetime] = None
    refresh_error_message: Optional[str] = None

    # Real-time health (from monitor)
    is_healthy: Optional[bool] = None
    health_status: Optional[str] = None
    consecutive_failures: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SessionRefreshResponse(BaseModel):
    """Модель ответа для операции refresh."""
    success: bool
    message: str
    session_expires_at: Optional[datetime] = None


class SessionBackupResponse(BaseModel):
    """Модель ответа для операции бэкапа."""
    success: bool
    message: str
    backup_path: Optional[str] = None


class SessionRestoreRequest(BaseModel):
    """Модель запроса для восстановления сессии."""
    backup_path: str


class SessionHealthResponse(BaseModel):
    """Модель ответа для проверки здоровья сессии."""
    account_id: str
    is_healthy: bool
    health_status: str
    last_check: datetime
    consecutive_failures: int
    session_expires_at: Optional[datetime] = None
    time_until_expiry_seconds: Optional[int] = None
    last_failure_type: Optional[str] = None
    last_error_message: Optional[str] = None


class TOTPSetupResponse(BaseModel):
    """Модель ответа для настройки TOTP."""
    secret: str
    otpauth_url: str


class TOTPVerifyRequest(BaseModel):
    """Модель запроса для верификации TOTP кода."""
    code: str


class TOTPDisableRequest(BaseModel):
    """Модель запроса для отключения TOTP."""
    code: str | None = None


class SessionConfigResponse(BaseModel):
    """Модель ответа для конфигурации сессии."""
    account_id: uuid.UUID
    auto_refresh_enabled: bool
    refresh_before_expires_hours: int
    phone: str
    username: Optional[str] = None


class UpdateSessionConfigRequest(BaseModel):
    """Модель запроса для обновления конфигурации сессии."""
    auto_refresh_enabled: bool | None = None
    refresh_before_expires_hours: int | None = Field(None, ge=1, le=168, description="Hours before expiration to refresh (1-168)")


class TestAlertResponse(BaseModel):
    """Модель ответа для тестового алерта."""
    success: bool
    message: str
    event_id: str
    tasks_enqueued: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=List[TelegramSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список всех Telegram сессий текущего пользователя.

    Returns:
        List[TelegramSessionResponse]: Список сессий с информацией о здоровье
    """
    # Query all Telegram accounts for current user
    accounts = db.query(TelegramAccount).filter(
        TelegramAccount.user_id == current_user.id
    ).all()

    # Enrich with real-time health from monitor
    monitor = get_telegram_session_monitor()
    result = []

    for account in accounts:
        account_dict = {
            "id": account.id,
            "user_id": account.user_id,
            "phone": account.phone,
            "username": account.username,
            "first_name": account.first_name,
            "tg_user_id": account.tg_user_id,
            "is_active": account.is_active,
            "session_health_status": account.session_health_status.value if account.session_health_status else None,
            "last_health_check": account.last_health_check,
            "session_expires_at": account.session_expires_at,
            "auto_refresh_enabled": account.auto_refresh_enabled,
            "refresh_before_expires_hours": account.refresh_before_expires_hours or 24,
            "last_refreshed_at": account.last_refreshed_at,
            "refresh_error_message": account.refresh_error_message,
        }

        # Get real-time health from monitor
        try:
            health = monitor.get_account_health(str(account.id))
            if health:
                account_dict["is_healthy"] = health.is_healthy
                account_dict["health_status"] = health.health_status
                account_dict["consecutive_failures"] = health.consecutive_failures
        except Exception:
            # Monitor not available - skip real-time enrichment
            pass

        result.append(TelegramSessionResponse(**account_dict))

    return result


@router.get("/{account_id}", response_model=TelegramSessionResponse)
def get_session(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить детальную информацию о Telegram сессии.

    Args:
        account_id: UUID аккаунта

    Returns:
        TelegramSessionResponse: Детальная информация о сессии
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    account_dict = {
        "id": account.id,
        "user_id": account.user_id,
        "phone": account.phone,
        "username": account.username,
        "first_name": account.first_name,
        "tg_user_id": account.tg_user_id,
        "is_active": account.is_active,
        "session_health_status": account.session_health_status.value if account.session_health_status else None,
        "last_health_check": account.last_health_check,
        "session_expires_at": account.session_expires_at,
        "auto_refresh_enabled": account.auto_refresh_enabled,
        "refresh_before_expires_hours": account.refresh_before_expires_hours or 24,
        "last_refreshed_at": account.last_refreshed_at,
        "refresh_error_message": account.refresh_error_message,
    }

    # Get real-time health from monitor
    monitor = get_telegram_session_monitor()
    try:
        health = monitor.get_account_health(str(account_id))
        if health:
            account_dict["is_healthy"] = health.is_healthy
            account_dict["health_status"] = health.health_status
            account_dict["consecutive_failures"] = health.consecutive_failures
    except Exception:
        pass

    return TelegramSessionResponse(**account_dict)


@router.post("/{account_id}/refresh", response_model=SessionRefreshResponse)
def refresh_session(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ручной refresh Telegram сессии.

    Args:
        account_id: UUID аккаунта

    Returns:
        SessionRefreshResponse: Результат операции refresh
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Perform refresh
    service = get_telegram_session_service()
    try:
        import asyncio
        asyncio.run(service.refresh_session(str(account_id), db))

        # Refresh account from DB to get updated values
        db.refresh(account)

        return SessionRefreshResponse(
            success=True,
            message="Session refreshed successfully",
            session_expires_at=account.session_expires_at
        )
    except Exception as e:
        return SessionRefreshResponse(
            success=False,
            message=f"Failed to refresh session: {str(e)}"
        )


@router.post("/{account_id}/backup", response_model=SessionBackupResponse)
def backup_session(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать бэкап Telegram сессии.

    Args:
        account_id: UUID аккаунта

    Returns:
        SessionBackupResponse: Результат операции бэкапа
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Perform backup
    service = get_telegram_session_service()
    try:
        backup_path = service.backup_session(str(account_id), db)

        return SessionBackupResponse(
            success=True,
            message=f"Session backed up to {backup_path}",
            backup_path=backup_path
        )
    except Exception as e:
        return SessionBackupResponse(
            success=False,
            message=f"Failed to backup session: {str(e)}"
        )


@router.post("/{account_id}/restore", response_model=SessionRefreshResponse)
def restore_session(
    account_id: uuid.UUID,
    restore_request: SessionRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Восстановить Telegram сессию из бэкапа.

    Args:
        account_id: UUID аккаунта
        restore_request: Путь к файлу бэкапа

    Returns:
        SessionRefreshResponse: Результат операции восстановления
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Perform restore
    service = get_telegram_session_service()
    try:
        import asyncio
        asyncio.run(service.restore_session(str(account_id), restore_request.backup_path, db))

        # Refresh account from DB to get updated values
        db.refresh(account)

        return SessionRefreshResponse(
            success=True,
            message="Session restored successfully",
            session_expires_at=account.session_expires_at
        )
    except Exception as e:
        return SessionRefreshResponse(
            success=False,
            message=f"Failed to restore session: {str(e)}"
        )


@router.get("/{account_id}/health", response_model=SessionHealthResponse)
def get_session_health(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить текущий статус здоровья Telegram сессии.

    Args:
        account_id: UUID аккаунта

    Returns:
        SessionHealthResponse: Детальная информация о здоровье сессии
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Get health from monitor
    monitor = get_telegram_session_monitor()
    try:
        import asyncio
        health = asyncio.run(monitor.check_account_health(str(account_id)))

        return SessionHealthResponse(
            account_id=health.account_id,
            is_healthy=health.is_healthy,
            health_status=health.health_status,
            last_check=health.last_check,
            consecutive_failures=health.consecutive_failures,
            session_expires_at=health.session_expires_at,
            time_until_expiry_seconds=health.time_until_expiry_seconds,
            last_failure_type=health.last_failure_type,
            last_error_message=health.last_error_message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check session health: {str(e)}"
        )


@router.get("/{account_id}/config", response_model=SessionConfigResponse)
def get_session_config(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить конфигурацию автоматического refresh для Telegram сессии.

    Args:
        account_id: UUID аккаунта

    Returns:
        SessionConfigResponse: Текущая конфигурация сессии
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    return SessionConfigResponse(
        account_id=account.id,
        auto_refresh_enabled=account.auto_refresh_enabled,
        refresh_before_expires_hours=account.refresh_before_expires_hours or 24,
        phone=account.phone,
        username=account.username
    )


@router.put("/{account_id}/config", response_model=SessionConfigResponse)
def update_session_config(
    account_id: uuid.UUID,
    config: UpdateSessionConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить конфигурацию автоматического refresh для Telegram сессии.

    Позволяет настроить параметры автоматического refresh и rotation для
    распределения нагрузки между несколькими аккаунтами.

    Args:
        account_id: UUID аккаунта
        config: Новые параметры конфигурации

    Returns:
        SessionConfigResponse: Обновленная конфигурация сессии
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Update fields if provided
    if config.auto_refresh_enabled is not None:
        account.auto_refresh_enabled = config.auto_refresh_enabled

    if config.refresh_before_expires_hours is not None:
        account.refresh_before_expires_hours = config.refresh_before_expires_hours

    # Save changes
    db.add(account)
    db.commit()
    db.refresh(account)

    return SessionConfigResponse(
        account_id=account.id,
        auto_refresh_enabled=account.auto_refresh_enabled,
        refresh_before_expires_hours=account.refresh_before_expires_hours or 24,
        phone=account.phone,
        username=account.username
    )


# =============================================================================
# TOTP 2FA Endpoints
# =============================================================================

def _get_totp(secret: str) -> pyotp.TOTP:
    """Создать TOTP объект из секрета."""
    return pyotp.TOTP(secret)


@router.post("/{account_id}/2fa/setup", response_model=TOTPSetupResponse)
def setup_totp(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Настроить TOTP 2FA для Telegram аккаунта.

    Генерирует секрет и otpauth URI для сканирования QR кода.
    Секрет сохраняется зашифрованным, но 2FA не активируется до верификации.

    Args:
        account_id: UUID аккаунта

    Returns:
        TOTPSetupResponse: Секрет и otpauth URL для настройки authenticator app
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # Generate TOTP secret
    secret = pyotp.random_base32()
    issuer = os.getenv("TOTP_ISSUER", "TelegramBroadcast")
    label = account.phone or str(account.id)
    otpauth_url = _get_totp(secret).provisioning_uri(name=label, issuer_name=issuer)

    # Encrypt and store the secret (2FA not yet enabled - requires verification)
    try:
        encrypted_secret = encryption_service.encrypt_totp_secret(secret)
        account.totp_secret = encrypted_secret
        db.add(account)
        db.commit()
        db.refresh(account)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid TOTP secret: {str(e)}")

    return {"secret": secret, "otpauth_url": otpauth_url}


@router.post("/{account_id}/2fa/verify")
def verify_totp(
    account_id: uuid.UUID,
    payload: TOTPVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Верифицировать TOTP код и активировать 2FA для автоматического refresh.

    После успешной верификации, система сможет автоматически использовать
    TOTP коды при refresh сессии Telegram.

    Args:
        account_id: UUID аккаунта
        payload: TOTP код из authenticator app

    Returns:
        Статус активации 2FA
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    if not account.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP is not initialized. Call /2fa/setup first.")

    # Decrypt secret and verify code
    try:
        decrypted_secret = encryption_service.decrypt_totp_secret(account.totp_secret)
        totp = _get_totp(decrypted_secret)

        if not totp.verify(payload.code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

        # 2FA is now enabled (totp_secret exists and is verified)
        db.add(account)
        db.commit()
        db.refresh(account)

        return {"status": "enabled", "message": "2FA successfully enabled for automatic session refresh"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt TOTP secret: {str(e)}")


@router.post("/{account_id}/2fa/disable")
def disable_totp(
    account_id: uuid.UUID,
    payload: TOTPDisableRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отключить TOTP 2FA для Telegram аккаунта.

    Опционально требует текущий TOTP код для подтверждения отключения.

    Args:
        account_id: UUID аккаунта
        payload: Опциональный TOTP код для подтверждения

    Returns:
        Статус отключения 2FA
    """
    # Verify ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    # If 2FA is enabled and code is provided, verify it
    if account.totp_secret and payload and payload.code:
        try:
            decrypted_secret = encryption_service.decrypt_totp_secret(account.totp_secret)
            totp = _get_totp(decrypted_secret)

            if not totp.verify(payload.code, valid_window=1):
                raise HTTPException(status_code=401, detail="Invalid TOTP code")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Failed to decrypt TOTP secret: {str(e)}")

    # Remove TOTP secret
    account.totp_secret = None
    db.add(account)
    db.commit()
    db.refresh(account)

    return {"status": "disabled", "message": "2FA successfully disabled"}


# =============================================================================
# Test Alert Endpoint
# =============================================================================

def _enqueue_process_event(payload: Dict, *, delay_sec: int = 0) -> bool:
    """Кладёт задачу в очередь или логирует, если Celery недоступен."""
    if celery_app:
        try:
            celery_app.send_task(
                "notifications.process_event",
                args=[payload],
                queue=settings.NOTIFICATIONS_QUEUE,
                countdown=delay_sec,
            )
            return True
        except Exception:
            logger.exception("Failed to enqueue notification task")
            return False
    logger.warning("Celery app not configured; skipping enqueue", extra={"payload": payload})
    return False


@router.post("/test-alert", response_model=TestAlertResponse)
def send_test_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправить тестовый алерт для проверки webhook интеграций.

    Создаёт тестовое уведомление о здоровье сессии и отправляет его через
    систему уведомлений. Полезно для проверки корректности настройки
    webhook интеграций и получения алертов.

    Returns:
        TestAlertResponse: Результат отправки тестового алерта
    """
    event_id = str(uuid.uuid4())

    # Build test event payload
    payload = {
        "event_id": event_id,
        "severity": "info",
        "tags": {
            "source": "telegram_sessions",
            "event_type": "health_alert_test",
            "user_id": str(current_user.id),
        },
        "host": "telegram-session-service",
        "context": {
            "test": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "This is a test alert for Telegram session health monitoring",
        },
        "subject": "Test Alert: Telegram Session Health Monitoring",
        "body": (
            "This is a test notification from the Telegram Session Health Monitoring system.\n\n"
            f"User ID: {current_user.id}\n"
            f"Test sent at: {datetime.now(timezone.utc).isoformat()}\n\n"
            "If you receive this message, your webhook integration is working correctly."
        ),
    }

    # Enqueue notification task
    enqueued = 1 if _enqueue_process_event(payload) else 0

    return TestAlertResponse(
        success=enqueued > 0,
        message="Test alert sent to notification system" if enqueued > 0 else "Failed to enqueue test alert",
        event_id=event_id,
        tasks_enqueued=enqueued,
    )
