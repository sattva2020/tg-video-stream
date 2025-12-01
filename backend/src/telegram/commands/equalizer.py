"""
Equalizer Commands for Telegram Bot

Telegram команды для управления эквалайзером:
- /eq - показать текущий пресет и список доступных
- /eq <preset> - установить пресет эквалайзера
"""

from typing import Optional
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from streamer.playback_control import get_playback_controller
from src.config.equalizer_presets import (
    EQUALIZER_PRESETS,
    PRESET_CATEGORIES,
    list_presets_by_category,
)
from src.telegram.utils.auth import get_or_create_user
from src.telegram.utils.decorators import with_error_handling

logger = logging.getLogger(__name__)


@with_error_handling
async def eq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Управление эквалайзером.
    
    Usage:
        /eq - показать текущий пресет и меню выбора
        /eq <preset_name> - установить пресет
    """
    user = await get_or_create_user(update.effective_user)
    channel_id = str(update.effective_chat.id)
    
    playback_controller = get_playback_controller()
    
    # Если нет аргументов - показать текущее состояние и меню
    if not context.args:
        await _show_equalizer_menu(update, channel_id, playback_controller)
        return
    
    # Если указан пресет - установить его
    preset_name = context.args[0].lower()
    
    if preset_name not in EQUALIZER_PRESETS:
        await update.message.reply_text(
            f"❌ Неизвестный пресет: {preset_name}\n\n"
            f"Используйте /eq для просмотра доступных пресетов"
        )
        return
    
    # Установить пресет
    try:
        success = playback_controller.set_equalizer_preset(channel_id, preset_name)
        
        if success:
            preset = EQUALIZER_PRESETS[preset_name]
            await update.message.reply_text(
                f"🎛️ <b>Эквалайзер обновлен</b>\n\n"
                f"Пресет: <b>{preset.display_name}</b>\n"
                f"Описание: {preset.description}",
                parse_mode="HTML"
            )
            
            logger.info(
                f"User {user.id} set equalizer preset '{preset_name}' for channel {channel_id}"
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось применить эквалайзер. "
                "Возможно, GStreamer не доступен."
            )
    
    except Exception as e:
        logger.error(f"Error setting equalizer preset: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при установке пресета: {str(e)}"
        )


async def _show_equalizer_menu(update: Update, channel_id: str, playback_controller):
    """Показать меню выбора пресета эквалайзера."""
    # Получить текущее состояние
    eq_state = playback_controller.get_equalizer_state(channel_id)
    current_preset = eq_state["preset"]
    
    # Заголовок сообщения
    message = "🎛️ <b>Эквалайзер</b>\n\n"
    
    if current_preset in EQUALIZER_PRESETS:
        preset_obj = EQUALIZER_PRESETS[current_preset]
        message += f"Текущий пресет: <b>{preset_obj.display_name}</b>\n"
        message += f"{preset_obj.description}\n\n"
    else:
        message += f"Текущий пресет: <b>Кастомный</b>\n\n"
    
    # Группировка пресетов по категориям
    presets_by_category = list_presets_by_category()
    
    # Создать inline keyboard с пресетами
    keyboard = []
    
    for category, preset_names in presets_by_category.items():
        # Заголовок категории
        category_label = PRESET_CATEGORIES.get(category, category)
        message += f"<b>{category_label}:</b>\n"
        
        # Кнопки для пресетов в этой категории
        category_buttons = []
        for preset_name in preset_names:
            preset = EQUALIZER_PRESETS[preset_name]
            
            # Добавить ✓ если это текущий пресет
            label = preset.display_name
            if preset_name == current_preset:
                label = f"✓ {label}"
            
            # Команда для установки пресета
            message += f"  • {preset.display_name} - /eq {preset_name}\n"
            
            category_buttons.append(
                InlineKeyboardButton(
                    label,
                    callback_data=f"eq:{preset_name}"
                )
            )
        
        # Добавить ряды кнопок (по 2 в ряд)
        for i in range(0, len(category_buttons), 2):
            row = category_buttons[i:i+2]
            keyboard.append(row)
        
        message += "\n"
    
    message += "Выберите пресет из кнопок ниже или используйте команду /eq <название>"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def eq_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback для inline кнопок эквалайзера.
    
    Callback data format: "eq:<preset_name>"
    """
    query = update.callback_query
    await query.answer()
    
    user = await get_or_create_user(update.effective_user)
    channel_id = str(update.effective_chat.id)
    
    # Парсить callback data
    if not query.data or not query.data.startswith("eq:"):
        await query.edit_message_text("❌ Неверный формат данных")
        return
    
    preset_name = query.data[3:]  # Удалить "eq:" префикс
    
    if preset_name not in EQUALIZER_PRESETS:
        await query.edit_message_text(f"❌ Неизвестный пресет: {preset_name}")
        return
    
    # Установить пресет
    playback_controller = get_playback_controller()
    
    try:
        success = playback_controller.set_equalizer_preset(channel_id, preset_name)
        
        if success:
            preset = EQUALIZER_PRESETS[preset_name]
            
            # Обновить сообщение
            await query.edit_message_text(
                f"🎛️ <b>Эквалайзер обновлен</b>\n\n"
                f"Пресет: <b>{preset.display_name}</b>\n"
                f"Описание: {preset.description}\n\n"
                f"Используйте /eq для изменения пресета",
                parse_mode="HTML"
            )
            
            logger.info(
                f"User {user.id} set equalizer preset '{preset_name}' "
                f"via callback for channel {channel_id}"
            )
        else:
            await query.edit_message_text(
                "⚠️ Не удалось применить эквалайзер. "
                "Возможно, GStreamer не доступен."
            )
    
    except Exception as e:
        logger.error(f"Error in eq callback handler: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


def register_equalizer_commands(application):
    """
    Регистрация команд эквалайзера в Telegram боте.
    
    Args:
        application: telegram.ext.Application instance
    """
    from telegram.ext import CommandHandler
    
    # Команда /eq
    application.add_handler(CommandHandler("eq", eq_command))
    
    # Callback handler для inline кнопок
    application.add_handler(CallbackQueryHandler(eq_callback_handler, pattern="^eq:"))
    
    logger.info("Equalizer commands registered")
