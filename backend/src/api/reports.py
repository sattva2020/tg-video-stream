"""
Reports API endpoints.
Feature: 012-comprehensive-analytics-dashboard

Эндпоинты для экспорта и планирования отчетов:
- POST /analytics/reports/export - Экспорт отчета в формате CSV
- POST /analytics/reports/schedule - Планирование автоматической отправки отчетов
- GET /analytics/reports/schedule - Получение списка расписаний
- PUT /analytics/reports/schedule/{id} - Обновление расписания
- DELETE /analytics/reports/schedule/{id} - Удаление расписания
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from src.database import get_db
from src.lib.rbac import require_role, UserRole
from src.schemas.reports import (
    ReportExportRequest,
    ReportExportResponse,
    ReportScheduleRequest,
    ReportScheduleResponse,
    ScheduleListItem,
    ReportScheduleListResponse,
    ReportScheduleUpdate,
    ReportType,
    ReportFormat,
)
from src.services.report_service import ReportService, get_report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics/reports", tags=["Reports"])


async def get_report_service_dep(
    db: Session = Depends(get_db)
) -> ReportService:
    """Dependency для получения ReportService."""
    return get_report_service(db=db)


def _generate_filename(report_type: ReportType, period: str, format: ReportFormat) -> str:
    """
    Генерация имени файла для отчета.

    Args:
        report_type: Тип отчета
        period: Период данных
        format: Формат файла

    Returns:
        Имя файла с расширением
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = "csv" if format == "csv" else format
    return f"report_{report_type}_{period}_{timestamp}.{ext}"


def _get_report_type_name(report_type: ReportType) -> str:
    """Получить человекочитаемое название типа отчета."""
    names = {
        "summary": "Сводный отчет",
        "listeners": "История слушателей",
        "top_tracks": "Топ треков",
        "engagement": "Вовлеченность",
        "stream_performance": "Производительность потока",
        "content_insights": "Аналитика контента",
    }
    return names.get(report_type, report_type)


@router.post(
    "/export",
    response_model=ReportExportResponse,
    summary="Экспортировать отчет",
    description="Генерирует отчет в указанном формате для скачивания"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR])
async def export_report(
    request: Request,
    req: ReportExportRequest,
    service: ReportService = Depends(get_report_service_dep)
):
    """
    Экспортировать отчет в формате CSV.

    Требуемые роли: SUPERADMIN, ADMIN, MODERATOR
    """
    try:
        logger.info(f"Exporting report: type={req.report_type}, period={req.period}, format={req.format}")

        # Валидация периода
        valid_periods = ["7d", "30d", "90d", "all"]
        if req.period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )

        # Генерация отчета в зависимости от типа
        if req.report_type == "summary":
            csv_data = await service.generate_summary_report(period=req.period)
        elif req.report_type == "listeners":
            csv_data = await service.generate_listener_history_report(period=req.period)
        elif req.report_type == "top_tracks":
            csv_data = await service.generate_top_tracks_report(period=req.period, limit=10)
        elif req.report_type == "engagement":
            csv_data = await service.generate_engagement_report(period=req.period)
        elif req.report_type == "stream_performance":
            csv_data = await service.generate_stream_performance_report(period=req.period)
        elif req.report_type == "content_insights":
            csv_data = await service.generate_content_insights_report(period=req.period)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported report type: {req.report_type}"
            )

        filename = _generate_filename(req.report_type, req.period, req.format)

        logger.info(f"Report exported successfully: {filename}, size={len(csv_data)} bytes")

        return ReportExportResponse(
            success=True,
            report_type=req.report_type,
            format=req.format,
            data=csv_data,
            filename=filename,
            generated_at=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail="Failed to export report")


@router.post(
    "/schedule",
    response_model=ReportScheduleResponse,
    summary="Запланировать отчет",
    description="Создает расписание для автоматической генерации и отправки отчета"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def schedule_report(
    request: Request,
    req: ReportScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Запланировать автоматическую отправку отчета.

    Требуемые роли: SUPERADMIN, ADMIN

    Note: Для полной функциональности требуется:
    - Модель ScheduledReport в базе данных
    - Фоновая задача (Celery/APScheduler) для отправки отчетов
    - SMTP конфигурация для отправки email

    В текущей реализации endpoint возвращает mock-ответ.
    """
    try:
        logger.info(
            f"Scheduling report: type={req.report_type}, period={req.period}, "
            f"frequency={req.frequency}, email={req.email}"
        )

        # TODO: Создать запись в базе данных при наличии модели ScheduledReport
        # scheduled_report = ScheduledReport(
        #     report_type=req.report_type,
        #     period=req.period,
        #     format=req.format,
        #     frequency=req.frequency,
        #     email=req.email,
        #     enabled=req.enabled,
        #     created_by=request.state.user_id
        # )
        # db.add(scheduled_report)
        # db.commit()
        # db.refresh(scheduled_report)

        # Mock-реализация для демонстрации API
        now = datetime.now(timezone.utc)

        # Вычисляем следующий запуск
        if req.frequency == "daily":
            next_run = now + timedelta(days=1)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)
        elif req.frequency == "weekly":
            next_run = now + timedelta(weeks=1)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)
        else:  # monthly
            next_run = now + timedelta(days=30)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)

        # Mock ID - в реальной реализации будет ID из базы
        mock_id = 1

        logger.info(f"Report scheduled successfully: id={mock_id}, next_run={next_run}")

        return ReportScheduleResponse(
            id=mock_id,
            report_type=req.report_type,
            frequency=req.frequency,
            email=req.email,
            enabled=req.enabled,
            created_at=now,
            next_run_at=next_run
        )

    except Exception as e:
        logger.error(f"Error scheduling report: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule report")


@router.get(
    "/schedule",
    response_model=ReportScheduleListResponse,
    summary="Получить список расписаний",
    description="Возвращает все запланированные отчеты"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def list_scheduled_reports(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Получить список всех запланированных отчетов.

    Требуемые роли: SUPERADMIN, ADMIN

    Note: В текущей реализации возвращает пустой список.
    При наличии модели ScheduledReport будет загружать данные из базы.
    """
    try:
        logger.info("Listing scheduled reports")

        # TODO: Загрузить из базы при наличии модели ScheduledReport
        # schedules = db.execute(
        #     select(ScheduledReport).order_by(ScheduledReport.created_at.desc())
        # ).scalars().all()
        #
        # schedule_items = [
        #     ScheduleListItem(
        #         id=s.id,
        #         report_type=s.report_type,
        #         period=s.period,
        #         format=s.format,
        #         frequency=s.frequency,
        #         email=s.email,
        #         enabled=s.enabled,
        #         created_at=s.created_at,
        #         next_run_at=s.next_run_at,
        #         last_sent_at=s.last_sent_at
        #     )
        #     for s in schedules
        # ]

        # Mock-реализация
        schedule_items = []

        return ReportScheduleListResponse(
            schedules=schedule_items,
            total=len(schedule_items)
        )

    except Exception as e:
        logger.error(f"Error listing scheduled reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to list scheduled reports")


@router.put(
    "/schedule/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="Обновить расписание",
    description="Обновляет параметры запланированного отчета"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def update_scheduled_report(
    request: Request,
    schedule_id: int,
    req: ReportScheduleUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновить расписание отчета.

    Требуемые роли: SUPERADMIN, ADMIN

    Note: В текущей реализации возвращает mock-ответ.
    """
    try:
        logger.info(f"Updating scheduled report: id={schedule_id}")

        # TODO: Обновить в базе при наличии модели ScheduledReport
        # schedule = db.execute(
        #     select(ScheduledReport).where(ScheduledReport.id == schedule_id)
        # ).scalar_one_or_none()
        #
        # if not schedule:
        #     raise HTTPException(status_code=404, detail="Schedule not found")
        #
        # if req.frequency is not None:
        #     schedule.frequency = req.frequency
        # if req.email is not None:
        #     schedule.email = req.email
        # if req.enabled is not None:
        #     schedule.enabled = req.enabled
        #
        # db.commit()
        # db.refresh(schedule)

        # Mock-реализация
        now = datetime.now(timezone.utc)

        return ReportScheduleResponse(
            id=schedule_id,
            report_type="summary",  # Mock
            frequency=req.frequency or "daily",
            email=req.email,
            enabled=req.enabled if req.enabled is not None else True,
            created_at=now - timedelta(days=1),
            next_run_at=now + timedelta(days=1)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scheduled report: {e}")
        raise HTTPException(status_code=500, detail="Failed to update scheduled report")


@router.delete(
    "/schedule/{schedule_id}",
    summary="Удалить расписание",
    description="Удаляет запланированный отчет"
)
@require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
async def delete_scheduled_report(
    request: Request,
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """
    Удалить расписание отчета.

    Требуемые роли: SUPERADMIN, ADMIN

    Note: В текущей реализации возвращает mock-ответ.
    """
    try:
        logger.info(f"Deleting scheduled report: id={schedule_id}")

        # TODO: Удалить из базы при наличии модели ScheduledReport
        # schedule = db.execute(
        #     select(ScheduledReport).where(ScheduledReport.id == schedule_id)
        # ).scalar_one_or_none()
        #
        # if not schedule:
        #     raise HTTPException(status_code=404, detail="Schedule not found")
        #
        # db.delete(schedule)
        # db.commit()

        return {"success": True, "message": f"Schedule {schedule_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled report: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete scheduled report")
