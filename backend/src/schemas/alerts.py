"""
Schemas for alert rules, alert instances, and alert groups.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=255, description="Уникальное имя правила")
    description: Optional[str] = Field(None, description="Описание правила")
    enabled: bool = Field(default=True, description="Включено ли правило")
    alert_type: str = Field(..., max_length=50, description="Тип алерта (stream_quality, service_health, resource, custom)")
    severity: str = Field(default="warning", max_length=32, description="Уровень важности (critical, warning, info)")
    category: Optional[str] = Field(None, max_length=100, description="Категория алерта")
    conditions: dict = Field(..., description="Условия срабатывания алерта")
    cooldown_sec: int = Field(default=300, ge=0, description="Время коолдауна между алертами")
    rate_limit_minutes: Optional[int] = Field(None, ge=1, description="Окно_rate limit в минутах")
    rate_limit_count: Optional[int] = Field(None, ge=1, description="Максимальное количество алертов в окне")
    notification_channels: Optional[dict] = Field(None, description="Каналы для уведомлений")
    notify_on_recovery: bool = Field(default=False, description="Отправлять уведомление при восстановлении")
    auto_resolve: bool = Field(default=False, description="Автоматически закрывать алерт при устранении условия")
    escalation_enabled: bool = Field(default=False, description="Включена эскалация")
    escalation_rules: Optional[dict] = Field(None, description="Правила эскалации")
    active_windows: Optional[dict] = Field(None, description="Временные окна активности правила")
    silence_windows: Optional[dict] = Field(None, description="Окна подавления алертов")


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    alert_type: Optional[str] = Field(None, max_length=50)
    severity: Optional[str] = Field(None, max_length=32)
    category: Optional[str] = Field(None, max_length=100)
    conditions: Optional[dict] = None
    cooldown_sec: Optional[int] = Field(None, ge=0)
    rate_limit_minutes: Optional[int] = Field(None, ge=1)
    rate_limit_count: Optional[int] = Field(None, ge=1)
    notification_channels: Optional[dict] = None
    notify_on_recovery: Optional[bool] = None
    auto_resolve: Optional[bool] = None
    escalation_enabled: Optional[bool] = None
    escalation_rules: Optional[dict] = None
    active_windows: Optional[dict] = None
    silence_windows: Optional[dict] = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    last_triggered_at: Optional[datetime]
    last_resolved_at: Optional[datetime]
    trigger_count: int
    consecutive_triggers: int
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[UUID]
    updated_by: Optional[UUID]

    class Config:
        orm_mode = True


class AlertInstanceBase(BaseModel):
    alert_type: str = Field(..., max_length=50, description="Тип алерта")
    severity: str = Field(default="warning", max_length=32, description="Уровень важности")
    status: str = Field(default="firing", max_length=32, description="Статус алерта (firing, resolved, acknowledged, suppressed)")
    trigger_value: Optional[dict] = Field(None, description="Значение, вызвавшее алерт")
    context: Optional[dict] = Field(None, description="Дополнительный контекст алерта")
    notification_sent: bool = Field(default=False, description="Отправлено ли уведомление")
    notification_channels: Optional[dict] = Field(None, description="Каналы уведомлений и статусы")


class AlertInstanceCreate(AlertInstanceBase):
    rule_id: UUID = Field(..., description="ID правила алерта")


class AlertInstanceUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=32)
    notification_sent: Optional[bool] = None
    notification_channels: Optional[dict] = None
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UUID] = None
    duration_sec: Optional[int] = Field(None, ge=0)


class AlertInstanceResponse(AlertInstanceBase):
    id: UUID
    rule_id: UUID
    group_id: Optional[UUID]
    fired_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[UUID]
    duration_sec: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class AlertGroupBase(BaseModel):
    group_key: str = Field(..., max_length=255, description="Уникальный ключ группы")
    name: Optional[str] = Field(None, max_length=255, description="Название группы")
    status: str = Field(default="active", max_length=32, description="Статус группы (active, resolved, suppressed)")
    severity: str = Field(default="warning", max_length=32, description="Уровень важности")
    context: Optional[dict] = Field(None, description="Контекст группы")


class AlertGroupCreate(AlertGroupBase):
    rule_id: UUID = Field(..., description="ID правила алерта")


class AlertGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)
    severity: Optional[str] = Field(None, max_length=32)
    context: Optional[dict] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None


class AlertGroupResponse(AlertGroupBase):
    id: UUID
    rule_id: UUID
    alert_count: int
    first_alert_at: datetime
    last_alert_at: datetime
    notification_sent: bool
    last_notification_at: Optional[datetime]
    notification_count: int
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
