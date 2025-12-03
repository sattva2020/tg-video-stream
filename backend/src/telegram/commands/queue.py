"""
Queue Commands for Telegram Bot

Telegram команды для управления очередью воспроизведения:
- /queue - показать текущую очередь
- /vipqueue - показать статистику VIP очереди (только для админов)
- /clearqueue - очистить очередь (только для админов)
- /setmode - переключить режим очереди FIFO/PRIORITY (только для админов)
"""

from typing import Optional
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.services.unified_queue_service import (
    get_unified_queue_service,
    QueueMode,
)
from src.models.user import User, UserRole
from src.telegram.utils.auth import get_or_create_user
from src.telegram.utils.decorators import admin_only, with_error_handling

logger = logging.getLogger(__name__)

# Константы
QUEUE_PAGE_SIZE = 10
VIP_BADGE = "⭐"
ADMIN_BADGE = "👑"
NORMAL_BADGE = "🎵"


def _get_priority_badge(metadata: dict) -> str:
    """Получить badge для приоритета трека."""
    is_vip = metadata.get("is_vip", False)
    is_admin = metadata.get("is_admin", False)
    
    if is_vip:
        return VIP_BADGE
    elif is_admin:
        return ADMIN_BADGE
    else:
        return NORMAL_BADGE


def _format_duration(seconds: Optional[int]) -> str:
    """Форматировать длительность трека."""
    if seconds is None:
        return "∞"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


@with_error_handling
async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать текущую очередь.
    
    Usage: /queue [page]
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = update.effective_chat.id
    
    # Получить номер страницы из аргументов
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
            if page < 1:
                page = 1
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный номер страницы. Используйте: /queue [номер страницы]"
            )
            return
    
    # Получить очередь
    queue_service = get_unified_queue_service()
    mode = queue_service._get_mode(channel_id)
    
    offset = (page - 1) * QUEUE_PAGE_SIZE
    queue_info = await queue_service.get_all(
        channel_id=channel_id,
        limit=QUEUE_PAGE_SIZE,
        offset=offset,
    )
    
    if queue_info.total_items == 0:
        await update.message.reply_text("📭 Очередь пуста")
        return
    
    # Форматировать список треков
    total_pages = (queue_info.total_items + QUEUE_PAGE_SIZE - 1) // QUEUE_PAGE_SIZE
    
    header = f"📋 <b>Очередь воспроизведения</b>\n"
    header += f"Режим: {'🎯 Приоритетная' if mode == QueueMode.PRIORITY else '📑 FIFO'}\n"
    header += f"Всего треков: {queue_info.total_items}\n"
    header += f"Страница {page}/{total_pages}\n\n"
    
    lines = []
    for idx, item in enumerate(queue_info.items, start=offset + 1):
        # Добавить badge для priority режима
        badge = ""
        if mode == QueueMode.PRIORITY:
            badge = _get_priority_badge(item.metadata)
        
        duration = _format_duration(item.duration)
        
        # Формат: "1. ⭐ Track Name [3:45]"
        line = f"{idx}. {badge} <b>{item.title}</b> [{duration}]"
        lines.append(line)
    
    message = header + "\n".join(lines)
    
    # Добавить навигацию если есть другие страницы
    if total_pages > 1:
        nav_parts = []
        if page > 1:
            nav_parts.append(f"← /queue {page - 1}")
        if page < total_pages:
            nav_parts.append(f"/queue {page + 1} →")
        
        if nav_parts:
            message += "\n\n" + " | ".join(nav_parts)
    
    await update.message.reply_text(message, parse_mode="HTML")
    
    logger.info(
        f"User {user.id} viewed queue: channel={channel_id}, page={page}/{total_pages}"
    )


@admin_only
@with_error_handling
async def vipqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать статистику VIP очереди (только для админов).
    
    Usage: /vipqueue
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = update.effective_chat.id
    
    queue_service = get_unified_queue_service()
    mode = queue_service._get_mode(channel_id)
    
    # Проверить режим очереди
    if mode != QueueMode.PRIORITY:
        await update.message.reply_text(
            "⚠️ VIP очередь доступна только в режиме PRIORITY.\n"
            f"Текущий режим: {mode.value}\n\n"
            "Используйте /setmode priority для переключения."
        )
        return
    
    # Получить статистику
    stats = await queue_service.get_queue_stats(channel_id)
    
    message = "📊 <b>Статистика VIP очереди</b>\n\n"
    message += f"Всего треков: {stats['total']}\n"
    message += f"{VIP_BADGE} VIP: {stats['vip']}\n"
    message += f"{ADMIN_BADGE} Админы: {stats['admin']}\n"
    message += f"{NORMAL_BADGE} Обычные: {stats['normal']}\n\n"
    
    # Рассчитать процент VIP
    if stats['total'] > 0:
        vip_percent = (stats['vip'] / stats['total']) * 100
        admin_percent = (stats['admin'] / stats['total']) * 100
        normal_percent = (stats['normal'] / stats['total']) * 100
        
        message += f"Распределение:\n"
        message += f"VIP: {vip_percent:.1f}%\n"
        message += f"Админы: {admin_percent:.1f}%\n"
        message += f"Обычные: {normal_percent:.1f}%"
    
    await update.message.reply_text(message, parse_mode="HTML")
    
    logger.info(f"Admin {user.id} viewed VIP queue stats: channel={channel_id}")


@admin_only
@with_error_handling
async def clearqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Очистить очередь (только для админов).
    
    Usage: /clearqueue
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = update.effective_chat.id
    
    queue_service = get_unified_queue_service()
    
    # Очистить очередь
    count = await queue_service.clear(channel_id)
    
    if count == 0:
        await update.message.reply_text("📭 Очередь уже пуста")
    else:
        await update.message.reply_text(
            f"🗑️ Очередь очищена\n"
            f"Удалено треков: {count}"
        )
    
    logger.info(f"Admin {user.id} cleared queue: channel={channel_id}, items={count}")


@admin_only
@with_error_handling
async def setmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Переключить режим очереди (только для админов).
    
    Usage: /setmode <fifo|priority>
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = update.effective_chat.id
    
    # Проверить аргументы
    if not context.args or context.args[0].lower() not in ["fifo", "priority"]:
        await update.message.reply_text(
            "❌ Неверный режим. Используйте:\n"
            "/setmode fifo - обычная очередь (FIFO)\n"
            "/setmode priority - приоритетная очередь (VIP)"
        )
        return
    
    new_mode_str = context.args[0].lower()
    new_mode = QueueMode(new_mode_str)
    
    queue_service = get_unified_queue_service()
    current_mode = queue_service._get_mode(channel_id)
    
    # Проверить что режим не тот же самый
    if current_mode == new_mode:
        await update.message.reply_text(
            f"ℹ️ Текущий режим уже установлен: {new_mode.value}"
        )
        return
    
    # Проверить размер очереди
    size = await queue_service.get_size(channel_id)
    
    if size > 0:
        # Предупредить о необходимости миграции
        await update.message.reply_text(
            f"⚠️ <b>Внимание!</b>\n\n"
            f"В очереди {size} треков.\n"
            f"Смена режима с <b>{current_mode.value}</b> на <b>{new_mode.value}</b> "
            f"НЕ мигрирует существующие треки автоматически.\n\n"
            f"Рекомендации:\n"
            f"1. Очистить очередь: /clearqueue\n"
            f"2. Затем сменить режим: /setmode {new_mode_str}\n\n"
            f"Или используйте /migrate {current_mode.value} {new_mode.value} "
            f"для автоматической миграции.",
            parse_mode="HTML"
        )
        return
    
    # Установить новый режим
    await queue_service.set_mode(channel_id, new_mode)
    
    mode_names = {
        QueueMode.FIFO: "📑 FIFO (обычная очередь)",
        QueueMode.PRIORITY: "🎯 PRIORITY (приоритетная очередь)"
    }
    
    await update.message.reply_text(
        f"✅ Режим очереди изменен\n"
        f"Было: {mode_names[current_mode]}\n"
        f"Стало: {mode_names[new_mode]}"
    )
    
    logger.info(
        f"Admin {user.id} changed queue mode: "
        f"channel={channel_id}, {current_mode.value} -> {new_mode.value}"
    )


@admin_only
@with_error_handling
async def migrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Мигрировать очередь между режимами (только для админов).
    
    Usage: /migrate <from_mode> <to_mode>
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = update.effective_chat.id
    
    # Проверить аргументы
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверные аргументы. Используйте:\n"
            "/migrate fifo priority - мигрировать из FIFO в PRIORITY\n"
            "/migrate priority fifo - мигрировать из PRIORITY в FIFO"
        )
        return
    
    from_mode_str = context.args[0].lower()
    to_mode_str = context.args[1].lower()
    
    if from_mode_str not in ["fifo", "priority"] or to_mode_str not in ["fifo", "priority"]:
        await update.message.reply_text(
            "❌ Неверный режим. Доступные режимы: fifo, priority"
        )
        return
    
    if from_mode_str == to_mode_str:
        await update.message.reply_text(
            "❌ Исходный и целевой режим совпадают"
        )
        return
    
    from_mode = QueueMode(from_mode_str)
    to_mode = QueueMode(to_mode_str)
    
    # Показать прогресс
    progress_msg = await update.message.reply_text(
        f"⏳ Миграция очереди: {from_mode.value} → {to_mode.value}..."
    )
    
    try:
        queue_service = get_unified_queue_service()
        
        # Выполнить миграцию
        migrated_count = await queue_service.migrate_queue(
            channel_id=channel_id,
            from_mode=from_mode,
            to_mode=to_mode,
        )
        
        # Автоматически переключить режим
        await queue_service.set_mode(channel_id, to_mode)
        
        # Обновить сообщение
        await progress_msg.edit_text(
            f"✅ <b>Миграция завершена</b>\n\n"
            f"Режим: {from_mode.value} → {to_mode.value}\n"
            f"Перенесено треков: {migrated_count}\n"
            f"Текущий режим: {to_mode.value}",
            parse_mode="HTML"
        )
        
        logger.info(
            f"Admin {user.id} migrated queue: "
            f"channel={channel_id}, {from_mode.value} -> {to_mode.value}, "
            f"items={migrated_count}"
        )
        
    except Exception as e:
        await progress_msg.edit_text(
            f"❌ Ошибка миграции: {str(e)}"
        )
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


def register_queue_commands(application):
    """
    Регистрация команд управления очередью в Telegram боте.
    
    Args:
        application: telegram.ext.Application instance
    """
    from telegram.ext import CommandHandler
    
    # Команды очереди
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("vipqueue", vipqueue_command))
    application.add_handler(CommandHandler("clearqueue", clearqueue_command))
    application.add_handler(CommandHandler("setmode", setmode_command))
    application.add_handler(CommandHandler("migrate", migrate_command))
    
    logger.info("Queue commands registered")
