"""
A/B Testing Service
Feature: 016-a-b-testing-framework-for-content

Сервис для управления A/B тестированием контента:
- Создание и управление тестами
- Распределение трафика между вариантами
- Отслеживание метрик
- Статистический анализ результатов
"""

import json
import logging
import uuid
import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.ab_testing import ABTest, ABTestVariant, ABTestMetric, ABTestStatus
from src.schemas.ab_testing import (
    ABTestCreate,
    ABTestUpdate,
    ABTestResponse,
    ABTestListResponse,
    ABTestCollectionResponse,
    ABTestVariantResponse,
    ABTestMetricCreate,
    ABTestMetricResponse,
    ABTestStartResponse,
    ABTestStopResponse,
    ABTestStatistics,
    ABTestAnalysisResponse,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis cache keys
CACHE_PREFIX = "ab_testing:"
CACHE_TEST_KEY = f"{CACHE_PREFIX}test:{{test_id}}"
CACHE_ACTIVE_TESTS_KEY = f"{CACHE_PREFIX}active_tests:{{channel_id}}"
CACHE_TRAFFIC_SPLIT_KEY = f"{CACHE_PREFIX}traffic:{{test_id}}:{{user_id}}"
CACHE_TTL = 300  # 5 minutes


class ABTestingService:
    """
    Сервис для управления A/B тестами.

    Методы:
    - create_test: Создание нового A/B теста
    - get_test: Получение теста по ID
    - list_tests: Список тестов с фильтрацией
    - update_test: Обновление метаданных теста
    - delete_test: Удаление теста
    - start_test: Запуск теста
    - stop_test: Остановка теста с выбором победителя
    - assign_variant: Распределение пользователя по варианту
    - record_metric: Запись метрики для варианта
    - analyze_test: Статистический анализ теста
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

    async def _invalidate_cache(self, test_id: UUID, channel_id: Optional[UUID] = None) -> None:
        """Инвалидация кэша для теста."""
        if not self.redis:
            return
        try:
            await self.redis.delete(CACHE_TEST_KEY.format(test_id=str(test_id)))
            if channel_id:
                await self.redis.delete(CACHE_ACTIVE_TESTS_KEY.format(channel_id=str(channel_id)))
        except Exception as e:
            logger.warning(f"Redis cache invalidation error: {e}")

    def _validate_traffic_allocation(self, variants: List[Dict[str, Any]]) -> bool:
        """
        Проверка корректности распределения трафика.

        Args:
            variants: Список вариантов с полями traffic_allocation

        Returns:
            True если распределение валидно

        Raises:
            ValueError: Если распределение некорректно
        """
        if not variants:
            raise ValueError("Должен быть хотя бы один вариант")

        total = sum(v.get("traffic_allocation", 0) for v in variants)

        if total == 0:
            raise ValueError("Суммарное распределение трафика не может быть 0")

        if total != 100:
            raise ValueError(f"Суммарное распределение трафика должно быть 100%, получено {total}%")

        # Проверка диапазонов
        for v in variants:
            alloc = v.get("traffic_allocation", 0)
            if not (0 <= alloc <= 100):
                raise ValueError(f"Распределение трафика должно быть 0-100%, получено {alloc}%")

        return True

    async def create_test(self, test_data: ABTestCreate, created_by: Optional[UUID] = None) -> ABTestResponse:
        """
        Создание нового A/B теста.

        Args:
            test_data: Данные для создания теста
            created_by: ID пользователя создателя

        Returns:
            ABTestResponse с созданным тестом

        Raises:
            ValueError: Если данные некорректны
        """
        # Валидация вариантов
        variants_data = [v.model_dump() for v in test_data.variants]
        self._validate_traffic_allocation(variants_data)

        # Создание теста
        test = ABTest(
            channel_id=test_data.channel_id,
            name=test_data.name,
            description=test_data.description,
            hypothesis=test_data.hypothesis,
            planned_duration_hours=test_data.planned_duration_hours,
            traffic_config=test_data.traffic_config,
            status=ABTestStatus.DRAFT,
            created_by=created_by,
        )

        self.db.add(test)
        self.db.flush()  # Чтобы получить test.id

        # Создание вариантов
        variants_responses = []
        for idx, variant_data in enumerate(test_data.variants):
            variant = ABTestVariant(
                test_id=test.id,
                name=variant_data.name,
                description=variant_data.description,
                traffic_allocation=variant_data.traffic_allocation,
                configuration=variant_data.configuration,
                position=variant_data.position,
            )
            self.db.add(variant)
            self.db.flush()

            variants_responses.append(
                ABTestVariantResponse(
                    id=variant.id,
                    test_id=variant.test_id,
                    position=variant.position,
                    name=variant.name,
                    description=variant.description,
                    traffic_allocation=variant.traffic_allocation,
                    configuration=variant.configuration,
                    is_winner=variant.is_winner,
                    conversion_rate=None,
                    improvement=None,
                    created_at=variant.created_at,
                    updated_at=variant.updated_at,
                )
            )

        self.db.commit()
        self.db.refresh(test)

        response = ABTestResponse(
            id=test.id,
            channel_id=test.channel_id,
            name=test.name,
            description=test.description,
            hypothesis=test.hypothesis,
            status=test.status.value,
            start_time=test.start_time,
            end_time=test.end_time,
            planned_duration_hours=test.planned_duration_hours,
            traffic_config=test.traffic_config,
            winner_variant_id=test.winner_variant_id,
            confidence_level=float(test.confidence_level) if test.confidence_level else None,
            is_significant=test.is_significant,
            created_at=test.created_at,
            updated_at=test.updated_at,
            created_by=test.created_by,
            variants=variants_responses,
        )

        # Кэширование
        await self._set_to_cache(
            CACHE_TEST_KEY.format(test_id=str(test.id)),
            response.model_dump(),
        )

        logger.info(f"Created A/B test {test.id}: {test.name}")
        return response

    async def get_test(self, test_id: UUID) -> Optional[ABTestResponse]:
        """
        Получение теста по ID.

        Args:
            test_id: ID теста

        Returns:
            ABTestResponse или None если не найден
        """
        # Проверка кэша
        cache_key = CACHE_TEST_KEY.format(test_id=str(test_id))
        cached = await self._get_from_cache(cache_key)
        if cached:
            return ABTestResponse(**cached)

        # Запрос из БД
        query = select(ABTest).where(ABTest.id == test_id)
        test = self.db.execute(query).scalar_one_or_none()

        if not test:
            return None

        # Загрузка вариантов
        variants_query = select(ABTestVariant).where(
            ABTestVariant.test_id == test_id
        ).order_by(ABTestVariant.position)
        variants = self.db.execute(variants_query).scalars().all()

        variants_responses = [
            ABTestVariantResponse(
                id=v.id,
                test_id=v.test_id,
                position=v.position,
                name=v.name,
                description=v.description,
                traffic_allocation=v.traffic_allocation,
                configuration=v.configuration,
                is_winner=v.is_winner,
                conversion_rate=float(v.conversion_rate) if v.conversion_rate else None,
                improvement=float(v.improvement) if v.improvement else None,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
            for v in variants
        ]

        response = ABTestResponse(
            id=test.id,
            channel_id=test.channel_id,
            name=test.name,
            description=test.description,
            hypothesis=test.hypothesis,
            status=test.status.value,
            start_time=test.start_time,
            end_time=test.end_time,
            planned_duration_hours=test.planned_duration_hours,
            traffic_config=test.traffic_config,
            winner_variant_id=test.winner_variant_id,
            confidence_level=float(test.confidence_level) if test.confidence_level else None,
            is_significant=test.is_significant,
            created_at=test.created_at,
            updated_at=test.updated_at,
            created_by=test.created_by,
            variants=variants_responses,
        )

        await self._set_to_cache(cache_key, response.model_dump())
        return response

    async def list_tests(
        self,
        channel_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ABTestCollectionResponse:
        """
        Список тестов с фильтрацией.

        Args:
            channel_id: Фильтр по каналу
            status: Фильтр по статусу
            limit: Максимальное количество результатов
            offset: Смещение для пагинации

        Returns:
            ABTestCollectionResponse со списком тестов
        """
        query = select(ABTest)

        if channel_id:
            query = query.where(ABTest.channel_id == channel_id)
        if status:
            query = query.where(ABTest.status == status)

        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Получение данных с пагинацией
        query = query.order_by(desc(ABTest.created_at)).limit(limit).offset(offset)
        tests = self.db.execute(query).scalars().all()

        test_responses = []
        for test in tests:
            # Подсчет вариантов
            variant_count = self.db.execute(
                select(func.count()).where(ABTestVariant.test_id == test.id)
            ).scalar() or 0

            test_responses.append(
                ABTestListResponse(
                    id=test.id,
                    channel_id=test.channel_id,
                    name=test.name,
                    status=test.status.value,
                    start_time=test.start_time,
                    end_time=test.end_time,
                    winner_variant_id=test.winner_variant_id,
                    is_significant=test.is_significant,
                    created_at=test.created_at,
                    variant_count=variant_count,
                )
            )

        return ABTestCollectionResponse(tests=test_responses, total=total)

    async def update_test(self, test_id: UUID, test_data: ABTestUpdate) -> Optional[ABTestResponse]:
        """
        Обновление метаданных теста.

        Args:
            test_id: ID теста
            test_data: Данные для обновления

        Returns:
            Обновленный ABTestResponse или None

        Raises:
            ValueError: Если тест уже запущен
        """
        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            return None

        # Можно обновлять только черновики
        if test.status != ABTestStatus.DRAFT:
            raise ValueError(f"Можно обновлять только тесты в статусе draft, текущий статус: {test.status.value}")

        # Обновление полей
        if test_data.name is not None:
            test.name = test_data.name
        if test_data.description is not None:
            test.description = test_data.description
        if test_data.hypothesis is not None:
            test.hypothesis = test_data.hypothesis
        if test_data.planned_duration_hours is not None:
            test.planned_duration_hours = test_data.planned_duration_hours
        if test_data.traffic_config is not None:
            test.traffic_config = test_data.traffic_config

        self.db.commit()
        self.db.refresh(test)

        # Инвалидация кэша
        await self._invalidate_cache(test_id, test.channel_id)

        return await self.get_test(test_id)

    async def delete_test(self, test_id: UUID) -> bool:
        """
        Удаление теста.

        Args:
            test_id: ID теста

        Returns:
            True если удален, False если не найден

        Raises:
            ValueError: Если тест запущен
        """
        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            return False

        # Можно удалять только черновики
        if test.status == ABTestStatus.RUNNING:
            raise ValueError("Нельзя удалять запущенный тест. Сначала остановите его.")

        # Каскадное удаление сработает автоматически
        self.db.delete(test)
        self.db.commit()

        # Инвалидация кэша
        await self._invalidate_cache(test_id, test.channel_id)

        logger.info(f"Deleted A/B test {test_id}")
        return True

    async def start_test(self, test_id: UUID) -> ABTestStartResponse:
        """
        Запуск A/B теста.

        Args:
            test_id: ID теста

        Returns:
            ABTestStartResponse с данными запуска

        Raises:
            ValueError: Если тест нельзя запустить
        """
        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            raise ValueError(f"Тест {test_id} не найден")

        if test.status != ABTestStatus.DRAFT and test.status != ABTestStatus.PAUSED:
            raise ValueError(f"Можно запустить только тест в статусе draft или paused, текущий: {test.status.value}")

        # Проверка наличия вариантов
        variant_count = self.db.execute(
            select(func.count()).where(ABTestVariant.test_id == test_id)
        ).scalar() or 0

        if variant_count < 2:
            raise ValueError("Для запуска теста нужно минимум 2 варианта")

        # Запуск теста
        test.status = ABTestStatus.RUNNING
        if test.start_time is None:
            test.start_time = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(test)

        # Инвалидация кэша
        await self._invalidate_cache(test_id, test.channel_id)

        logger.info(f"Started A/B test {test_id}")

        return ABTestStartResponse(
            test_id=test.id,
            status=test.status.value,
            start_time=test.start_time,
        )

    async def stop_test(
        self,
        test_id: UUID,
        select_winner: bool = True,
        winner_variant_id: Optional[UUID] = None,
    ) -> ABTestStopResponse:
        """
        Остановка A/B теста.

        Args:
            test_id: ID теста
            select_winner: Выбрать ли победителя автоматически
            winner_variant_id: ID варианта-победителя (если задан вручную)

        Returns:
            ABTestStopResponse с результатами

        Raises:
            ValueError: Если тест не запущен
        """
        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            raise ValueError(f"Тест {test_id} не найден")

        if test.status != ABTestStatus.RUNNING:
            raise ValueError(f"Можно остановить только запущенный тест, текущий статус: {test.status.value}")

        # Остановка теста
        test.status = ABTestStatus.STOPPED
        test.end_time = datetime.now(timezone.utc)

        selected_winner_id = winner_variant_id
        confidence = None

        # Выбор победителя
        if select_winner and not winner_variant_id:
            # Анализ и автоматический выбор (placeholder, будет реализован в subtask-2-2)
            analysis = await self.analyze_test(test_id)
            selected_winner_id = analysis.winner_variant_id
            confidence = analysis.confidence_level

            if analysis.is_significant and selected_winner_id:
                test.winner_variant_id = selected_winner_id
                test.confidence_level = Decimal(str(confidence))
                test.is_significant = True

                # Обновление флага is_winner у варианта
                self.db.execute(
                    update(ABTestVariant)
                    .where(ABTestVariant.id == selected_winner_id)
                    .values(is_winner=True)
                )
        elif winner_variant_id:
            # Ручной выбор победителя
            test.winner_variant_id = winner_variant_id

        self.db.commit()
        self.db.refresh(test)

        # Инвалидация кэша
        await self._invalidate_cache(test_id, test.channel_id)

        logger.info(f"Stopped A/B test {test_id}, winner: {selected_winner_id}")

        return ABTestStopResponse(
            test_id=test.id,
            status=test.status.value,
            end_time=test.end_time,
            winner_variant_id=selected_winner_id,
            confidence_level=float(confidence) if confidence else None,
        )

    async def assign_variant(
        self,
        test_id: UUID,
        user_id: Optional[UUID] = None,
        force_variant_id: Optional[UUID] = None,
    ) -> Optional[UUID]:
        """
        Распределение пользователя по варианту теста.

        Args:
            test_id: ID теста
            user_id: ID пользователя (для консистентного распределения)
            force_variant_id: Принудительно назначенный вариант (для тестирования)

        Returns:
            ID варианта или None если тест не активен

        Raises:
            ValueError: Если тест не найден или не запущен
        """
        # Проверка кэша для консистентности
        if user_id:
            cache_key = CACHE_TRAFFIC_SPLIT_KEY.format(test_id=str(test_id), user_id=str(user_id))
            cached = await self._get_from_cache(cache_key)
            if cached:
                return UUID(cached.get("variant_id"))

        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            raise ValueError(f"Тест {test_id} не найден")

        if test.status != ABTestStatus.RUNNING:
            return None

        # Получение вариантов
        variants_query = select(ABTestVariant).where(
            ABTestVariant.test_id == test_id
        ).order_by(ABTestVariant.position)
        variants = self.db.execute(variants_query).scalars().all()

        if not variants:
            return None

        # Принудительное назначение (для тестирования)
        if force_variant_id:
            assigned_variant_id = force_variant_id
        else:
            # Взвешенное случайное распределение
            import random
            weights = [v.traffic_allocation for v in variants]
            chosen_variant = random.choices(variants, weights=weights, k=1)[0]
            assigned_variant_id = chosen_variant.id

        # Кэширование назначения (для консистентности)
        if user_id:
            cache_key = CACHE_TRAFFIC_SPLIT_KEY.format(test_id=str(test_id), user_id=str(user_id))
            await self._set_to_cache(
                cache_key,
                {"variant_id": str(assigned_variant_id)},
                ttl=86400,  # 24 часа
            )

        return assigned_variant_id

    async def record_metric(self, metric_data: ABTestMetricCreate) -> ABTestMetricResponse:
        """
        Запись метрики для варианта.

        Args:
            metric_data: Данные метрики

        Returns:
            ABTestMetricResponse с записанной метрикой

        Raises:
            ValueError: Если вариант не найден
        """
        variant = self.db.execute(
            select(ABTestVariant).where(ABTestVariant.id == metric_data.variant_id)
        ).scalar_one_or_none()

        if not variant:
            raise ValueError(f"Вариант {metric_data.variant_id} не найден")

        # Создание метрики
        metric = ABTestMetric(
            variant_id=metric_data.variant_id,
            metric_type=metric_data.metric_type,
            metric_value=metric_data.metric_value,
            metadata=metric_data.metadata,
            recorded_at=datetime.now(timezone.utc),
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)

        # Инвалидация кэша теста
        await self._invalidate_cache(variant.test_id)

        return ABTestMetricResponse(
            id=metric.id,
            variant_id=metric.variant_id,
            metric_type=metric.metric_type,
            metric_value=metric.metric_value,
            recorded_at=metric.recorded_at,
            metadata=metric.metadata,
        )

    async def analyze_test(self, test_id: UUID, confidence_level: float = 0.95) -> ABTestAnalysisResponse:
        """
        Статистический анализ A/B теста.

        Args:
            test_id: ID теста
            confidence_level: Уровень доверия (по умолчанию 0.95)

        Returns:
            ABTestAnalysisResponse с результатами анализа

        Raises:
            ValueError: Если тест не найден
        """
        test = self.db.execute(select(ABTest).where(ABTest.id == test_id)).scalar_one_or_none()

        if not test:
            raise ValueError(f"Тест {test_id} не найден")

        # Получение вариантов с метриками
        variants_query = select(ABTestVariant).where(
            ABTestVariant.test_id == test_id
        ).order_by(ABTestVariant.position)
        variants = self.db.execute(variants_query).scalars().all()

        variant_stats = []

        for variant in variants:
            # Агрегация метрик по варианту
            impressions = self.db.execute(
                select(func.sum(ABTestMetric.metric_value)).where(
                    and_(
                        ABTestMetric.variant_id == variant.id,
                        ABTestMetric.metric_type == "impressions"
                    )
                )
            ).scalar() or 0

            conversions = self.db.execute(
                select(func.sum(ABTestMetric.metric_value)).where(
                    and_(
                        ABTestMetric.variant_id == variant.id,
                        ABTestMetric.metric_type == "conversions"
                    )
                )
            ).scalar() or 0

            # Конверсия
            conversion_rate = float(conversions) / float(impressions) if impressions > 0 else 0.0

            # Расчет доверительного интервала
            ci_lower, ci_upper = await self.calculate_confidence_interval(
                conversions=int(conversions),
                total=int(impressions),
                confidence_level=confidence_level,
            )

            stats = ABTestStatistics(
                variant_id=variant.id,
                variant_name=variant.name,
                impressions=int(impressions),
                conversions=int(conversions),
                conversion_rate=conversion_rate,
                confidence_interval_lower=ci_lower,
                confidence_interval_upper=ci_upper,
            )
            variant_stats.append(stats)

        # Определение победителя и расчет статистической значимости
        winner_id = None
        p_value = None
        z_score = None
        is_significant = False

        if len(variant_stats) >= 2:
            # Сортируем варианты по конверсии
            sorted_variants = sorted(variant_stats, key=lambda x: x.conversion_rate, reverse=True)
            winner = sorted_variants[0]
            runner_up = sorted_variants[1]

            winner_id = winner.variant_id

            # Расчет статистической значимости между победителем и вторым местом
            if winner.impressions > 0 and runner_up.impressions > 0:
                is_significant, p_value, z_score = await self.calculate_statistical_significance(
                    control_conversions=runner_up.conversions,
                    control_total=runner_up.impressions,
                    treatment_conversions=winner.conversions,
                    treatment_total=winner.impressions,
                    confidence_level=confidence_level,
                )

                # Расчет относительного улучшения
                if runner_up.conversion_rate > 0:
                    winner.improvement = (
                        (winner.conversion_rate - runner_up.conversion_rate) /
                        runner_up.conversion_rate
                    )
                elif winner.conversion_rate > 0:
                    winner.improvement = 1.0  # 100% улучшение от 0
                else:
                    winner.improvement = 0.0

        elif len(variant_stats) == 1:
            # Только один вариант
            winner_id = variant_stats[0].variant_id

        # Рекомендация
        if is_significant and winner_id:
            recommended_action = f"Implement variant {winner_id} - statistically significant winner"
        elif p_value and p_value < 0.1:
            recommended_action = f"Trending towards variant {winner_id} - consider more traffic"
        elif len(variant_stats) >= 2:
            recommended_action = "Continue testing - no statistically significant winner yet"
        else:
            recommended_action = "Insufficient data for recommendation"

        response = ABTestAnalysisResponse(
            test_id=test.id,
            test_name=test.name,
            status=test.status.value,
            variants=variant_stats,
            winner_variant_id=winner_id,
            confidence_level=confidence_level * 100,  # Convert to percentage
            is_significant=is_significant,
            p_value=p_value,
            recommended_action=recommended_action,
            analyzed_at=datetime.now(timezone.utc),
        )

        return response

    def _get_z_critical(self, confidence_level: float) -> float:
        """
        Получение Z-критического значения для уровня доверия.

        Args:
            confidence_level: Уровень доверия (0.0 - 1.0)

        Returns:
            Z-критическое значение
        """
        # Стандартные z-значения для распространенных уровней доверия
        z_values = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }

        if confidence_level in z_values:
            return z_values[confidence_level]

        # Для других значений используем приближение через обратную функцию стандартного нормального распределения
        # Используем аппроксимацию Абрамовица и Стегуна
        alpha = 1.0 - confidence_level

        if alpha >= 1.0 or alpha <= 0.0:
            return 1.96  # Default to 95%

        # Двусторонний тест
        alpha = alpha / 2.0

        # Аппроксимация
        if alpha >= 0.5:
            return 0.0

        t = math.sqrt(-2.0 * math.log(alpha))
        c0 = 2.515517
        c1 = 0.802853
        c2 = 0.010328
        d1 = 1.432788
        d2 = 0.189269
        d3 = 0.001308

        numerator = c0 + c1 * t + c2 * t * t
        denominator = 1.0 + d1 * t + d2 * t * t + d3 * t * t * t
        z_score = t - numerator / denominator

        return z_score

    def _calculate_p_value(self, z_score: float, two_tailed: bool = True) -> float:
        """
        Расчет p-value из z-оценки.

        Args:
            z_score: Z-оценка
            two_tailed: Двусторонний тест

        Returns:
            p-value
        """
        # Стандартная нормальная CDF (кумулятивная функция распределения)
        def normal_cdf(x: float) -> float:
            """Аппроксимация стандартной нормальной CDF."""
            a1 = 0.254829592
            a2 = -0.284496736
            a3 = 1.421413741
            a4 = -1.453152027
            a5 = 1.061405429
            p = 0.3275911

            sign = 1.0 if x >= 0 else -1.0
            x = abs(x) / math.sqrt(2.0)

            t = 1.0 / (1.0 + p * x)
            y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

            return 0.5 * (1.0 + sign * y)

        if two_tailed:
            return 2.0 * (1.0 - normal_cdf(abs(z_score)))
        else:
            return 1.0 - normal_cdf(z_score)

    async def calculate_statistical_significance(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        confidence_level: float = 0.95,
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """
        Расчет статистической значимости (z-test для двух пропорций).

        Args:
            control_conversions: Конверсии контрольной группы
            control_total: Размер контрольной группы
            treatment_conversions: Конверсии тестовой группы
            treatment_total: Размер тестовой группы
            confidence_level: Уровень доверия (по умолчанию 0.95)

        Returns:
            (is_significant, p_value, z_score)

        Raises:
            ValueError: Если входные данные некорректны
        """
        # Валидация входных данных
        if control_total <= 0 or treatment_total <= 0:
            raise ValueError("Размер выборки должен быть положительным")

        if control_conversions < 0 or treatment_conversions < 0:
            raise ValueError("Количество конверсий не может быть отрицательным")

        if control_conversions > control_total or treatment_conversions > treatment_total:
            raise ValueError("Конверсии не могут превышать размер выборки")

        # Если выборки слишком маленькие, тест не надежен
        if control_total < 30 or treatment_total < 30:
            logger.warning(
                f"Маленькая выборка для z-test: control={control_total}, treatment={treatment_total}. "
                "Результаты могут быть ненадежными."
            )

        # Расчет конверсионных ставок
        p1 = float(control_conversions) / float(control_total) if control_total > 0 else 0.0
        p2 = float(treatment_conversions) / float(treatment_total) if treatment_total > 0 else 0.0

        # Объединенная пропорция (pooled proportion)
        pooled_p = float(control_conversions + treatment_conversions) / float(control_total + treatment_total)

        # Стандартная ошибка разности пропорций
        se = math.sqrt(
            pooled_p * (1.0 - pooled_p) * (1.0 / control_total + 1.0 / treatment_total)
        ) if (pooled_p > 0 and pooled_p < 1) else 0.0

        if se == 0.0:
            # Избегаем деления на ноль
            return False, None, None

        # Z-оценка
        z_score = (p2 - p1) / se

        # P-value (двусторонний тест)
        p_value = self._calculate_p_value(z_score, two_tailed=True)

        # Проверка значимости
        alpha = 1.0 - confidence_level
        is_significant = p_value is not None and p_value < alpha

        logger.debug(
            f"Z-test: p1={p1:.4f}, p2={p2:.4f}, z={z_score:.4f}, p={p_value:.4f}, "
            f"significant={is_significant}"
        )

        return is_significant, p_value, z_score

    async def calculate_confidence_interval(
        self,
        conversions: int,
        total: int,
        confidence_level: float = 0.95,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Расчет доверительного интервала для пропорции (метод Уилсона).

        Args:
            conversions: Количество конверсий
            total: Размер выборки
            confidence_level: Уровень доверия (0.0 - 1.0, по умолчанию 0.95)

        Returns:
            (lower_bound, upper_bound) или (None, None) если расчет невозможен

        Raises:
            ValueError: Если входные данные некорректны
        """
        # Валидация входных данных
        if total <= 0:
            raise ValueError("Размер выборки должен быть положительным")

        if conversions < 0 or conversions > total:
            raise ValueError("Количество конверсий должно быть от 0 до размера выборки")

        if not (0.0 < confidence_level < 1.0):
            raise ValueError("Уровень доверия должен быть между 0 и 1")

        # Если нет данных, возвращаем None
        if total == 0:
            return None, None

        # Пропорция
        p = float(conversions) / float(total) if total > 0 else 0.0

        # Z-критическое значение
        z = self._get_z_critical(confidence_level)

        # Метод Уилсона (лучше работает для малых выборок и крайних значений)
        denominator = 1.0 + z * z / total

        if denominator == 0:
            return None, None

        center = (p + z * z / (2.0 * total)) / denominator
        margin = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator

        lower_bound = max(0.0, center - margin)
        upper_bound = min(1.0, center + margin)

        logger.debug(
            f"Confidence interval (Wilson): p={p:.4f}, "
            f"CI=[{lower_bound:.4f}, {upper_bound:.4f}]"
        )

        return lower_bound, upper_bound

    async def calculate_t_test(
        self,
        control_mean: float,
        control_std: float,
        control_size: int,
        treatment_mean: float,
        treatment_std: float,
        treatment_size: int,
        confidence_level: float = 0.95,
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """
        Расчет статистической значимости (t-test для двух выборок).

        Используется для непрерывных метрик (время просмотра, средний чек и т.д.).

        Args:
            control_mean: Среднее значение контрольной группы
            control_std: Стандартное отклонение контрольной группы
            control_size: Размер контрольной группы
            treatment_mean: Среднее значение тестовой группы
            treatment_std: Стандартное отклонение тестовой группы
            treatment_size: Размер тестовой группы
            confidence_level: Уровень доверия (по умолчанию 0.95)

        Returns:
            (is_significant, p_value, t_score)
        """
        # Валидация
        if control_size <= 0 or treatment_size <= 0:
            raise ValueError("Размер выборки должен быть положительным")

        if control_std < 0 or treatment_std < 0:
            raise ValueError("Стандартное отклонение не может быть отрицательным")

        # Стандартная ошибка разности средних
        numerator = control_std ** 2 / control_size + treatment_std ** 2 / treatment_size
        se = math.sqrt(numerator) if numerator > 0 else 0.0

        if se == 0.0:
            return False, None, None

        # T-статистика
        t_score = (treatment_mean - control_mean) / se

        # Степени свободы (формула Уэлча)
        df_numerator = (control_std ** 2 / control_size + treatment_std ** 2 / treatment_size) ** 2
        df_denominator = (
            (control_std ** 2 / control_size) ** 2 / (control_size - 1) +
            (treatment_std ** 2 / treatment_size) ** 2 / (treatment_size - 1)
        )
        degrees_of_freedom = df_numerator / df_denominator if df_denominator > 0 else control_size + treatment_size - 2

        # Аппроксимация p-value через t-распределение
        # Для больших df t-распределение приближается к нормальному
        if degrees_of_freedom > 30:
            p_value = self._calculate_p_value(t_score, two_tailed=True)
        else:
            # Для малых df используем упрощенную аппроксимацию
            # (в реальном проекте лучше использовать scipy)
            p_value = self._calculate_p_value(t_score, two_tailed=True)

        # Проверка значимости
        alpha = 1.0 - confidence_level
        is_significant = p_value is not None and p_value < alpha

        logger.debug(
            f"T-test: control_mean={control_mean:.4f}, treatment_mean={treatment_mean:.4f}, "
            f"t={t_score:.4f}, df={degrees_of_freedom:.2f}, p={p_value:.4f}, "
            f"significant={is_significant}"
        )

        return is_significant, p_value, t_score


def get_ab_testing_service(
    db: Session,
    redis_client: Optional["aioredis.Redis"] = None
) -> ABTestingService:
    """
    Фабрика для создания сервиса A/B тестирования.

    Args:
        db: SQLAlchemy сессия
        redis_client: Опциональный Redis клиент

    Returns:
        ABTestingService instance
    """
    return ABTestingService(db=db, redis_client=redis_client)
