"""
Pydantic схемы для авторизации через Telegram Login Widget.

Схемы соответствуют OpenAPI контракту: specs/013-telegram-login/contracts/telegram-auth.openapi.yaml
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import uuid


class TelegramAuthRequest(BaseModel):
    """
    Данные от Telegram Login Widget.
    Соответствует структуре callback от виджета.
    
    Все поля кроме id, first_name, auth_date, hash являются опциональными
    в зависимости от настроек приватности пользователя.
    """
    id: int = Field(..., description="Уникальный ID пользователя в Telegram")
    first_name: str = Field(..., description="Имя пользователя")
    last_name: Optional[str] = Field(None, description="Фамилия пользователя")
    username: Optional[str] = Field(None, description="Username в Telegram (без @)")
    photo_url: Optional[str] = Field(None, description="URL аватара пользователя")
    auth_date: int = Field(..., description="Unix timestamp авторизации")
    hash: str = Field(..., description="HMAC-SHA256 подпись для верификации")
    
    # Опциональный Turnstile token для CAPTCHA
    turnstile_token: Optional[str] = Field(None, description="Cloudflare Turnstile token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 123456789,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "photo_url": "https://t.me/i/userpic/320/abc123.jpg",
                "auth_date": 1700000000,
                "hash": "abc123def456..."
            }
        }
    )


class UserResponse(BaseModel):
    """Базовая информация о пользователе для ответа API."""
    id: uuid.UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: str
    status: str
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class TelegramAuthResponse(BaseModel):
    """
    Ответ после успешной авторизации через Telegram.
    
    JWT токен устанавливается в HttpOnly cookie, поэтому не возвращается в теле.
    """
    success: bool = True
    user: UserResponse
    is_new_user: bool = Field(False, description="True если пользователь создан при этом входе")
    message: str = "Авторизация успешна"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": None,
                    "full_name": "John Doe",
                    "profile_picture_url": "https://t.me/i/userpic/320/abc123.jpg",
                    "role": "user",
                    "status": "pending",
                    "telegram_id": 123456789,
                    "telegram_username": "johndoe"
                },
                "is_new_user": True,
                "message": "Авторизация успешна"
            }
        }
    )


class TelegramLinkRequest(BaseModel):
    """
    Запрос на связывание Telegram с существующим аккаунтом.
    Структура идентична TelegramAuthRequest.
    """
    id: int = Field(..., description="Уникальный ID пользователя в Telegram")
    first_name: str = Field(..., description="Имя пользователя")
    last_name: Optional[str] = Field(None, description="Фамилия пользователя")
    username: Optional[str] = Field(None, description="Username в Telegram (без @)")
    photo_url: Optional[str] = Field(None, description="URL аватара пользователя")
    auth_date: int = Field(..., description="Unix timestamp авторизации")
    hash: str = Field(..., description="HMAC-SHA256 подпись для верификации")


class TelegramLinkResponse(BaseModel):
    """Ответ после успешного связывания Telegram с аккаунтом."""
    success: bool = True
    message: str = "Telegram успешно привязан к аккаунту"
    telegram_id: int
    telegram_username: Optional[str] = None


class TelegramUnlinkResponse(BaseModel):
    """Ответ после отвязки Telegram от аккаунта."""
    success: bool = True
    message: str = "Telegram успешно отвязан от аккаунта"


class TelegramAuthError(BaseModel):
    """Схема ошибки авторизации через Telegram."""
    detail: str
    code: str = "telegram_auth_error"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Подпись невалидна или устарела",
                "code": "invalid_signature"
            }
        }
    )
