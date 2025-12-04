"""
Equalizer Commands for Telegram Bot

Telegram команды для управления эквалайзером через PlaybackService API:
- /eq — показать текущее состояние и каталог пресетов
- /eq <preset> — применить пресет (bass_boost, meditation и т.д.)
"""

import logging
from typing import List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from database import SessionLocal
from src.config.equalizer_presets import (
    EQUALIZER_PRESETS,
    PRESET_CATEGORIES,
    list_presets_grouped_with_metadata,
)
from src.services.playback_service import PlaybackService
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
    message = update.effective_message
    if message is None:
        logger.error("/eq command invoked without message context")
        return

    db = SessionLocal()
    try:
        user = await get_or_create_user(update.effective_user, db)
        channel_id = update.effective_chat.id
        playback_service = PlaybackService(db)

        if not context.args:
            await _reply_with_equalizer_menu(message, playback_service, user.id, channel_id)
            return

        preset_name = context.args[0].lower()

        try:
            result = playback_service.set_equalizer_preset(user.id, preset_name, channel_id)
        except ValueError as exc:
            await message.reply_text(
                f"❌ {exc}\n\n"
                f"Используйте /eq для списка доступных пресетов"
            )
            return
        except RuntimeError as exc:
            logger.error("Equalizer backend unavailable", exc_info=True)
            await message.reply_text(
                "⚠️ Не удалось применить эквалайзер. Проверите доступность GStreamer."
            )
            return
        except Exception as exc:  # noqa: BLE001 - хотим показать текст ошибки
            logger.error("Unexpected error in /eq", exc_info=True)
            await message.reply_text(f"❌ Ошибка при установке пресета: {exc}")
            return

        await message.reply_text(
            "🎛️ <b>Эквалайзер обновлен</b>\n\n"
            f"Пресет: <b>{result['display_name']}</b>\n"
            f"Описание: {result['description']}\n\n"
            "Используйте /eq для выбора другого пресета",
            parse_mode="HTML",
        )

        logger.info(
            "User %s set equalizer preset '%s' for channel %s",
            user.id,
            preset_name,
            channel_id,
        )
    finally:
        db.close()


async def _reply_with_equalizer_menu(
    message,
    playback_service: PlaybackService,
    user_id: int,
    channel_id: int,
) -> None:
    eq_state = playback_service.get_equalizer_state(user_id, channel_id)
    categories, total = _build_preset_catalog()
    text, markup = _render_equalizer_view(eq_state, categories, total)
    await message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def eq_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback для inline кнопок эквалайзера.
    
    Callback data format: "eq:<preset_name>"
    """
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("eq:"):
        await query.edit_message_text("❌ Неверный формат данных")
        return

    preset_name = query.data[3:]
    db = SessionLocal()
    try:
        user = await get_or_create_user(update.effective_user, db)
        channel_id = update.effective_chat.id
        playback_service = PlaybackService(db)

        try:
            playback_service.set_equalizer_preset(user.id, preset_name, channel_id)
        except ValueError as exc:
            await query.edit_message_text(f"❌ {exc}")
            return
        except RuntimeError:
            await query.edit_message_text(
                "⚠️ Не удалось применить эквалайзер. Проверьте состояние пайплайна."
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in eq callback handler", exc_info=True)
            await query.edit_message_text(f"❌ Ошибка: {exc}")
            return

        eq_state = playback_service.get_equalizer_state(user.id, channel_id)
        categories, total = _build_preset_catalog()
        text, markup = _render_equalizer_view(eq_state, categories, total)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

        logger.info(
            "User %s set equalizer preset '%s' via callback for channel %s",
            user.id,
            preset_name,
            channel_id,
        )
    finally:
        db.close()


def _build_preset_catalog() -> Tuple[List[dict], int]:
    """Подготовить структуру каталога как в REST API."""

    grouped = list_presets_grouped_with_metadata()
    categories: List[dict] = []
    total = 0

    for category_id, presets in grouped.items():
        sorted_presets = sorted(presets, key=lambda preset: preset["display_name"])
        categories.append(
            {
                "id": category_id,
                "label": PRESET_CATEGORIES.get(category_id, category_id.title()),
                "presets": sorted_presets,
            }
        )
        total += len(sorted_presets)

    categories.sort(key=lambda category: category["label"])
    return categories, total


def _render_equalizer_view(
    eq_state: dict,
    categories: List[dict],
    total: int,
) -> Tuple[str, InlineKeyboardMarkup]:
    """Сформировать текст и клавиатуру для отображения каталога."""

    current_preset = eq_state.get("preset", "flat")
    lines: List[str] = ["🎛️ <b>Эквалайзер</b>", ""]

    if current_preset == "custom":
        lines.append("Текущий пресет: <b>Кастомный</b>")
        lines.append("Настройки были сохранены вручную")
    elif current_preset in EQUALIZER_PRESETS:
        preset_obj = EQUALIZER_PRESETS[current_preset]
        lines.append(f"Текущий пресет: <b>{preset_obj.display_name}</b>")
        lines.append(preset_obj.description)
    else:
        lines.append(f"Текущий пресет: <b>{current_preset}</b>")
    lines.append("")
    lines.append(f"Всего доступно пресетов: {total}")
    lines.append("")

    keyboard: List[List[InlineKeyboardButton]] = []
    for category in categories:
        lines.append(f"<b>{category['label']}:</b>")
        row: List[InlineKeyboardButton] = []
        for preset in category["presets"]:
            label = preset["display_name"]
            if preset["name"] == current_preset:
                label = f"✓ {label}"

            lines.append(
                f"  • {preset['display_name']} — /eq {preset['name']}"
            )

            row.append(
                InlineKeyboardButton(label, callback_data=f"eq:{preset['name']}")
            )

            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        lines.append("")

    lines.append(
        "Выберите пресет кнопками ниже или отправьте команду /eq <название>"
    )

    text = "\n".join(lines)
    return text, InlineKeyboardMarkup(keyboard)


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
