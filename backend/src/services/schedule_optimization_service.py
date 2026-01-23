"""
Schedule Optimization Service
Feature: 015-smart-scheduling-auto-pilot-mode

Сервис для оптимизации расписания трансляций:
- Обнаружение пробелов в расписании
- Расчет метрик оптимизации (покрытие, вовлеченность, разнообразие)
- Генерация предложений по улучшению расписания
- Обнаружение конфликтов (базовое)
- Кэширование через Redis
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from dataclasses import dataclass
from itertools import combinations

import numpy as np

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.schedule_optimization import (
    ScheduleOptimization,
    ScheduleRecommendation,
    OptimizationStatus
)
from src.models.schedule import ScheduleSlot, RepeatType
from src.models.playlist import Playlist
from src.models.analytics import TrackPlay
from src.schemas.schedule_ai import (
    ScheduleOptimizationRequest,
    ScheduleOptimizationResponse,
    ScheduleOptimizationPreview,
    OptimizationParameters,
    OptimizationMetrics,
    ScheduleSlotSuggestion,
    AppliedChanges,
    ScheduleGap,
    GapDetectionRequest,
    GapDetectionResponse,
    ScheduleConflict,
    ConflictDetectionRequest,
    ConflictDetectionResponse,
    ConflictInfo,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "schedule_optimization:"
CACHE_GAPS_KEY = f"{CACHE_PREFIX}gaps:{{channel_id}}:{{start_date}}:{{end_date}}"
CACHE_METRICS_KEY = f"{CACHE_PREFIX}metrics:{{channel_id}}:{{start_date}}:{{end_date}}"
CACHE_OPTIMIZATION_KEY = f"{CACHE_PREFIX}optimization:{{optimization_id}}"
CACHE_TTL = 900  # 15 minutes


@dataclass
class OptimizationObjective:
    """Цель оптимизации с весом."""
    name: str
    weight: float
    minimize: bool = False  # True if we want to minimize (e.g., gaps, conflicts)


@dataclass
class ScheduleSolution:
    """Решение оптимизации расписания."""
    suggestions: List[ScheduleSlotSuggestion]
    objective_scores: Dict[str, float]
    overall_score: float
    metrics: OptimizationMetrics


class MultiObjectiveOptimizer:
    """
    Многокритериальный оптимизатор расписания.

    Оптимизирует расписание по нескольким критериям:
    - Максимизация покрытия (coverage)
    - Максимизация вовлеченности (engagement)
    - Максимизация разнообразия (variety)
    - Минимизация конфликтов (conflicts)
    - Максимизация покрытия пиковых часов (peak_hours_coverage)

    Использует взвешенную сумму критериев для комбинированной оценки.
    """

    def __init__(self, objectives: Optional[List[OptimizationObjective]] = None):
        """
        Инициализация оптимизатора.

        Args:
            objectives: Список целей оптимизации с весами
        """
        self.objectives = objectives or self._default_objectives()

    def _default_objectives(self) -> List[OptimizationObjective]:
        """Цели оптимизации по умолчанию."""
        return [
            OptimizationObjective("coverage_percent", weight=0.25, minimize=False),
            OptimizationObjective("engagement_score", weight=0.30, minimize=False),
            OptimizationObjective("variety_score", weight=0.20, minimize=False),
            OptimizationObjective("conflicts_resolved", weight=0.15, minimize=True),
            OptimizationObjective("peak_hours_coverage", weight=0.10, minimize=False),
        ]

    def normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Нормализация оценок к диапазону [0, 1].

        Args:
            scores: Словарь с исходными оценками

        Returns:
            Нормализованные оценки
        """
        normalized = {}

        for obj in self.objectives:
            value = scores.get(obj.name, 0.0)

            # Специфичная нормализация для каждой метрики
            if obj.name == "coverage_percent":
                # Уже в процентах, нормализуем к [0, 1]
                normalized[obj.name] = min(1.0, value / 100.0)
            elif obj.name == "engagement_score":
                # Шкала 0-10, нормализуем к [0, 1]
                normalized[obj.name] = min(1.0, value / 10.0)
            elif obj.name == "variety_score":
                # Шкала 0-10, нормализуем к [0, 1]
                normalized[obj.name] = min(1.0, value / 10.0)
            elif obj.name == "conflicts_resolved":
                # Количество конфликтов, нормализуем: 0 конфликтов = 1.0
                # Используем обратную величину: 1 / (1 + conflicts)
                normalized[obj.name] = 1.0 / (1.0 + max(0, value))
            elif obj.name == "peak_hours_coverage":
                # Уже в процентах, нормализуем к [0, 1]
                normalized[obj.name] = min(1.0, value / 100.0)
            else:
                # Общая нормализация
                normalized[obj.name] = max(0.0, min(1.0, value))

        return normalized

    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """
        Расчет взвешенной оценки.

        Args:
            scores: Нормализованные оценки по критериям

        Returns:
            Взвешенная сумма оценок
        """
        total_score = 0.0
        total_weight = 0.0

        for obj in self.objectives:
            value = scores.get(obj.name, 0.0)
            total_score += obj.weight * value
            total_weight += obj.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def generate_pareto_front(
        self,
        solutions: List[ScheduleSolution]
    ) -> List[ScheduleSolution]:
        """
        Генерация фронта Парето (недоминируемых решений).

        Args:
            solutions: Список всех решений

        Returns:
            Список недоминируемых решений
        """
        if not solutions:
            return []

        pareto_front = []

        for sol1 in solutions:
            is_dominated = False

            for sol2 in solutions:
                if sol1 is sol2:
                    continue

                # Проверяем, доминирует ли sol2 над sol1
                # sol2 доминирует sol1, если по всем критериям не хуже
                # и хотя бы по одному критерию лучше
                dominates = True
                better_in_one = False

                for obj in self.objectives:
                    val1 = sol1.objective_scores.get(obj.name, 0.0)
                    val2 = sol2.objective_scores.get(obj.name, 0.0)

                    if obj.minimize:
                        # Для минимизации меньше = лучше
                        if val2 > val1:
                            dominates = False
                            break
                        elif val2 < val1:
                            better_in_one = True
                    else:
                        # Для максимизации больше = лучше
                        if val2 < val1:
                            dominates = False
                            break
                        elif val2 > val1:
                            better_in_one = True

                if dominates and better_in_one:
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_front.append(sol1)

        return pareto_front

    def rank_solutions(
        self,
        solutions: List[ScheduleSolution]
    ) -> List[ScheduleSolution]:
        """
        Ранжирование решений по взвешенной оценке.

        Args:
            solutions: Список решений

        Returns:
            Отсортированный список решений (лучшие сначала)
        """
        return sorted(
            solutions,
            key=lambda s: s.overall_score,
            reverse=True
        )


class ScheduleOptimizationService:
    """
    Сервис оптимизации расписания с Redis кэшированием.

    Методы:
    - detect_gaps: Обнаружение пробелов в расписании
    - calculate_metrics: Расчет метрик оптимизации
    - generate_suggestions: Генерация предложений по улучшению
    - detect_conflicts: Обнаружение конфликтов в расписании
    - create_optimization: Создание записи оптимизации
    - get_optimization: Получение результатов оптимизации
    """

    def __init__(self, db: Session, redis_client: Optional["aioredis.Redis"] = None):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
            redis_client: Опциональный Redis клиент для кэширования
        """
        self.db = db
        self.redis = redis_client

    async def _get_from_cache(self, key: str) -> Optional[dict]:
        """Получение данных из кэша Redis."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    async def _set_to_cache(self, key: str, data: dict, ttl: int = CACHE_TTL) -> None:
        """Сохранение данных в кэш Redis."""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    async def _invalidate_cache(self, channel_id: str) -> None:
        """Инвалидация кэша для канала."""
        if not self.redis:
            return
        try:
            # Удаляем все ключи с шаблоном для канала
            pattern = f"{CACHE_PREFIX}*:{channel_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis cache invalidation error: {e}")

    async def detect_gaps(
        self,
        request: GapDetectionRequest
    ) -> GapDetectionResponse:
        """
        Обнаружение пробелов в расписании.

        Args:
            request: Запрос на обнаружение пробелов

        Returns:
            GapDetectionResponse с найденными пробелами
        """
        cache_key = CACHE_GAPS_KEY.format(
            channel_id=request.channel_id,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat()
        )
        cached = await self._get_from_cache(cache_key)
        if cached:
            return GapDetectionResponse(**cached)

        # Получаем существующие слоты за период
        channel_uuid = UUID(request.channel_id)
        slots_query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.channel_id == channel_uuid,
                ScheduleSlot.start_date >= request.start_date,
                ScheduleSlot.start_date <= request.end_date,
                ScheduleSlot.is_active == True
            )
        ).order_by(ScheduleSlot.start_date, ScheduleSlot.start_time)

        slots = self.db.execute(slots_query).scalars().all()

        # Группируем слоты по датам
        slots_by_date: Dict[date, List[Tuple[time, time]]] = {}
        for slot in slots:
            slot_date = slot.start_date
            if slot_date not in slots_by_date:
                slots_by_date[slot_date] = []
            slots_by_date[slot_date].append((slot.start_time, slot.end_time))

        # Загружаем аналитику пиковых часов если нужно
        peak_hours_map = set()
        if request.consider_peak_hours:
            # Получаем пиковые часы за последние 30 дней
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            peak_query = select(
                func.date_part('dow', TrackPlay.played_at).label('dow'),
                func.date_part('hour', TrackPlay.played_at).label('hour')
            ).where(
                and_(
                    TrackPlay.played_at >= thirty_days_ago,
                    TrackPlay.listeners_count > 0
                )
            ).group_by(
                func.date_part('dow', TrackPlay.played_at),
                func.date_part('hour', TrackPlay.played_at)
            ).having(
                func.avg(TrackPlay.listeners_count) > 5.0
            )

            peak_rows = self.db.execute(peak_query).fetchall()
            peak_hours_map = {(int(row.dow), int(row.hour)) for row in peak_rows}

        # Находим пробелы
        gaps: List[ScheduleGap] = []
        total_gap_hours = 0.0
        peak_hours_gap = 0.0
        fillable_gaps = 0

        current_date = request.start_date
        while current_date <= request.end_date:
            day_slots = slots_by_date.get(current_date, [])

            # Сортируем слоты по времени
            day_slots.sort(key=lambda x: x[0])

            # Находим пробелы между слотами
            occupied_ranges = day_slots  # List of (start_time, end_time)
            free_ranges = self._find_free_ranges(occupied_ranges)

            for free_start, free_end in free_ranges:
                duration = (
                    free_end.hour - free_start.hour +
                    (free_end.minute - free_start.minute) / 60.0
                )

                # Пропускаем слишком короткие промежутки (< 30 минут)
                if duration < 0.5:
                    continue

                day_of_week = current_date.weekday()
                is_peak = False

                # Проверяем, попадает ли пробел в пиковые часы
                for hour in range(free_start.hour, free_end.hour):
                    if (day_of_week, hour) in peak_hours_map:
                        is_peak = True
                        peak_hours_gap += 1.0
                        break

                gap = ScheduleGap(
                    date=current_date,
                    start_time=free_start.strftime("%H:%M"),
                    end_time=free_end.strftime("%H:%M"),
                    duration_hours=round(duration, 2),
                    is_peak_hour=is_peak
                )
                gaps.append(gap)
                total_gap_hours += duration

                # Считаем заполняемые пробелы (длительностью от 1 часа)
                if duration >= 1.0:
                    fillable_gaps += 1

            current_date += timedelta(days=1)

        result = GapDetectionResponse(
            channel_id=request.channel_id,
            period={
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat()
            },
            total_gap_hours=round(total_gap_hours, 2),
            peak_hours_gap=round(peak_hours_gap, 2),
            gaps=gaps,
            fillable_gaps=fillable_gaps
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    def _find_free_ranges(
        self,
        occupied_ranges: List[Tuple[time, time]]
    ) -> List[Tuple[time, time]]:
        """
        Поиск свободных диапазонов времени.

        Args:
            occupied_ranges: Список занятых диапазонов (start_time, end_time)

        Returns:
            Список свободных диапазонов
        """
        if not occupied_ranges:
            # Весь день свободен
            return [(time(0, 0), time(23, 59))]

        # Сортируем по началу
        sorted_ranges = sorted(occupied_ranges, key=lambda x: x[0])

        free_ranges = []

        # Проверяем промежуток до первого слота
        first_start = sorted_ranges[0][0]
        if first_start > time(0, 0):
            free_ranges.append((time(0, 0), first_start))

        # Промежутки между слотами
        for i in range(len(sorted_ranges) - 1):
            current_end = sorted_ranges[i][1]
            next_start = sorted_ranges[i + 1][0]

            if next_start > current_end:
                free_ranges.append((current_end, next_start))

        # Промежуток после последнего слота
        last_end = sorted_ranges[-1][1]
        if last_end < time(23, 59):
            free_ranges.append((last_end, time(23, 59)))

        return free_ranges

    async def calculate_metrics(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        parameters: OptimizationParameters
    ) -> OptimizationMetrics:
        """
        Расчет метрик оптимизации расписания.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода
            parameters: Параметры оптимизации

        Returns:
            OptimizationMetrics с рассчитанными метриками
        """
        cache_key = CACHE_METRICS_KEY.format(
            channel_id=channel_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        cached = await self._get_from_cache(cache_key)
        if cached:
            return OptimizationMetrics(**cached)

        channel_uuid = UUID(channel_id)

        # Получаем слоты за период
        slots_query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.channel_id == channel_uuid,
                ScheduleSlot.start_date >= start_date,
                ScheduleSlot.start_date <= end_date,
                ScheduleSlot.is_active == True
            )
        )

        slots = self.db.execute(slots_query).scalars().all()
        total_slots = len(slots)

        # Вычисляем общее покрытие
        total_seconds = 0
        for slot in slots:
            duration = (
                slot.end_time.hour - slot.start_time.hour +
                (slot.end_time.minute - slot.start_time.minute) / 60.0
            ) * 3600
            total_seconds += duration

        period_days = (end_date - start_date).days + 1
        possible_hours = period_days * 24
        covered_hours = total_seconds / 3600.0
        gap_hours = possible_hours - covered_hours
        coverage_percent = (covered_hours / possible_hours * 100) if possible_hours > 0 else 0

        # Вычисляем оценку вовлеченности
        engagement_score = await self._calculate_engagement_score(
            channel_uuid, start_date, end_date
        )

        # Вычисляем оценку разнообразия
        variety_score = await self._calculate_variety_score(
            channel_uuid, slots
        )

        # Подсчитываем конфликты (базово)
        conflicts_resolved = await self._count_conflicts(
            channel_uuid, start_date, end_date
        )

        # Вычисляем покрытие пиковых часов
        peak_hours_coverage = await self._calculate_peak_hours_coverage(
            channel_uuid, slots, start_date, end_date
        )

        result = OptimizationMetrics(
            gap_hours=round(gap_hours, 2),
            coverage_percent=round(coverage_percent, 2),
            engagement_score=round(engagement_score, 2),
            variety_score=round(variety_score, 2),
            conflicts_resolved=conflicts_resolved,
            total_slots=total_slots,
            peak_hours_coverage=round(peak_hours_coverage, 2)
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result

    async def _calculate_engagement_score(
        self,
        channel_id: UUID,
        start_date: date,
        end_date: date
    ) -> float:
        """
        Расчет оценки вовлеченности на основе исторических данных.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Оценка вовлеченности (0-10)
        """
        # Получаем среднюю вовлеченность за период
        period_start = datetime.combine(start_date, time.min)
        period_end = datetime.combine(end_date, time.max)

        avg_listeners = self.db.execute(
            select(func.avg(TrackPlay.listeners_count)).where(
                and_(
                    TrackPlay.played_at >= period_start,
                    TrackPlay.played_at <= period_end
                )
            )
        ).scalar()

        if not avg_listeners:
            return 0.0

        # Нормализуем к шкале 0-10
        # Предполагаем, что 100+ слушателей = 10 баллов
        score = min(10.0, avg_listeners / 10.0)
        return score

    async def _calculate_variety_score(
        self,
        channel_id: UUID,
        slots: List[ScheduleSlot]
    ) -> float:
        """
        Расчет оценки разнообразия контента.

        Args:
            channel_id: ID канала
            slots: Список слотов

        Returns:
            Оценка разнообразия (0-10)
        """
        if not slots:
            return 0.0

        # Считаем уникальные плейлисты
        unique_playlists = set()
        for slot in slots:
            if slot.playlist_id:
                unique_playlists.add(slot.playlist_id)

        # Вычисляем соотношение уникальных плейлистов к общему количеству
        if len(slots) == 0:
            return 0.0

        variety_ratio = len(unique_playlists) / len(slots)

        # Нормализуем к шкале 0-10
        # Идеальное соотношение - 0.5 (каждый плейлист используется 2 раза в среднем)
        score = min(10.0, variety_ratio * 20.0)
        return score

    async def _count_conflicts(
        self,
        channel_id: UUID,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Подсчет конфликтов в расписании.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Количество конфликтов
        """
        # Получаем все слоты за период
        slots_query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.channel_id == channel_id,
                ScheduleSlot.start_date >= start_date,
                ScheduleSlot.start_date <= end_date,
                ScheduleSlot.is_active == True
            )
        ).order_by(ScheduleSlot.start_date, ScheduleSlot.start_time)

        slots = self.db.execute(slots_query).scalars().all()

        # Группируем по датам
        slots_by_date: Dict[date, List[ScheduleSlot]] = {}
        for slot in slots:
            slot_date = slot.start_date
            if slot_date not in slots_by_date:
                slots_by_date[slot_date] = []
            slots_by_date[slot_date].append(slot)

        # Подсчитываем пересечения
        conflicts = 0
        for day_slots in slots_by_date.values():
            for i, slot1 in enumerate(day_slots):
                for slot2 in day_slots[i + 1:]:
                    if self._slots_overlap(slot1, slot2):
                        conflicts += 1

        return conflicts

    def _slots_overlap(self, slot1: ScheduleSlot, slot2: ScheduleSlot) -> bool:
        """
        Проверка пересечения двух слотов.

        Args:
            slot1: Первый слот
            slot2: Второй слот

        Returns:
            True если слоты пересекаются
        """
        if slot1.start_date != slot2.start_date:
            return False

        # Проверяем пересечение по времени
        start1 = slot1.start_time.hour * 60 + slot1.start_time.minute
        end1 = slot1.end_time.hour * 60 + slot1.end_time.minute
        start2 = slot2.start_time.hour * 60 + slot2.start_time.minute
        end2 = slot2.end_time.hour * 60 + slot2.end_time.minute

        return not (end1 <= start2 or end2 <= start1)

    async def _calculate_peak_hours_coverage(
        self,
        channel_id: UUID,
        slots: List[ScheduleSlot],
        start_date: date,
        end_date: date
    ) -> float:
        """
        Расчет покрытия пиковых часов.

        Args:
            channel_id: ID канала
            slots: Список слотов
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Процент покрытия пиковых часов
        """
        # Получаем пиковые часы
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        peak_hours = self.db.execute(
            select(
                func.date_part('dow', TrackPlay.played_at).label('dow'),
                func.date_part('hour', TrackPlay.played_at).label('hour')
            ).where(
                and_(
                    TrackPlay.played_at >= thirty_days_ago,
                    TrackPlay.listeners_count > 0
                )
            ).group_by(
                func.date_part('dow', TrackPlay.played_at),
                func.date_part('hour', TrackPlay.played_at)
            ).having(
                func.avg(TrackPlay.listeners_count) > 5.0
            )
        ).fetchall()

        peak_hours_set = {(int(row.dow), int(row.hour)) for row in peak_hours}

        if not peak_hours_set:
            return 100.0  # Нет данных о пиковых часах

        # Считаем покрытие пиковых часов
        total_peak_hours = 0
        covered_peak_hours = 0

        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.weekday()

            for hour in range(24):
                if (day_of_week, hour) in peak_hours_set:
                    total_peak_hours += 1

                    # Проверяем, покрывается ли этот час слотом
                    for slot in slots:
                        if slot.start_date == current_date:
                            start_hour = slot.start_time.hour
                            end_hour = slot.end_time.hour
                            if start_hour <= hour < end_hour:
                                covered_peak_hours += 1
                                break

            current_date += timedelta(days=1)

        if total_peak_hours == 0:
            return 100.0

        return (covered_peak_hours / total_peak_hours) * 100.0

    async def detect_conflicts(
        self,
        request: ConflictDetectionRequest
    ) -> ConflictDetectionResponse:
        """
        Обнаружение конфликтов в расписании.

        Args:
            request: Запрос на обнаружение конфликтов

        Returns:
            ConflictDetectionResponse с найденными конфликтами
        """
        channel_uuid = UUID(request.channel_id)

        # Получаем слоты за период
        slots_query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.channel_id == channel_uuid,
                ScheduleSlot.start_date >= request.start_date,
                ScheduleSlot.start_date <= request.end_date,
                ScheduleSlot.is_active == True
            )
        ).order_by(ScheduleSlot.start_date, ScheduleSlot.start_time)

        slots = self.db.execute(slots_query).scalars().all()

        # Группируем по датам и ищем конфликты
        conflicts: List[ScheduleConflict] = []
        slots_by_date: Dict[date, List[ScheduleSlot]] = {}

        for slot in slots:
            slot_date = slot.start_date
            if slot_date not in slots_by_date:
                slots_by_date[slot_date] = []
            slots_by_date[slot_date].append(slot)

        for conflict_date, day_slots in slots_by_date.items():
            day_conflicts: List[ConflictInfo] = []

            for i, slot1 in enumerate(day_slots):
                for slot2 in day_slots[i + 1:]:
                    if self._slots_overlap(slot1, slot2):
                        # Добавляем информацию о конфликте для обоих слотов
                        for slot in [slot1, slot2]:
                            playlist = self.db.execute(
                                select(Playlist).where(Playlist.id == slot.playlist_id)
                            ).scalar_one_or_none()

                            day_conflicts.append(
                                ConflictInfo(
                                    slot_id=str(slot.id),
                                    title=slot.title,
                                    playlist_name=playlist.name if playlist else None,
                                    start_time=slot.start_time.strftime("%H:%M"),
                                    end_time=slot.end_time.strftime("%H:%M"),
                                    priority=slot.priority or 0
                                )
                            )

            if day_conflicts:
                conflicts.append(
                    ScheduleConflict(
                        date=conflict_date,
                        conflicts=day_conflicts
                    )
                )

        return ConflictDetectionResponse(
            channel_id=request.channel_id,
            period={
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat()
            },
            total_conflicts=len(conflicts),
            conflicts=conflicts
        )

    async def create_optimization(
        self,
        request: ScheduleOptimizationRequest,
        user_id: Optional[str] = None
    ) -> ScheduleOptimizationResponse:
        """
        Создание записи оптимизации расписания.

        Args:
            request: Запрос на оптимизацию
            user_id: Опциональный ID пользователя

        Returns:
            ScheduleOptimizationResponse с созданной оптимизацией
        """
        # Рассчитываем метрики
        metrics = await self.calculate_metrics(
            request.channel_id,
            request.start_date,
            request.end_date,
            request.parameters
        )

        # Создаем запись оптимизации
        optimization = ScheduleOptimization(
            channel_id=UUID(request.channel_id),
            user_id=UUID(user_id) if user_id else None,
            start_date=request.start_date,
            end_date=request.end_date,
            status=OptimizationStatus.PENDING,
            parameters=request.parameters.model_dump(),
            metrics=metrics.model_dump()
        )

        self.db.add(optimization)
        self.db.commit()
        self.db.refresh(optimization)

        # Инвалидируем кэш
        await self._invalidate_cache(request.channel_id)

        return ScheduleOptimizationResponse(
            id=str(optimization.id),
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date,
            status=OptimizationStatus.PENDING,
            metrics=metrics,
            suggestions=[],
            parameters=request.parameters,
            created_at=optimization.created_at
        )

    async def generate_optimization_suggestions(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        parameters: OptimizationParameters,
        num_candidates: int = 10
    ) -> List[ScheduleSlotSuggestion]:
        """
        Генерация предложений по оптимизации с использованием многокритериальной оптимизации.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода
            parameters: Параметры оптимизации
            num_candidates: Количество генерируемых кандидатов

        Returns:
            Список лучших предложений
        """
        # Создаем оптимизатор с настраиваемыми весами
        objectives = [
            OptimizationObjective("coverage_percent", weight=parameters.priority_coverage or 0.25, minimize=False),
            OptimizationObjective("engagement_score", weight=parameters.priority_engagement or 0.30, minimize=False),
            OptimizationObjective("variety_score", weight=parameters.priority_variety or 0.20, minimize=False),
            OptimizationObjective("conflicts_resolved", weight=parameters.priority_conflicts or 0.15, minimize=True),
            OptimizationObjective("peak_hours_coverage", weight=parameters.priority_peak_hours or 0.10, minimize=False),
        ]

        optimizer = MultiObjectiveOptimizer(objectives)

        # Генерируем кандидатов решений
        candidate_solutions = await self._generate_candidate_solutions(
            channel_id, start_date, end_date, parameters, num_candidates
        )

        if not candidate_solutions:
            return []

        # Ранжируем решения
        ranked_solutions = optimizer.rank_solutions(candidate_solutions)

        # Получаем лучшее решение
        best_solution = ranked_solutions[0]

        # Генерируем предложения на основе лучшего решения
        suggestions = await self._create_suggestions_from_solution(
            best_solution, channel_id
        )

        return suggestions

    async def _generate_candidate_solutions(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        parameters: OptimizationParameters,
        num_candidates: int
    ) -> List[ScheduleSolution]:
        """
        Генерация кандидатов решений для оптимизации.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода
            parameters: Параметры оптимизации
            num_candidates: Количество кандидатов

        Returns:
            Список решений
        """
        solutions = []
        channel_uuid = UUID(channel_id)

        # Получаем существующие слоты
        existing_slots_query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.channel_id == channel_uuid,
                ScheduleSlot.start_date >= start_date,
                ScheduleSlot.start_date <= end_date,
                ScheduleSlot.is_active == True
            )
        )
        existing_slots = self.db.execute(existing_slots_query).scalars().all()

        # Получаем доступные плейлисты
        playlists_query = select(Playlist).where(Playlist.is_active == True)
        available_playlists = self.db.execute(playlists_query).scalars().all()

        # Получаем пробелы в расписании
        gap_request = GapDetectionRequest(
            channel_id=channel_id,
            start_date=start_date,
            end_date=end_date,
            consider_peak_hours=True
        )
        gaps_response = await self.detect_gaps(gap_request)

        # Генерируем кандидатов с разными стратегиями
        strategies = [
            {"fill_gaps": True, "prioritize_peak": True, "max_variety": False},
            {"fill_gaps": True, "prioritize_peak": False, "max_variety": True},
            {"fill_gaps": True, "prioritize_peak": True, "max_variety": True},
            {"fill_gaps": False, "prioritize_peak": True, "max_variety": False},
        ]

        for i in range(num_candidates):
            # Выбираем стратегию
            strategy = strategies[i % len(strategies)]

            # Генерируем предложения для этой стратегии
            suggestions = await self._generate_suggestions_for_strategy(
                gaps_response.gaps,
                available_playlists,
                existing_slots,
                strategy,
                channel_uuid
            )

            # Вычисляем метрики для этого решения
            metrics = await self._calculate_metrics_for_suggestions(
                channel_uuid, start_date, end_date, suggestions, existing_slots
            )

            # Вычисляем оценки по критериям
            objective_scores = {
                "coverage_percent": metrics.coverage_percent,
                "engagement_score": metrics.engagement_score,
                "variety_score": metrics.variety_score,
                "conflicts_resolved": metrics.conflicts_resolved,
                "peak_hours_coverage": metrics.peak_hours_coverage,
            }

            # Нормализуем и вычисляем общую оценку
            optimizer = MultiObjectiveOptimizer()
            normalized_scores = optimizer.normalize_scores(objective_scores)
            overall_score = optimizer.calculate_weighted_score(normalized_scores)

            solution = ScheduleSolution(
                suggestions=suggestions,
                objective_scores=objective_scores,
                overall_score=overall_score,
                metrics=metrics
            )

            solutions.append(solution)

        return solutions

    async def _generate_suggestions_for_strategy(
        self,
        gaps: List[ScheduleGap],
        available_playlists: List[Playlist],
        existing_slots: List[ScheduleSlot],
        strategy: Dict[str, bool],
        channel_id: UUID
    ) -> List[ScheduleSlotSuggestion]:
        """
        Генерация предложений для конкретной стратегии.

        Args:
            gaps: Список пробелов
            available_playlists: Доступные плейлисты
            existing_slots: Существующие слоты
            strategy: Стратегия оптимизации
            channel_id: ID канала

        Returns:
            Список предложений
        """
        suggestions = []

        if not gaps or not available_playlists:
            return suggestions

        # Сортируем плейлисты в зависимости от стратегии
        if strategy["max_variety"]:
            # Максимизируем разнообразие - перемешиваем плейлисты
            playlists = list(available_playlists)
        else:
            # Используем плейлисты по порядку
            playlists = available_playlists

        playlist_idx = 0

        for gap in gaps:
            # Пропускаем слишком короткие пробелы
            if gap.duration_hours < 0.5:
                continue

            # Пропускаем непиковые часы если приоритет пиков
            if strategy["prioritize_peak"] and not gap.is_peak_hour:
                # Но заполняем некоторые непиковые часы (30%)
                import random
                if random.random() > 0.3:
                    continue

            # Выбираем плейлист
            playlist = playlists[playlist_idx % len(playlists)]
            playlist_idx += 1

            # Создаем предложение
            suggestion = ScheduleSlotSuggestion(
                title=playlist.name,
                date=gap.date,
                start_time=gap.start_time,
                end_time=gap.end_time,
                playlist_id=str(playlist.id),
                playlist_name=playlist.name,
                confidence=0.85 if gap.is_peak_hour else 0.70,
                reason=f"Заполнение пробела в {'пиковый' if gap.is_peak_hour else 'обычный'} час"
            )

            suggestions.append(suggestion)

        return suggestions

    async def _calculate_metrics_for_suggestions(
        self,
        channel_id: UUID,
        start_date: date,
        end_date: date,
        suggestions: List[ScheduleSlotSuggestion],
        existing_slots: List[ScheduleSlot]
    ) -> OptimizationMetrics:
        """
        Расчет метрик для набора предложений.

        Args:
            channel_id: ID канала
            start_date: Начало периода
            end_date: Конец периода
            suggestions: Предложения
            existing_slots: Существующие слоты

        Returns:
            Метрики оптимизации
        """
        # Создаем временные слоты на основе предложений
        temp_slots = list(existing_slots)

        for sug in suggestions:
            # Создаем временный слот
            start_time_parts = sug.start_time.split(":")
            end_time_parts = sug.end_time.split(":")

            temp_slot = ScheduleSlot(
                title=sug.title,
                channel_id=channel_id,
                start_date=sug.date,
                start_time=time(int(start_time_parts[0]), int(start_time_parts[1])),
                end_time=time(int(end_time_parts[0]), int(end_time_parts[1])),
                playlist_id=UUID(sug.playlist_id) if sug.playlist_id else None,
                is_active=False,  # Временный, неактивный
                priority=0
            )
            temp_slots.append(temp_slot)

        # Вычисляем метрики
        parameters = OptimizationParameters()  # Используем параметры по умолчанию
        metrics = await self.calculate_metrics(
            str(channel_id), start_date, end_date, parameters
        )

        return metrics

    async def _create_suggestions_from_solution(
        self,
        solution: ScheduleSolution,
        channel_id: str
    ) -> List[ScheduleSlotSuggestion]:
        """
        Создание предложений из решения.

        Args:
            solution: Решение оптимизации
            channel_id: ID канала

        Returns:
            Список предложений
        """
        return solution.suggestions

    async def get_optimization(
        self,
        optimization_id: str
    ) -> Optional[ScheduleOptimizationResponse]:
        """
        Получение результатов оптимизации.

        Args:
            optimization_id: ID оптимизации

        Returns:
            ScheduleOptimizationResponse или None
        """
        cache_key = CACHE_OPTIMIZATION_KEY.format(optimization_id=optimization_id)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ScheduleOptimizationResponse(**cached)

        optimization = self.db.execute(
            select(ScheduleOptimization).where(
                ScheduleOptimization.id == UUID(optimization_id)
            )
        ).scalar_one_or_none()

        if not optimization:
            return None

        # Формируем предложения
        suggestions = []
        if optimization.suggestions:
            for sug in optimization.suggestions:
                suggestions.append(
                    ScheduleSlotSuggestion(**sug)
                )

        # Формируем метрики
        metrics = None
        if optimization.metrics:
            metrics = OptimizationMetrics(**optimization.metrics)

        # Формируем примененные изменения
        applied_changes = None
        if optimization.applied_changes:
            applied_changes = AppliedChanges(**optimization.applied_changes)

        result = ScheduleOptimizationResponse(
            id=str(optimization.id),
            channel_id=str(optimization.channel_id),
            start_date=optimization.start_date,
            end_date=optimization.end_date,
            status=optimization.status,
            metrics=metrics,
            suggestions=suggestions,
            parameters=OptimizationParameters(**optimization.parameters),
            applied_changes=applied_changes,
            error_message=optimization.error_message,
            warnings=optimization.warnings or [],
            created_at=optimization.created_at,
            completed_at=optimization.completed_at
        )

        await self._set_to_cache(cache_key, result.model_dump())
        return result


def get_schedule_optimization_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> ScheduleOptimizationService:
    """
    Фабрика для создания сервиса оптимизации расписания.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент

    Returns:
        ScheduleOptimizationService instance
    """
    return ScheduleOptimizationService(db=db, redis_client=redis_client)
