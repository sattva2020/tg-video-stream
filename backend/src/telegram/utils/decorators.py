"""
Telegram Bot Decorators

Декораторы для команд Telegram бота:
- admin_only - проверка прав администратора
- with_error_handling - обработка ошибок
"""

from functools import wraps
import logging
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from src.telegram.utils.auth import get_or_create_user

logger = logging.getLogger(__name__)


def admin_only(func: Callable):
    """
    Декоратор для ограничения команды только администраторами.
    
    Проверяет роль пользователя и отклоняет запрос если пользователь не админ.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_or_create_user(update.effective_user)
        
        # Проверить права админа
        if not user.is_admin:
            await update.message.reply_text(
                "❌ Эта команда доступна только администраторам"
            )
            logger.warning(
                f"User {user.id} (role={user.role}) attempted to use admin-only command: "
                f"{update.message.text}"
            )
            return
        
        # Выполнить команду
        return await func(update, context)
    
    return wrapper


def with_error_handling(func: Callable):
    """
    Декоратор для обработки ошибок в командах.
    
    Перехватывает исключения и отправляет пользователю понятное сообщение об ошибке.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            error_message = f"❌ Произошла ошибка: {str(e)}"
            
            try:
                await update.message.reply_text(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
            
            logger.error(
                f"Error in command {func.__name__}: {e}",
                exc_info=True,
                extra={
                    "user_id": update.effective_user.id if update.effective_user else None,
                    "chat_id": update.effective_chat.id if update.effective_chat else None,
                    "message": update.message.text if update.message else None,
                }
            )
            
            raise
    
    return wrapper
