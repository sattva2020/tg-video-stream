"""
Schemas for notification channels, templates, recipients, rules, and delivery logs.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationChannelBase(BaseModel):
    name: str = Field(..., max_length=255, description="Уникальное имя канала")
    type: str = Field(..., max_length=50, description="Тип канала (email, telegram, slack, sms и т.д.)")
    config: dict = Field(default_factory=dict, description="Конфигурация транспорта")
    enabled: bool = Field(default=True, description="Включен ли канал")
    status: str = Field(default="ok", max_length=32, description="Текущее состояние канала")
    concurrency_limit: Optional[int] = Field(None, ge=1, description="Ограничение параллельных отправок")
    retry_attempts: int = Field(default=3, ge=0, description="Количество ретраев")
    retry_interval_sec: int = Field(default=30, ge=0, description="Интервал между ретраями")
    timeout_sec: int = Field(default=10, ge=1, description="Таймаут отправки")
    is_primary: bool = Field(default=False, description="Флаг основного канала")


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    config: Optional[dict] = None
    enabled: Optional[bool] = None
    status: Optional[str] = Field(None, max_length=32)
    concurrency_limit: Optional[int] = Field(None, ge=1)
    retry_attempts: Optional[int] = Field(None, ge=0)
    retry_interval_sec: Optional[int] = Field(None, ge=0)
    timeout_sec: Optional[int] = Field(None, ge=1)
    is_primary: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    id: UUID
    test_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class NotificationTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    locale: str = Field(default="en", max_length=5)
    subject: Optional[str] = Field(None, max_length=255)
    body: str = Field(..., description="Текст шаблона")
    variables: Optional[dict] = Field(None, description="Описание переменных")
    channel_id: Optional[UUID] = Field(None, description="Связанный канал")


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    locale: Optional[str] = Field(None, max_length=5)
    subject: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = None
    variables: Optional[dict] = None
    channel_id: Optional[UUID] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class NotificationRecipientBase(BaseModel):
    type: str = Field(..., max_length=50, description="Тип адресата (email, telegram, slack, sms)")
    address: str = Field(..., max_length=255, description="Адрес или идентификатор")
    silence_windows: Optional[dict] = Field(None, description="Окна тишины")
    status: str = Field(default="active", max_length=32, description="active | blocked | opt-out")


class NotificationRecipientCreate(NotificationRecipientBase):
    pass


class NotificationRecipientUpdate(BaseModel):
    address: Optional[str] = Field(None, max_length=255)
    silence_windows: Optional[dict] = None
    status: Optional[str] = Field(None, max_length=32)


class NotificationRecipientResponse(NotificationRecipientBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class NotificationRuleBase(BaseModel):
    name: str = Field(..., max_length=255)
    enabled: bool = Field(default=True)
    severity_filter: Optional[dict] = Field(None, description="Фильтры по уровню")
    tag_filter: Optional[dict] = Field(None, description="Фильтры по тегам")
    host_filter: Optional[dict] = Field(None, description="Фильтры по хостам")
    failover_timeout_sec: int = Field(default=30, ge=0)
    silence_windows: Optional[dict] = Field(None, description="Окна тишины")
    rate_limit: Optional[dict] = Field(None, description="Лимиты отправки")
    dedup_window_sec: int = Field(default=0, ge=0)
    template_id: Optional[UUID] = None
    recipient_ids: List[UUID] = Field(default_factory=list)
    channel_ids: List[UUID] = Field(default_factory=list)
    test_channel_ids: Optional[List[UUID]] = None


class NotificationRuleCreate(NotificationRuleBase):
    pass


class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    severity_filter: Optional[dict] = None
    tag_filter: Optional[dict] = None
    host_filter: Optional[dict] = None
    failover_timeout_sec: Optional[int] = Field(None, ge=0)
    silence_windows: Optional[dict] = None
    rate_limit: Optional[dict] = None
    dedup_window_sec: Optional[int] = Field(None, ge=0)
    template_id: Optional[UUID] = None
    recipient_ids: Optional[List[UUID]] = None
    channel_ids: Optional[List[UUID]] = None
    test_channel_ids: Optional[List[UUID]] = None


class NotificationRuleResponse(NotificationRuleBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class DeliveryLogResponse(BaseModel):
    id: UUID
    event_id: str
    rule_id: Optional[UUID]
    channel_id: Optional[UUID]
    recipient_id: Optional[UUID]
    status: str
    attempt: int
    latency_ms: Optional[int]
    response_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
