"""
Mobile API schemas
Feature: 017-native-mobile-applications
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# === Types ===

MobilePlatform = Literal["ios", "android"]
DeviceStatus = Literal["active", "inactive", "revoked"]


# === Device Registration Schemas ===

class MobileDeviceRegisterRequest(BaseModel):
    """Запрос на регистрацию мобильного устройства."""
    device_id: str = Field(..., min_length=1, max_length=255, description="Уникальный идентификатор устройства")
    platform: MobilePlatform = Field(..., description="Платформа устройства (ios или android)")
    push_token: str = Field(..., min_length=1, max_length=500, description="Push токен для уведомлений")
    device_name: Optional[str] = Field(None, max_length=255, description="Название устройства")
    app_version: Optional[str] = Field(None, max_length=50, description="Версия приложения")
    os_version: Optional[str] = Field(None, max_length=50, description="Версия ОС")


class MobileDeviceRegisterResponse(BaseModel):
    """Ответ на регистрацию устройства."""
    id: UUID = Field(..., description="ID зарегистрированного устройства")
    device_id: str = Field(..., description="Идентификатор устройства")
    platform: MobilePlatform = Field(..., description="Платформа устройства")
    status: DeviceStatus = Field(..., description="Статус устройства")
    registered_at: datetime = Field(..., description="Время регистрации")


# === Push Token Management Schemas ===

class PushTokenUpdateRequest(BaseModel):
    """Запрос на обновление push токена."""
    push_token: str = Field(..., min_length=1, max_length=500, description="Новый push токен")


class PushTokenUpdateResponse(BaseModel):
    """Ответ на обновление токена."""
    id: UUID = Field(..., description="ID устройства")
    push_token: str = Field(..., description="Обновленный push токен")
    updated_at: datetime = Field(..., description="Время обновления")


# === Device Info Schemas ===

class MobileDeviceResponse(BaseModel):
    """Информация о мобильном устройстве."""
    id: UUID = Field(..., description="ID устройства")
    device_id: str = Field(..., description="Идентификатор устройства")
    platform: MobilePlatform = Field(..., description="Платформа устройства")
    device_name: Optional[str] = Field(None, description="Название устройства")
    app_version: Optional[str] = Field(None, description="Версия приложения")
    os_version: Optional[str] = Field(None, description="Версия ОС")
    status: DeviceStatus = Field(..., description="Статус устройства")
    push_token: str = Field(..., description="Push токен")
    last_seen_at: Optional[datetime] = Field(None, description="Последняя активность")
    registered_at: datetime = Field(..., description="Время регистрации")
    updated_at: Optional[datetime] = Field(None, description="Время последнего обновления")

    class Config:
        orm_mode = True


class MobileDeviceListResponse(BaseModel):
    """Список мобильных устройств пользователя."""
    devices: List[MobileDeviceResponse] = Field(default_factory=list, description="Список устройств")
    total: int = Field(..., ge=0, description="Общее количество устройств")


# === Device Management Schemas ===

class MobileDeviceUpdateRequest(BaseModel):
    """Запрос на обновление информации об устройстве."""
    device_name: Optional[str] = Field(None, max_length=255, description="Название устройства")
    app_version: Optional[str] = Field(None, max_length=50, description="Версия приложения")
    os_version: Optional[str] = Field(None, max_length=50, description="Версия ОС")
    status: Optional[DeviceStatus] = Field(None, description="Статус устройства")


class MobileDeviceUpdateResponse(BaseModel):
    """Ответ на обновление устройства."""
    id: UUID = Field(..., description="ID устройства")
    updated_at: datetime = Field(..., description="Время обновления")


# === Notification Test Schema ===

class PushNotificationTestRequest(BaseModel):
    """Запрос на тестовое push уведомление."""
    device_id: UUID = Field(..., description="ID устройства")
    title: str = Field(..., max_length=255, description="Заголовок уведомления")
    body: str = Field(..., max_length=1000, description="Текст уведомления")
    data: Optional[dict] = Field(None, description="Дополнительные данные")


class PushNotificationTestResponse(BaseModel):
    """Ответ на отправку тестового уведомления."""
    success: bool = Field(..., description="Успешность отправки")
    message: str = Field(..., description="Сообщение о результате")
    notification_id: Optional[str] = Field(None, description="ID уведомления в сервисе推送")


# === Batch Operations Schema ===

class UnregisterDevicesRequest(BaseModel):
    """Запрос на отмену регистрации нескольких устройств."""
    device_ids: List[UUID] = Field(..., min_items=1, description="Список ID устройств для удаления")


class UnregisterDevicesResponse(BaseModel):
    """Ответ на отмену регистрации устройств."""
    unregistered_count: int = Field(..., ge=0, description="Количество удаленных устройств")
    device_ids: List[UUID] = Field(..., description="Список ID удаленных устройств")
