"""
A/B Testing API endpoints.
Feature: 016-a-b-testing-framework-for-content

Эндпоинты для управления A/B тестированием контента:
- POST /ab-tests - Создание A/B теста
- GET /ab-tests - Список A/B тестов
- GET /ab-tests/{id} - Получение A/B теста
- PATCH /ab-tests/{id} - Обновление A/B теста
- DELETE /ab-tests/{id} - Удаление A/B теста
- POST /ab-tests/{id}/start - Запуск A/B теста
- POST /ab-tests/{id}/stop - Остановка A/B теста
- GET /ab-tests/{id}/analysis - Статистический анализ
- POST /ab-tests/metrics - Запись метрики
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from sqlalchemy.orm import Session

from src.database import get_db
from src.lib.rbac import require_role, UserRole
from src.schemas.ab_testing import (
    ABTestCreate,
    ABTestUpdate,
    ABTestResponse,
    ABTestCollectionResponse,
    ABTestMetricCreate,
    ABTestMetricResponse,
    ABTestStartResponse,
    ABTestStopResponse,
    ABTestAnalysisResponse,
)
from src.services.ab_testing_service import ABTestingService, get_ab_testing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ab-tests", tags=["A/B Testing"])


# === Helper Functions ===

async def get_ab_testing_service_dep(
    db: Session = Depends(get_db)
) -> ABTestingService:
    """Dependency для получения ABTestingService."""
    return get_ab_testing_service(db=db, redis_client=None)


# === Public Endpoints (require authentication) ===

@router.post(
    "",
    response_model=ABTestResponse,
    summary="Создание A/B теста",
    description="Создает новый A/B тест с вариантами"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def create_ab_test(
    request: Request,
    test_data: ABTestCreate,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Создание нового A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN
    """
    try:
        # TODO: Extract created_by from current_user when auth is implemented
        return await service.create_test(test_data=test_data)
    except ValueError as e:
        logger.error(f"Validation error creating A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating A/B test: {e}")
        raise HTTPException(status_code=500, detail="Failed to create A/B test")


@router.get(
    "",
    response_model=ABTestCollectionResponse,
    summary="Список A/B тестов",
    description="Получение списка A/B тестов с фильтрацией"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def list_ab_tests(
    request: Request,
    channel_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID канала"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=100, description="Максимальное количество результатов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Получение списка A/B тестов.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        return await service.list_tests(
            channel_id=channel_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing A/B tests: {e}")
        raise HTTPException(status_code=500, detail="Failed to list A/B tests")


@router.get(
    "/{test_id}",
    response_model=ABTestResponse,
    summary="Получение A/B теста",
    description="Получение A/B теста по ID"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def get_ab_test(
    request: Request,
    test_id: uuid.UUID,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Получение A/B теста по ID.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        test = await service.get_test(test_id=test_id)
        if not test:
            raise HTTPException(status_code=404, detail="A/B test not found")
        return test
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get A/B test")


@router.patch(
    "/{test_id}",
    response_model=ABTestResponse,
    summary="Обновление A/B теста",
    description="Обновление метаданных A/B теста"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def update_ab_test(
    request: Request,
    test_id: uuid.UUID,
    test_data: ABTestUpdate,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Обновление метаданных A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN

    Примечание: Обновлять можно только тесты в статусе draft.
    """
    try:
        test = await service.update_test(test_id=test_id, test_data=test_data)
        if not test:
            raise HTTPException(status_code=404, detail="A/B test not found")
        return test
    except ValueError as e:
        logger.error(f"Validation error updating A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update A/B test")


@router.delete(
    "/{test_id}",
    summary="Удаление A/B теста",
    description="Удаление A/B теста"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def delete_ab_test(
    request: Request,
    test_id: uuid.UUID,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Удаление A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN

    Примечание: Удалять можно только тесты не в статусе running.
    """
    try:
        success = await service.delete_test(test_id=test_id)
        if not success:
            raise HTTPException(status_code=404, detail="A/B test not found")
        return {"success": True, "message": "A/B test deleted successfully"}
    except ValueError as e:
        logger.error(f"Validation error deleting A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete A/B test")


@router.post(
    "/{test_id}/start",
    response_model=ABTestStartResponse,
    summary="Запуск A/B теста",
    description="Запуск A/B теста для сбора данных"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def start_ab_test(
    request: Request,
    test_id: uuid.UUID,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Запуск A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN

    Примечание: Запустить можно только тест в статусе draft или paused.
    """
    try:
        return await service.start_test(test_id=test_id)
    except ValueError as e:
        logger.error(f"Validation error starting A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start A/B test")


@router.post(
    "/{test_id}/stop",
    response_model=ABTestStopResponse,
    summary="Остановка A/B теста",
    description="Остановка A/B теста с выбором победителя"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def stop_ab_test(
    request: Request,
    test_id: uuid.UUID,
    select_winner: bool = Query(True, description="Автоматически выбрать победителя"),
    winner_variant_id: Optional[uuid.UUID] = Query(None, description="ID варианта-победителя (ручной выбор)"),
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Остановка A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN

    Примечание: Остановить можно только запущенный тест.
    """
    try:
        return await service.stop_test(
            test_id=test_id,
            select_winner=select_winner,
            winner_variant_id=winner_variant_id,
        )
    except ValueError as e:
        logger.error(f"Validation error stopping A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop A/B test")


@router.get(
    "/{test_id}/analysis",
    response_model=ABTestAnalysisResponse,
    summary="Статистический анализ A/B теста",
    description="Получение результатов статистического анализа"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def analyze_ab_test(
    request: Request,
    test_id: uuid.UUID,
    confidence_level: float = Query(0.95, ge=0.5, le=0.99, description="Уровень доверия (0.5-0.99)"),
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Статистический анализ A/B теста.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR

    Включает расчет конверсий, доверительных интервалов и статистической значимости.
    """
    try:
        return await service.analyze_test(
            test_id=test_id,
            confidence_level=confidence_level,
        )
    except ValueError as e:
        logger.error(f"Validation error analyzing A/B test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze A/B test")


@router.post(
    "/metrics",
    response_model=ABTestMetricResponse,
    summary="Запись метрики",
    description="Запись метрики для варианта A/B теста"
)
async def record_metric(
    request: Request,
    metric_data: ABTestMetricCreate,
    service: ABTestingService = Depends(get_ab_testing_service_dep),
):
    """
    Запись метрики для варианта A/B теста.

    Внутренний эндпоинт для записи метрик (impressions, clicks, conversions, etc.).
    """
    try:
        return await service.record_metric(metric_data=metric_data)
    except ValueError as e:
        logger.error(f"Validation error recording metric: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail="Failed to record metric")
