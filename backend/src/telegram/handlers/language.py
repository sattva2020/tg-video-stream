"""
Telegram language detection and localization handler.

Detects user's Telegram language and provides localized responses.
Supports: ru (Russian), en (English), uk (Ukrainian), es (Spanish)

User Story 10 (Interface Localization):
Интерфейс доступен на русском, украинском, английском и испанском языках.
"""

import logging
from typing import Optional, Dict, Any
from functools import wraps

from pyrogram import Client, filters
from pyrogram.types import Message, User

logger = logging.getLogger(__name__)

# Supported languages with their Telegram codes
SUPPORTED_LANGUAGES = {
    "ru": "ru",  # Russian
    "en": "en",  # English
    "uk": "uk",  # Ukrainian
    "es": "es",  # Spanish
    # Fallbacks for similar languages
    "be": "ru",  # Belarusian -> Russian
    "kk": "ru",  # Kazakh -> Russian
    "pt": "es",  # Portuguese -> Spanish (similar)
    "pt-br": "es",  # Brazilian Portuguese -> Spanish
    "ca": "es",  # Catalan -> Spanish
}

DEFAULT_LANGUAGE = "ru"

# Localized messages for common responses
MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "welcome": "👋 Добро пожаловать! Я бот для управления аудио-трансляциями.",
        "help": "📚 Используйте /help для списка команд.",
        "error": "❌ Произошла ошибка: {error}",
        "success": "✅ Успешно!",
        "loading": "⏳ Загрузка...",
        "not_found": "🔍 Не найдено",
        "unauthorized": "🔒 Требуется авторизация",
        "rate_limited": "⚠️ Превышен лимит запросов. Подождите {seconds} сек.",
        "language_set": "✅ Язык установлен: Русский",
        "language_detect": "🌐 Обнаружен язык: {lang}",
        "invalid_command": "❓ Неизвестная команда. Используйте /help",
        "permission_denied": "🚫 Недостаточно прав для этого действия",
    },
    "en": {
        "welcome": "👋 Welcome! I'm a bot for managing audio broadcasts.",
        "help": "📚 Use /help for the list of commands.",
        "error": "❌ An error occurred: {error}",
        "success": "✅ Success!",
        "loading": "⏳ Loading...",
        "not_found": "🔍 Not found",
        "unauthorized": "🔒 Authorization required",
        "rate_limited": "⚠️ Rate limit exceeded. Wait {seconds} sec.",
        "language_set": "✅ Language set: English",
        "language_detect": "🌐 Language detected: {lang}",
        "invalid_command": "❓ Unknown command. Use /help",
        "permission_denied": "🚫 Insufficient permissions for this action",
    },
    "uk": {
        "welcome": "👋 Ласкаво просимо! Я бот для керування аудіо-трансляціями.",
        "help": "📚 Використовуйте /help для списку команд.",
        "error": "❌ Сталася помилка: {error}",
        "success": "✅ Успішно!",
        "loading": "⏳ Завантаження...",
        "not_found": "🔍 Не знайдено",
        "unauthorized": "🔒 Потрібна авторизація",
        "rate_limited": "⚠️ Перевищено ліміт запитів. Зачекайте {seconds} сек.",
        "language_set": "✅ Мову встановлено: Українська",
        "language_detect": "🌐 Виявлена мова: {lang}",
        "invalid_command": "❓ Невідома команда. Використовуйте /help",
        "permission_denied": "🚫 Недостатньо прав для цієї дії",
    },
    "es": {
        "welcome": "👋 ¡Bienvenido! Soy un bot para gestionar transmisiones de audio.",
        "help": "📚 Use /help para ver la lista de comandos.",
        "error": "❌ Ocurrió un error: {error}",
        "success": "✅ ¡Éxito!",
        "loading": "⏳ Cargando...",
        "not_found": "🔍 No encontrado",
        "unauthorized": "🔒 Autorización requerida",
        "rate_limited": "⚠️ Límite de solicitudes excedido. Espere {seconds} seg.",
        "language_set": "✅ Idioma establecido: Español",
        "language_detect": "🌐 Idioma detectado: {lang}",
        "invalid_command": "❓ Comando desconocido. Use /help",
        "permission_denied": "🚫 Permisos insuficientes para esta acción",
    },
}

# Language display names
LANGUAGE_NAMES = {
    "ru": {"ru": "Русский", "en": "Russian", "uk": "Російська", "es": "Ruso"},
    "en": {"ru": "Английский", "en": "English", "uk": "Англійська", "es": "Inglés"},
    "uk": {"ru": "Украинский", "en": "Ukrainian", "uk": "Українська", "es": "Ucraniano"},
    "es": {"ru": "Испанский", "en": "Spanish", "uk": "Іспанська", "es": "Español"},
}

# User language cache (user_id -> language_code)
_user_languages: Dict[int, str] = {}


def detect_language(user: Optional[User]) -> str:
    """
    Detect user's preferred language from Telegram settings.
    
    Args:
        user: Pyrogram User object
        
    Returns:
        Language code (ru, en, uk, es)
    """
    if not user:
        return DEFAULT_LANGUAGE
    
    # Check cache first
    if user.id in _user_languages:
        return _user_languages[user.id]
    
    # Get Telegram language code
    lang_code = getattr(user, "language_code", None) or DEFAULT_LANGUAGE
    lang_code = lang_code.lower().split("-")[0]  # Handle codes like "en-US"
    
    # Map to supported language
    detected = SUPPORTED_LANGUAGES.get(lang_code, DEFAULT_LANGUAGE)
    
    # Cache the result
    _user_languages[user.id] = detected
    
    logger.debug(f"Detected language for user {user.id}: {lang_code} -> {detected}")
    return detected


def get_user_language(user_id: int) -> str:
    """
    Get cached language for user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Language code
    """
    return _user_languages.get(user_id, DEFAULT_LANGUAGE)


def set_user_language(user_id: int, language: str) -> bool:
    """
    Set user's preferred language.
    
    Args:
        user_id: Telegram user ID
        language: Language code
        
    Returns:
        True if language was set successfully
    """
    if language not in SUPPORTED_LANGUAGES.values():
        # Check if it's a valid supported language directly
        if language not in ["ru", "en", "uk", "es"]:
            return False
    
    _user_languages[user_id] = language
    logger.info(f"User {user_id} language set to: {language}")
    return True


def get_message(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Get localized message by key.
    
    Args:
        key: Message key
        language: Language code (optional, defaults to Russian)
        **kwargs: Format arguments
        
    Returns:
        Localized message string
    """
    lang = language or DEFAULT_LANGUAGE
    messages = MESSAGES.get(lang, MESSAGES[DEFAULT_LANGUAGE])
    message = messages.get(key, MESSAGES[DEFAULT_LANGUAGE].get(key, key))
    
    try:
        return message.format(**kwargs)
    except KeyError:
        return message


def localized(func):
    """
    Decorator to inject user's language into handler.
    
    Adds 'lang' parameter to handler kwargs.
    """
    @wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        user = message.from_user
        lang = detect_language(user)
        kwargs["lang"] = lang
        return await func(client, message, *args, **kwargs)
    return wrapper


async def cmd_language(client: Client, message: Message):
    """
    Set or view current language.
    
    Usage: 
        /language - Show current language
        /language ru|en|uk|es - Set language
    """
    try:
        user_id = message.from_user.id
        current_lang = detect_language(message.from_user)
        
        args = message.text.split(maxsplit=1)
        
        if len(args) < 2:
            # Show current language and available options
            lang_name = LANGUAGE_NAMES.get(current_lang, {}).get(current_lang, current_lang)
            
            response = (
                f"🌐 **{get_message('language_detect', current_lang, lang=lang_name)}**\n\n"
                f"**Доступные языки / Available languages:**\n"
                f"• `/language ru` - 🇷🇺 Русский\n"
                f"• `/language en` - 🇬🇧 English\n"
                f"• `/language uk` - 🇺🇦 Українська\n"
                f"• `/language es` - 🇪🇸 Español\n"
            )
            await message.reply_text(response)
            return
        
        new_lang = args[1].strip().lower()
        
        if new_lang not in ["ru", "en", "uk", "es"]:
            await message.reply_text(
                get_message("error", current_lang, error="Invalid language code")
            )
            return
        
        # Set new language
        set_user_language(user_id, new_lang)
        
        await message.reply_text(get_message("language_set", new_lang))
        logger.info(f"User {user_id} changed language to: {new_lang}")
        
    except Exception as e:
        logger.error(f"Error in cmd_language: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


def register_language_handlers(app: Client):
    """
    Register language-related command handlers.
    
    Args:
        app: Pyrogram Client instance
    """
    app.on_message(filters.command(["language", "lang"]))(cmd_language)
    
    logger.info("Language handlers registered successfully")


# Export utilities for use in other handlers
__all__ = [
    "detect_language",
    "get_user_language",
    "set_user_language",
    "get_message",
    "localized",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "LANGUAGE_NAMES",
    "register_language_handlers",
]
