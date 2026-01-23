"""
Reports API schemas
Feature: 012-comprehensive-analytics-dashboard
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

ReportType = Literal["summary", "listeners", "top_tracks", "engagement", "stream_performance", "content_insights"]
ReportFormat = Literal["csv"]  # Can be extended with "pdf", "xlsx" etc.
ScheduleFrequency = Literal["daily", "weekly", "monthly"]


# === Export Request Schemas ===

class ReportExportRequest(BaseModel):
    """Запрос на экспорт отчета."""
    report_type: ReportType = Field(..., description="Тип отчета")
    period: str = Field("7d", description="Период данных (7d, 30d, 90d, all)")
    format: ReportFormat = Field("csv", description="Формат отчета")


class ReportExportResponse(BaseModel):
    """Ответ на экспорт отчета."""
    success: bool = Field(..., description="Успешность операции")
    report_type: ReportType = Field(..., description="Тип отчета")
    format: ReportFormat = Field(..., description="Формат отчета")
    data: Optional[str] = Field(None, description="CSV данные (для формата csv)")
    filename: str = Field(..., description="Имя файла для скачивания")
    generated_at: datetime = Field(..., description="Время генерации")


# === Schedule Request Schemas ===

class ReportScheduleRequest(BaseModel):
    """Запрос на планирование отчета."""
    report_type: ReportType = Field(..., description="Тип отчета")
    period: str = Field("7d", description="Период данных (7d, 30d, 90d, all)")
    format: ReportFormat = Field("csv", description="Формат отчета")
    frequency: ScheduleFrequency = Field(..., description="Частота отправки")
    email: Optional[str] = Field(None, description="Email для отправки отчета")
    enabled: bool = Field(True, description="Включено ли расписание")


class ReportScheduleResponse(BaseModel):
    """Ответ на планирование отчета."""
    id: int = Field(..., description="ID расписания")
    report_type: ReportType = Field(..., description="Тип отчета")
    frequency: ScheduleFrequency = Field(..., description="Частота отправки")
    email: Optional[str] = Field(None, description="Email для отправки")
    enabled: bool = Field(..., description="Включено ли расписание")
    created_at: datetime = Field(..., description="Время создания")
    next_run_at: Optional[datetime] = Field(None, description="Следующий запуск")


class ReportScheduleUpdate(BaseModel):
    """Обновление расписания отчета."""
    frequency: Optional[ScheduleFrequency] = Field(None, description="Частота отправки")
    email: Optional[str] = Field(None, description="Email для отправки отчета")
    enabled: Optional[bool] = Field(None, description="Включено ли расписание")


# === Schedule List Schemas ===

class ScheduleListItem(BaseModel):
    """Элемент списка расписаний."""
    id: int = Field(..., description="ID расписания")
    report_type: ReportType = Field(..., description="Тип отчета")
    period: str = Field(..., description="Период данных")
    format: ReportFormat = Field(..., description="Формат отчета")
    frequency: ScheduleFrequency = Field(..., description="Частота отправки")
    email: Optional[str] = Field(None, description="Email для отправки")
    enabled: bool = Field(..., description="Включено ли расписание")
    created_at: datetime = Field(..., description="Время создания")
    next_run_at: Optional[datetime] = Field(None, description="Следующий запуск")
    last_sent_at: Optional[datetime] = Field(None, description="Последняя отправка")


class ReportScheduleListResponse(BaseModel):
    """Список расписаний отчетов."""
    schedules: list[ScheduleListItem] = Field(default_factory=list, description="Список расписаний")
    total: int = Field(..., description="Общее количество")
