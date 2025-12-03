"""
Internationalization (i18n) API endpoints.

Provides:
- GET /api/i18n/languages - List available languages
- GET /api/i18n/messages/{lang} - Get messages for language
- POST /api/i18n/detect - Detect language from Accept-Language header

User Story 10 (Interface Localization):
Интерфейс доступен на русском, украинском, английском и испанском языках.
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/i18n", tags=["i18n"])


# Supported languages configuration
SUPPORTED_LANGUAGES = [
    {
        "code": "ru",
        "name": "Русский",
        "nativeName": "Русский",
        "flag": "🇷🇺",
        "direction": "ltr",
        "isDefault": True,
    },
    {
        "code": "en",
        "name": "English",
        "nativeName": "English",
        "flag": "🇬🇧",
        "direction": "ltr",
        "isDefault": False,
    },
    {
        "code": "uk",
        "name": "Ukrainian",
        "nativeName": "Українська",
        "flag": "🇺🇦",
        "direction": "ltr",
        "isDefault": False,
    },
    {
        "code": "es",
        "name": "Spanish",
        "nativeName": "Español",
        "flag": "🇪🇸",
        "direction": "ltr",
        "isDefault": False,
    },
]

DEFAULT_LANGUAGE = "ru"

# Server-side messages (subset for API responses)
SERVER_MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "welcome": "Добро пожаловать",
        "error.generic": "Произошла ошибка",
        "error.notFound": "Не найдено",
        "error.unauthorized": "Требуется авторизация",
        "error.forbidden": "Доступ запрещён",
        "error.rateLimited": "Превышен лимит запросов",
        "success.saved": "Сохранено",
        "success.deleted": "Удалено",
        "success.updated": "Обновлено",
    },
    "en": {
        "welcome": "Welcome",
        "error.generic": "An error occurred",
        "error.notFound": "Not found",
        "error.unauthorized": "Authorization required",
        "error.forbidden": "Access denied",
        "error.rateLimited": "Rate limit exceeded",
        "success.saved": "Saved",
        "success.deleted": "Deleted",
        "success.updated": "Updated",
    },
    "uk": {
        "welcome": "Ласкаво просимо",
        "error.generic": "Сталася помилка",
        "error.notFound": "Не знайдено",
        "error.unauthorized": "Потрібна авторизація",
        "error.forbidden": "Доступ заборонено",
        "error.rateLimited": "Перевищено ліміт запитів",
        "success.saved": "Збережено",
        "success.deleted": "Видалено",
        "success.updated": "Оновлено",
    },
    "es": {
        "welcome": "Bienvenido",
        "error.generic": "Ocurrió un error",
        "error.notFound": "No encontrado",
        "error.unauthorized": "Autorización requerida",
        "error.forbidden": "Acceso denegado",
        "error.rateLimited": "Límite de solicitudes excedido",
        "success.saved": "Guardado",
        "success.deleted": "Eliminado",
        "success.updated": "Actualizado",
    },
}


class LanguageInfo(BaseModel):
    """Language information model."""
    code: str = Field(..., description="ISO 639-1 language code")
    name: str = Field(..., description="Language name in English")
    nativeName: str = Field(..., description="Language name in native script")
    flag: str = Field(..., description="Flag emoji")
    direction: str = Field(default="ltr", description="Text direction (ltr/rtl)")
    isDefault: bool = Field(default=False, description="Is default language")


class LanguagesResponse(BaseModel):
    """Response model for languages list."""
    languages: List[LanguageInfo]
    defaultLanguage: str
    totalCount: int


class MessagesResponse(BaseModel):
    """Response model for messages."""
    language: str
    messages: Dict[str, str]


class DetectLanguageResponse(BaseModel):
    """Response model for language detection."""
    detected: str
    supported: bool
    fallback: Optional[str] = None


@router.get("/languages", response_model=LanguagesResponse)
async def get_languages() -> LanguagesResponse:
    """
    Get list of available languages.
    
    Returns:
        List of supported languages with metadata
    """
    return LanguagesResponse(
        languages=[LanguageInfo(**lang) for lang in SUPPORTED_LANGUAGES],
        defaultLanguage=DEFAULT_LANGUAGE,
        totalCount=len(SUPPORTED_LANGUAGES),
    )


@router.get("/messages/{lang}", response_model=MessagesResponse)
async def get_messages(lang: str) -> MessagesResponse:
    """
    Get server-side messages for a language.
    
    Args:
        lang: Language code (ru, en, uk, es)
        
    Returns:
        Dictionary of translated messages
    """
    # Validate language
    if lang not in SERVER_MESSAGES:
        # Fall back to default
        logger.warning(f"Unsupported language requested: {lang}, falling back to {DEFAULT_LANGUAGE}")
        lang = DEFAULT_LANGUAGE
    
    return MessagesResponse(
        language=lang,
        messages=SERVER_MESSAGES[lang],
    )


@router.post("/detect", response_model=DetectLanguageResponse)
async def detect_language(request: Request) -> DetectLanguageResponse:
    """
    Detect language from Accept-Language header.
    
    Uses the Accept-Language HTTP header to determine
    the user's preferred language.
    
    Returns:
        Detected language and fallback if not supported
    """
    accept_language = request.headers.get("Accept-Language", "")
    
    # Parse Accept-Language header
    # Format: "en-US,en;q=0.9,ru;q=0.8"
    detected = DEFAULT_LANGUAGE
    supported = False
    fallback = None
    
    if accept_language:
        # Parse language preferences
        languages = []
        for part in accept_language.split(","):
            part = part.strip()
            if ";q=" in part:
                lang, q = part.split(";q=")
                try:
                    quality = float(q)
                except ValueError:
                    quality = 1.0
            else:
                lang = part
                quality = 1.0
            
            # Extract primary language code
            lang = lang.split("-")[0].lower()
            languages.append((lang, quality))
        
        # Sort by quality
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # Find first supported language
        supported_codes = [l["code"] for l in SUPPORTED_LANGUAGES]
        for lang, _ in languages:
            if lang in supported_codes:
                detected = lang
                supported = True
                break
        
        if not supported and languages:
            # Return the first preferred language with fallback
            detected = languages[0][0]
            fallback = DEFAULT_LANGUAGE
    
    logger.debug(f"Language detection: header={accept_language}, detected={detected}, supported={supported}")
    
    return DetectLanguageResponse(
        detected=detected if supported else DEFAULT_LANGUAGE,
        supported=supported,
        fallback=fallback,
    )


@router.get("/language/{lang}/exists")
async def check_language_exists(lang: str) -> Dict[str, Any]:
    """
    Check if a language is supported.
    
    Args:
        lang: Language code to check
        
    Returns:
        Existence status and language info if found
    """
    supported_codes = [l["code"] for l in SUPPORTED_LANGUAGES]
    exists = lang.lower() in supported_codes
    
    if exists:
        lang_info = next(
            (l for l in SUPPORTED_LANGUAGES if l["code"] == lang.lower()),
            None
        )
        return {
            "exists": True,
            "language": lang_info,
        }
    
    return {
        "exists": False,
        "language": None,
        "availableLanguages": supported_codes,
    }
