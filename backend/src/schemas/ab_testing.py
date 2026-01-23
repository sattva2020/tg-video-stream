"""
A/B Testing API schemas
Feature: 016-a-b-testing-framework-for-content
"""
from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


# === Types ===

ABTestStatus = Literal["draft", "running", "paused", "completed", "stopped"]
ABTestMetricType = Literal["impressions", "clicks", "conversions", "watch_time_seconds", "peak_listeners", "avg_view_duration"]


# === Variant Schemas ===

class ABTestVariantBase(BaseModel):
    """Базовые поля варианта A/B теста."""
    name: str = Field(..., min_length=1, max_length=255, description="Название варианта")
    description: Optional[str] = Field(None, description="Описание варианта")
    traffic_allocation: int = Field(..., ge=0, le=100, description="Процент трафика (0-100)")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Конфигурация варианта (playlist_id, schedule_settings, etc.)")


class ABTestVariantCreate(ABTestVariantBase):
    """Создание варианта A/B теста."""
    position: int = Field(0, ge=0, description="Порядок отображения")


class ABTestVariantUpdate(BaseModel):
    """Обновление варианта A/B теста."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название варианта")
    description: Optional[str] = Field(None, description="Описание варианта")
    traffic_allocation: Optional[int] = Field(None, ge=0, le=100, description="Процент трафика (0-100)")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Конфигурация варианта")


class ABTestVariantResponse(ABTestVariantBase):
    """Вариант A/B теста с результатами."""
    id: UUID = Field(..., description="ID варианта")
    test_id: UUID = Field(..., description="ID теста")
    position: int = Field(..., ge=0, description="Порядок отображения")
    is_winner: bool = Field(False, description="Является ли победителем")
    conversion_rate: Optional[float] = Field(None, ge=0, le=1, description="Конверсия (0.0 - 1.0)")
    improvement: Optional[float] = Field(None, description="Улучшение в % относительно baseline")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время обновления")


# === Metric Schemas ===

class ABTestMetricBase(BaseModel):
    """Базовые поля метрики A/B теста."""
    metric_type: ABTestMetricType = Field(..., description="Тип метрики")
    metric_value: int = Field(..., ge=0, description="Значение метрики")


class ABTestMetricCreate(ABTestMetricBase):
    """Создание метрики A/B теста."""
    variant_id: UUID = Field(..., description="ID варианта")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")


class ABTestMetricResponse(ABTestMetricBase):
    """Метрика A/B теста."""
    id: int = Field(..., description="ID метрики")
    variant_id: UUID = Field(..., description="ID варианта")
    recorded_at: datetime = Field(..., description="Время записи")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")


# === Test Schemas ===

class ABTestBase(BaseModel):
    """Базовые поля A/B теста."""
    name: str = Field(..., min_length=1, max_length=255, description="Название теста")
    description: Optional[str] = Field(None, description="Описание теста")
    hypothesis: Optional[str] = Field(None, description="Гипотеза теста")


class ABTestCreate(ABTestBase):
    """Создание A/B теста."""
    channel_id: UUID = Field(..., description="ID канала")
    planned_duration_hours: Optional[int] = Field(None, ge=1, description="Планируемая длительность в часах")
    traffic_config: Optional[Dict[str, Any]] = Field(None, description="Конфигурация распределения трафика")
    variants: List[ABTestVariantCreate] = Field(..., min_length=2, max_length=10, description="Варианты теста (минимум 2)")


class ABTestUpdate(BaseModel):
    """Обновление A/B теста."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название теста")
    description: Optional[str] = Field(None, description="Описание теста")
    hypothesis: Optional[str] = Field(None, description="Гипотеза теста")
    planned_duration_hours: Optional[int] = Field(None, ge=1, description="Планируемая длительность в часах")
    traffic_config: Optional[Dict[str, Any]] = Field(None, description="Конфигурация распределения трафика")


class ABTestResponse(ABTestBase):
    """A/B тест с результатами."""
    id: UUID = Field(..., description="ID теста")
    channel_id: UUID = Field(..., description="ID канала")
    status: ABTestStatus = Field(..., description="Статус теста")
    start_time: Optional[datetime] = Field(None, description="Время запуска")
    end_time: Optional[datetime] = Field(None, description="Время завершения")
    planned_duration_hours: Optional[int] = Field(None, description="Планируемая длительность в часах")
    traffic_config: Optional[Dict[str, Any]] = Field(None, description="Конфигурация распределения трафика")
    winner_variant_id: Optional[UUID] = Field(None, description="ID варианта-победителя")
    confidence_level: Optional[float] = Field(None, ge=0, le=100, description="Уровень доверия (0-100)")
    is_significant: Optional[bool] = Field(None, description="Статистически значимый результат")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время обновления")
    created_by: Optional[UUID] = Field(None, description="ID создателя")
    variants: List[ABTestVariantResponse] = Field(default_factory=list, description="Варианты теста")


class ABTestListResponse(BaseModel):
    """Список A/B тестов (без вариантов)."""
    id: UUID = Field(..., description="ID теста")
    channel_id: UUID = Field(..., description="ID канала")
    name: str = Field(..., description="Название теста")
    status: ABTestStatus = Field(..., description="Статус теста")
    start_time: Optional[datetime] = Field(None, description="Время запуска")
    end_time: Optional[datetime] = Field(None, description="Время завершения")
    winner_variant_id: Optional[UUID] = Field(None, description="ID варианта-победителя")
    is_significant: Optional[bool] = Field(None, description="Статистически значимый результат")
    created_at: datetime = Field(..., description="Время создания")
    variant_count: int = Field(..., ge=0, description="Количество вариантов")


class ABTestCollectionResponse(BaseModel):
    """Коллекция A/B тестов."""
    tests: List[ABTestListResponse] = Field(default_factory=list, description="Список тестов")
    total: int = Field(..., ge=0, description="Общее количество")


# === Statistical Analysis Schemas ===

class ABTestStatistics(BaseModel):
    """Статистика варианта для анализа."""
    variant_id: UUID = Field(..., description="ID варианта")
    variant_name: str = Field(..., description="Название варианта")
    impressions: int = Field(..., ge=0, description="Количество показов")
    conversions: int = Field(..., ge=0, description="Количество конверсий")
    conversion_rate: float = Field(..., ge=0, le=1, description="Конверсия (0.0 - 1.0)")
    confidence_interval_lower: Optional[float] = Field(None, ge=0, le=1, description="Нижняя граница доверительного интервала")
    confidence_interval_upper: Optional[float] = Field(None, ge=0, le=1, description="Верхняя граница доверительного интервала")


class ABTestAnalysisResponse(BaseModel):
    """Результаты статистического анализа A/B теста."""
    test_id: UUID = Field(..., description="ID теста")
    test_name: str = Field(..., description="Название теста")
    status: ABTestStatus = Field(..., description="Статус теста")
    variants: List[ABTestStatistics] = Field(default_factory=list, description="Статистика по вариантам")
    winner_variant_id: Optional[UUID] = Field(None, description="ID варианта-победителя")
    confidence_level: float = Field(..., ge=0, le=100, description="Уровень доверия (0-100)")
    is_significant: bool = Field(..., description="Статистически значимый результат")
    p_value: Optional[float] = Field(None, ge=0, le=1, description="P-value")
    recommended_action: Optional[str] = Field(None, description="Рекомендованное действие")
    analyzed_at: datetime = Field(..., description="Время анализа")


# === Internal Schemas (for service layer) ===

class ABTestStartRequest(BaseModel):
    """Запрос на запуск A/B теста."""
    test_id: UUID = Field(..., description="ID теста")


class ABTestStartResponse(BaseModel):
    """Ответ на запуск A/B теста."""
    test_id: UUID = Field(..., description="ID теста")
    status: ABTestStatus = Field(..., description="Новый статус")
    start_time: datetime = Field(..., description="Время запуска")


class ABTestStopRequest(BaseModel):
    """Запрос на остановку A/B теста."""
    test_id: UUID = Field(..., description="ID теста")
    select_winner: bool = Field(True, description="Автоматически выбрать победителя")


class ABTestStopResponse(BaseModel):
    """Ответ на остановку A/B теста."""
    test_id: UUID = Field(..., description="ID теста")
    status: ABTestStatus = Field(..., description="Новый статус")
    end_time: datetime = Field(..., description="Время остановки")
    winner_variant_id: Optional[UUID] = Field(None, description="ID выбранного победителя")
    confidence_level: Optional[float] = Field(None, description="Уровень доверия результата")
