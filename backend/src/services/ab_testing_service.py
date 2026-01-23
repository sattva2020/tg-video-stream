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

    async def analyze_test(self, test_id: UUID) -> ABTestAnalysisResponse:
        """
        Статистический анализ A/B теста.

        Args:
            test_id: ID теста

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

            # Доверительный интервал (placeholder, будет рассчитан в subtask-2-2)
            stats = ABTestStatistics(
                variant_id=variant.id,
                variant_name=variant.name,
                impressions=int(impressions),
                conversions=int(conversions),
                conversion_rate=conversion_rate,
                confidence_interval_lower=None,
                confidence_interval_upper=None,
            )
            variant_stats.append(stats)

        # Определение победителя (placeholder, будет улучшен в subtask-2-2)
        winner_id = None
        if variant_stats:
            winner = max(variant_stats, key=lambda x: x.conversion_rate)
            winner_id = winner.variant_id

        # Статистическая значимость (placeholder, будет рассчитана в subtask-2-2)
        p_value = None
        is_significant = False
        confidence_level = 95.0

        response = ABTestAnalysisResponse(
            test_id=test.id,
            test_name=test.name,
            status=test.status.value,
            variants=variant_stats,
            winner_variant_id=winner_id,
            confidence_level=confidence_level,
            is_significant=is_significant,
            p_value=p_value,
            recommended_action="Continue testing" if not is_significant else f"Implement variant {winner_id}",
            analyzed_at=datetime.now(timezone.utc),
        )

        return response

    # Placeholder методы для статистических расчетов (будут реализованы в subtask-2-2)
    async def calculate_statistical_significance(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
    ) -> tuple[bool, float]:
        """
        Расчет статистической значимости (z-test).

        Args:
            control_conversions: Конверсии контрольной группы
            control_total: Размер контрольной группы
            treatment_conversions: Конверсии тестовой группы
            treatment_total: Размер тестовой группы

        Returns:
            (is_significant, p_value)

        Note:
            Полная реализация будет в subtask-2-2
        """
        # Placeholder - будет реализован в subtask-2-2
        return False, None

    async def calculate_confidence_interval(
        self,
        conversions: int,
        total: int,
        confidence_level: float = 0.95,
    ) -> tuple[float, float]:
        """
        Расчет доверительного интервала.

        Args:
            conversions: Количество конверсий
            total: Размер выборки
            confidence_level: Уровень доверия (0.0 - 1.0)

        Returns:
            (lower_bound, upper_bound)

        Note:
            Полная реализация будет в subtask-2-2
        """
        # Placeholder - будет реализован в subtask-2-2
        return 0.0, 0.0


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
