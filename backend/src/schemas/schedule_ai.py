"""
Pydantic schemas for AI scheduling features.
Feature: 015-smart-scheduling-auto-pilot-mode
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ==================== Enums ====================

class OptimizationStatus(str, Enum):
    """Статусы оптимизации расписания."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecommendationType(str, Enum):
    """Типы рекомендаций."""
    FILL_GAP = "fill_gap"
    PEAK_HOURS = "peak_hours"
    VARIETY = "variety"
    PERFORMANCE = "performance"
    CONFLICT = "conflict"


# ==================== Optimization Schemas ====================

class OptimizationParameters(BaseModel):
    """Параметры оптимизации расписания."""
    maximize_engagement: bool = Field(default=True, description="Максимизировать вовлеченность")
    minimize_gaps: bool = Field(default=True, description="Минимизировать пробелы")
    balance_variety: bool = Field(default=True, description="Балансировать разнообразие")
    respect_priority: bool = Field(default=True, description="Учитывать приоритеты")
    target_hours: Optional[int] = Field(default=24, description="Целевое количество часов")
    max_conflicts_to_resolve: Optional[int] = Field(default=10, description="Макс. конфликтов для разрешения")


class OptimizationMetrics(BaseModel):
    """Метрики оптимизации."""
    gap_hours: float = Field(..., description="Часы без контента")
    coverage_percent: float = Field(..., ge=0, le=100, description="Покрытие расписания (%)")
    engagement_score: float = Field(..., ge=0, le=10, description="Оценка вовлеченности (0-10)")
    variety_score: float = Field(..., ge=0, le=10, description="Оценка разнообразия (0-10)")
    conflicts_resolved: int = Field(..., ge=0, description="Разрешенных конфликтов")
    total_slots: int = Field(..., ge=0, description="Общее количество слотов")
    peak_hours_coverage: float = Field(..., ge=0, le=100, description="Покрытие пиковых часов (%)")


class ScheduleSlotSuggestion(BaseModel):
    """Предложение по слоту расписания."""
    action: Literal["add", "modify", "remove"] = Field(..., description="Действие")
    slot_id: Optional[str] = Field(None, description="ID слота (для modify/remove)")
    date: date = Field(..., description="Дата слота")
    start_time: str = Field(..., description="Время начала (HH:MM)")
    end_time: str = Field(..., description="Время окончания (HH:MM)")
    playlist_id: Optional[str] = Field(None, description="ID плейлиста")
    playlist_name: Optional[str] = Field(None, description="Название плейлиста")
    reason: str = Field(..., description="Обоснование")
    priority: int = Field(default=5, ge=0, le=10, description="Приоритет")
    expected_engagement: Optional[float] = Field(None, ge=0, le=10, description="Ожидаемая вовлеченность")


class AppliedChanges(BaseModel):
    """Результат применения оптимизации."""
    slots_created: int = Field(..., ge=0, description="Создано слотов")
    slots_modified: int = Field(..., ge=0, description="Модифицировано слотов")
    slots_removed: int = Field(..., ge=0, description="Удалено слотов")
    gaps_filled: int = Field(..., ge=0, description="Заполнено пробелов")
    conflicts_resolved: int = Field(..., ge=0, description="Разрешено конфликтов")


class ScheduleOptimizationRequest(BaseModel):
    """Запрос на оптимизацию расписания."""
    channel_id: str = Field(..., description="ID канала")
    start_date: date = Field(..., description="Начало периода")
    end_date: date = Field(..., description="Конец периода")
    parameters: OptimizationParameters = Field(default_factory=OptimizationParameters, description="Параметры оптимизации")


class ScheduleOptimizationResponse(BaseModel):
    """Результат оптимизации расписания."""
    id: str = Field(..., description="ID оптимизации")
    channel_id: str = Field(..., description="ID канала")
    start_date: date = Field(..., description="Начало периода")
    end_date: date = Field(..., description="Конец периода")
    status: OptimizationStatus = Field(..., description="Статус")
    metrics: Optional[OptimizationMetrics] = Field(None, description="Метрики оптимизации")
    suggestions: List[ScheduleSlotSuggestion] = Field(default_factory=list, description="Предложения")
    parameters: OptimizationParameters = Field(..., description="Параметры оптимизации")
    applied_changes: Optional[AppliedChanges] = Field(None, description="Примененные изменения")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")
    created_at: datetime = Field(..., description="Время создания")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")

    model_config = ConfigDict(from_attributes=True)


class ScheduleOptimizationPreview(BaseModel):
    """Превью оптимизации до применения."""
    optimization_id: str = Field(..., description="ID оптимизации")
    current_metrics: OptimizationMetrics = Field(..., description="Текущие метрики")
    optimized_metrics: OptimizationMetrics = Field(..., description="Оптимизированные метрики")
    suggestions: List[ScheduleSlotSuggestion] = Field(..., description="Предложения по изменению")
    estimated_improvement: Dict[str, float] = Field(..., description="Оценка улучшений")


# ==================== Recommendation Schemas ====================

class RecommendationMetadata(BaseModel):
    """Метаданные рекомендации."""
    similar_performances: List[str] = Field(default_factory=list, description="ID схожих плейлистов")
    avg_listeners_at_time: Optional[int] = Field(None, ge=0, description="Средние слушатели в это время")
    historical_engagement: Optional[float] = Field(None, ge=0, le=10, description="Историческая вовлеченность")
    trend: Optional[Literal["rising", "stable", "falling"]] = Field(None, description="Тренд")
    competitor_analysis: Optional[Dict[str, Any]] = Field(None, description="Анализ конкурентов")


class ScheduleRecommendationItem(BaseModel):
    """Элемент рекомендации."""
    id: str = Field(..., description="ID рекомендации")
    rec_type: RecommendationType = Field(..., description="Тип рекомендации")
    playlist_id: Optional[str] = Field(None, description="ID плейлиста")
    playlist_name: Optional[str] = Field(None, description="Название плейлиста")
    recommended_date: date = Field(..., description="Рекомендуемая дата")
    start_time: str = Field(..., description="Время начала (HH:MM)")
    end_time: str = Field(..., description="Время окончания (HH:MM)")
    confidence_score: float = Field(..., ge=0, le=100, description="Уверенность (0-100)")
    expected_engagement: Optional[float] = Field(None, ge=0, le=10, description="Ожидаемая вовлеченность")
    expected_listeners: Optional[int] = Field(None, ge=0, description="Прогноз слушателей")
    priority: int = Field(..., ge=0, description="Приоритет")
    title: str = Field(..., description="Заголовок")
    description: Optional[str] = Field(None, description="Описание")
    metadata: Optional[RecommendationMetadata] = Field(None, description="Метаданные")
    is_applied: bool = Field(default=False, description="Применена")
    is_dismissed: bool = Field(default=False, description="Отклонена")
    created_at: datetime = Field(..., description="Время создания")

    model_config = ConfigDict(from_attributes=True)


class ScheduleRecommendationRequest(BaseModel):
    """Запрос на получение рекомендаций."""
    channel_id: str = Field(..., description="ID канала")
    target_date: date = Field(..., description="Целевая дата")
    recommendation_types: Optional[List[RecommendationType]] = Field(
        default=None,
        description="Фильтр по типам рекомендаций"
    )
    max_recommendations: int = Field(default=10, ge=1, le=50, description="Макс. количество рекомендаций")
    min_confidence: float = Field(default=50.0, ge=0, le=100, description="Мин. уверенность")


class ScheduleRecommendationResponse(BaseModel):
    """Ответ с рекомендациями."""
    recommendations: List[ScheduleRecommendationItem] = Field(..., description="Список рекомендаций")
    total_count: int = Field(..., ge=0, description="Общее количество")
    high_confidence_count: int = Field(..., ge=0, description="Высокоуверенных рекомендаций")
    target_date: date = Field(..., description="Целевая дата")
    generated_at: datetime = Field(..., description="Время генерации")


class ApplyRecommendationRequest(BaseModel):
    """Запрос на применение рекомендации."""
    recommendation_id: str = Field(..., description="ID рекомендации")
    create_slot: bool = Field(default=True, description="Создать слот расписания")


# ==================== Peak Hours Schemas ====================

class PeakHoursDataPoint(BaseModel):
    """Точка данных пиковых часов."""
    day_of_week: int = Field(..., ge=0, le=6, description="День недели (0=Пн, 6=Вс)")
    hour: int = Field(..., ge=0, le=23, description="Час суток (0-23)")
    total_plays: int = Field(..., ge=0, description="Всего воспроизведений")
    avg_listeners: float = Field(..., ge=0, description="Средние слушатели")
    peak_listeners: int = Field(..., ge=0, description="Пиковые слушатели")
    avg_duration_seconds: int = Field(..., ge=0, description="Средняя длительность (сек)")
    unique_tracks_count: int = Field(..., ge=0, description="Уникальных треков")


class PeakHoursResponse(BaseModel):
    """Аналитика пиковых часов."""
    channel_id: str = Field(..., description="ID канала")
    period_start: date = Field(..., description="Начало периода")
    period_end: date = Field(..., description="Конец периода")
    sample_size: int = Field(..., ge=0, description="Размер выборки (дней)")
    peak_hours_data: List[PeakHoursDataPoint] = Field(..., description="Данные по часам")
    best_hours: List[Dict[str, Any]] = Field(..., description="Лучшие часы для контента")
    updated_at: datetime = Field(..., description="Время обновления")

    model_config = ConfigDict(from_attributes=True)


class PeakHoursRequest(BaseModel):
    """Запрос аналитики пиковых часов."""
    channel_id: str = Field(..., description="ID канала")
    period: Literal["7d", "30d", "90d"] = Field(default="30d", description="Период анализа")
    min_sample_size: int = Field(default=7, ge=1, description="Мин. размер выборки")


# ==================== Auto-Pilot Schemas ====================

class AutoPilotTemplate(BaseModel):
    """Шаблон для автопилота."""
    name: str = Field(..., description="Название шаблона")
    description: Optional[str] = Field(None, description="Описание")
    time_slots: List[Dict[str, Any]] = Field(..., description="Временные слоты")
    repeat_pattern: Optional[Literal["daily", "weekdays", "weekends", "custom"]] = Field(
        default="daily",
        description="Шаблон повторения"
    )
    repeat_days: Optional[List[int]] = Field(None, description="Дни повторения (0-6)")


class AutoPilotRequest(BaseModel):
    """Запрос на генерацию расписания автопилотом."""
    channel_id: str = Field(..., description="ID канала")
    date_range: Dict[str, str] = Field(..., description="Диапазон дат {start, end}")
    template: Optional[AutoPilotTemplate] = Field(None, description="Шаблон расписания")
    use_ai_recommendations: bool = Field(default=True, description="Использовать AI рекомендации")
    fill_gaps: bool = Field(default=True, description="Заполнять пробелы")
    resolve_conflicts: bool = Field(default=True, description="Разрешать конфликты")
    max_daily_hours: int = Field(default=24, ge=1, le=24, description="Макс. часов в день")


class AutoPilotResponse(BaseModel):
    """Результат генерации автопилота."""
    task_id: str = Field(..., description="ID фоновой задачи")
    channel_id: str = Field(..., description="ID канала")
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="Статус")
    date_range: Dict[str, str] = Field(..., description="Диапазон дат")
    slots_created: int = Field(default=0, ge=0, description="Создано слотов")
    gaps_filled: int = Field(default=0, ge=0, description="Заполнено пробелов")
    conflicts_resolved: int = Field(default=0, ge=0, description="Разрешено конфликтов")
    error_message: Optional[str] = Field(None, description="Ошибка")
    created_at: datetime = Field(..., description="Время создания")


class AutoPilotProgress(BaseModel):
    """Прогресс выполнения автопилота."""
    task_id: str = Field(..., description="ID задачи")
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="Статус")
    progress_percent: float = Field(..., ge=0, le=100, description="Прогресс (%)")
    current_day: Optional[date] = Field(None, description="Текущий день")
    total_days: int = Field(..., ge=0, description="Всего дней")
    slots_created: int = Field(..., ge=0, description="Создано слотов")
    estimated_remaining_seconds: Optional[int] = Field(None, ge=0, description="Осталось секунд")
    error_message: Optional[str] = Field(None, description="Ошибка")


# ==================== Conflict Resolution Schemas ====================

class ConflictInfo(BaseModel):
    """Информация о конфликте."""
    slot_id: str = Field(..., description="ID слота")
    title: Optional[str] = Field(None, description="Название")
    playlist_name: Optional[str] = Field(None, description="Плейлист")
    start_time: str = Field(..., description="Начало (HH:MM)")
    end_time: str = Field(..., description="Конец (HH:MM)")
    priority: int = Field(..., description="Приоритет")


class ScheduleConflict(BaseModel):
    """Конфликт в расписании."""
    date: date = Field(..., description="Дата конфликта")
    conflicts: List[ConflictInfo] = Field(..., description="Конфликтующие слоты")


class ConflictDetectionRequest(BaseModel):
    """Запрос на обнаружение конфликтов."""
    channel_id: str = Field(..., description="ID канала")
    start_date: date = Field(..., description="Начало периода")
    end_date: date = Field(..., description="Конец периода")


class ConflictDetectionResponse(BaseModel):
    """Результат обнаружения конфликтов."""
    channel_id: str = Field(..., description="ID канала")
    period: Dict[str, str] = Field(..., description="Период {start, end}")
    total_conflicts: int = Field(..., ge=0, description="Всего конфликтов")
    conflicts: List[ScheduleConflict] = Field(..., description="Список конфликтов")


class ConflictResolutionAction(BaseModel):
    """Действие по разрешению конфликта."""
    slot_id: str = Field(..., description="ID слота")
    action: Literal["keep", "remove", "modify_time", "lower_priority"] = Field(..., description="Действие")
    new_start_time: Optional[str] = Field(None, description="Новое начало (HH:MM)")
    new_end_time: Optional[str] = Field(None, description="Новый конец (HH:MM)")
    new_priority: Optional[int] = Field(None, ge=0, description="Новый приоритет")


class ConflictResolutionRequest(BaseModel):
    """Запрос на разрешение конфликтов."""
    channel_id: str = Field(..., description="ID канала")
    date: date = Field(..., description="Дата разрешения")
    resolutions: List[ConflictResolutionAction] = Field(..., description="Действия по разрешению")


class ConflictResolutionResponse(BaseModel):
    """Результат разрешения конфликтов."""
    channel_id: str = Field(..., description="ID канала")
    date: date = Field(..., description="Дата")
    resolutions_applied: int = Field(..., ge=0, description="Применено разрешений")
    slots_removed: int = Field(..., ge=0, description="Удалено слотов")
    slots_modified: int = Field(..., ge=0, description="Модифицировано слотов")
    remaining_conflicts: int = Field(..., ge=0, description="Осталось конфликтов")


# ==================== Gap Detection Schemas ====================

class ScheduleGap(BaseModel):
    """Пробел в расписании."""
    date: date = Field(..., description="Дата")
    start_time: str = Field(..., description="Начало пробела (HH:MM)")
    end_time: str = Field(..., description="Конец пробела (HH:MM)")
    duration_hours: float = Field(..., ge=0, description="Длительность (часы)")
    is_peak_hour: bool = Field(default=False, description="Пиковый час")


class GapDetectionRequest(BaseModel):
    """Запрос на обнаружение пробелов."""
    channel_id: str = Field(..., description="ID канала")
    start_date: date = Field(..., description="Начало периода")
    end_date: date = Field(..., description="Конец периода")
    consider_peak_hours: bool = Field(default=True, description="Учитывать пиковые часы")


class GapDetectionResponse(BaseModel):
    """Результат обнаружения пробелов."""
    channel_id: str = Field(..., description="ID канала")
    period: Dict[str, str] = Field(..., description="Период {start, end}")
    total_gap_hours: float = Field(..., ge=0, description="Всего часов пробелов")
    peak_hours_gap: float = Field(..., ge=0, description="Пробелов в пиковые часы")
    gaps: List[ScheduleGap] = Field(..., description="Список пробелов")
    fillable_gaps: int = Field(..., ge=0, description="Заполняемых пробелов")
