"""
Telegram Bot Authentication Utilities

Утилиты для аутентификации пользователей в Telegram боте:
- get_or_create_user - получить или создать пользователя из Telegram
"""

from typing import Optional
import logging

from telegram import User as TelegramUser
from sqlalchemy.orm import Session

from src.models.user import User, UserStatus, UserRole
from database import SessionLocal

logger = logging.getLogger(__name__)


async def get_or_create_user(telegram_user: TelegramUser, db: Optional[Session] = None) -> User:
    """
    Получить существующего пользователя или создать нового из Telegram.
    
    Args:
        telegram_user: Telegram User объект из update.effective_user
        db: SQLAlchemy session (опционально, создается автоматически если не передан)
    
    Returns:
        User объект из БД
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        # Попытаться найти существующего пользователя по telegram_id
        user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
        
        if user:
            # Обновить данные профиля при каждом взаимодействии
            updated = False
            
            full_name = _build_full_name(telegram_user.first_name, telegram_user.last_name)
            if user.full_name != full_name:
                user.full_name = full_name
                updated = True
            
            if telegram_user.username and user.telegram_username != telegram_user.username:
                user.telegram_username = telegram_user.username
                updated = True
            
            if updated:
                db.commit()
                db.refresh(user)
                logger.info(f"Updated user profile for telegram_id={telegram_user.id}")
            
            return user
        
        # Создать нового пользователя
        user = User(
            telegram_id=telegram_user.id,
            telegram_username=telegram_user.username,
            full_name=_build_full_name(telegram_user.first_name, telegram_user.last_name),
            email=None,  # Telegram-only пользователь
            status=UserStatus.PENDING,  # По умолчанию pending, админ должен одобрить
            role=UserRole.USER,  # Обычный пользователь по умолчанию
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(
            f"Created new user from Telegram: "
            f"telegram_id={telegram_user.id}, "
            f"username={telegram_user.username}, "
            f"status={user.status.value}"
        )
        
        return user
        
    except Exception as e:
        if close_db:
            db.rollback()
        logger.error(f"Error in get_or_create_user: {e}", exc_info=True)
        raise
    
    finally:
        if close_db:
            db.close()


def _build_full_name(first_name: Optional[str], last_name: Optional[str]) -> str:
    """Построить full_name из имени и фамилии."""
    parts = []
    if first_name:
        parts.append(first_name)
    if last_name:
        parts.append(last_name)
    
    return " ".join(parts) if parts else "Telegram User"
