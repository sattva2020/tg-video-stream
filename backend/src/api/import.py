"""
Content Import API Router

API endpoints for importing playlists and content from various platforms:
- YouTube playlists
- Vimeo albums
- Local media libraries

Provides endpoints for creating, monitoring, and managing import jobs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID

from src.database import get_db
from src.models.user import User
from src.models.import_job import ImportJob, ImportStatus
from src.schemas.import_schemas import (
    ImportCreateRequest,
    ImportJobResponse,
    ImportJobListResponse,
    ImportJobUpdate,
)
from src.services.import_service import import_service
from src.services.activity_service import ActivityService
from api.auth import get_current_user

router = APIRouter()


# WebSocket notifications (imported lazily to avoid circular imports)
def _get_ws_module():
    try:
        from api import websocket as ws_module
        return ws_module
    except ImportError:
        return None


@router.post("/", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def create_import_job(
    request: ImportCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new import job.

    Supports importing from:
    - YouTube playlists (provide source_url)
    - Vimeo albums (provide source_url)
    - Local media libraries (provide source_path)

    The import job will be processed asynchronously in the background.
    """
    try:
        # Create import job
        import_job = import_service.create_import_job(
            db=db,
            request=request,
            user_id=current_user.id
        )

        # Log import started event
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="import_started",
            message=f"Запущен импорт контента из {request.platform.value}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "import_job_id": str(import_job.id),
                "platform": request.platform.value,
                "source_url": request.source_url,
                "source_path": request.source_path,
                "channel_id": str(request.channel_id) if request.channel_id else None,
                "options": request.options
            }
        )

        # Notify WebSocket clients
        ws_module = _get_ws_module()
        if ws_module:
            background_tasks.add_task(
                ws_module.notify_import_created,
                import_job,
                str(current_user.id)
            )

        # Celery task will pick up this job automatically from the queue
        # Task routing configured in celery_app.py

        return ImportJobResponse.model_validate(import_job)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create import job: {str(e)}"
        )


@router.get("/", response_model=ImportJobListResponse)
async def list_import_jobs(
    platform: Optional[str] = None,
    status_filter: Optional[str] = None,
    channel_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List import jobs with filtering and pagination.

    Filters:
    - platform: Filter by import platform (youtube, vimeo, local)
    - status: Filter by status (pending, in_progress, completed, failed, cancelled)
    - channel_id: Filter by target channel
    """
    query = db.query(ImportJob).filter(ImportJob.user_id == current_user.id)

    # Apply filters
    if platform:
        query = query.filter(ImportJob.platform == platform)
    if status_filter:
        query = query.filter(ImportJob.status == status_filter)
    if channel_id:
        query = query.filter(ImportJob.channel_id == channel_id)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(ImportJob.created_at.desc()).offset(offset).limit(page_size).all()

    return ImportJobListResponse(
        items=[ImportJobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific import job.
    """
    import_job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id
    ).first()

    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found"
        )

    return ImportJobResponse.model_validate(import_job)


@router.delete("/{job_id}")
async def cancel_import_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an import job.

    Only jobs in pending, in_progress, or paused status can be cancelled.
    """
    import_job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id
    ).first()

    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found"
        )

    try:
        # Cancel the import job
        import_service.cancel_import(db, import_job)

        # Log cancellation event
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="import_cancelled",
            message=f"Отменён импорт контента из {import_job.platform.value}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "import_job_id": str(import_job.id),
                "platform": import_job.platform.value,
                "status": import_job.status.value
            }
        )

        # Notify WebSocket clients
        ws_module = _get_ws_module()
        if ws_module:
            background_tasks.add_task(
                ws_module.notify_import_cancelled,
                str(import_job.id),
                str(current_user.id)
            )

        return {"ok": True, "message": "Import job cancelled successfully"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel import job: {str(e)}"
        )


@router.patch("/{job_id}")
async def update_import_job(
    job_id: UUID,
    update: ImportJobUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update import job status (pause/resume).

    Supported status transitions:
    - in_progress -> paused
    - paused -> in_progress
    - [any] -> cancelled (use DELETE instead)
    """
    import_job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id
    ).first()

    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found"
        )

    try:
        # Update job status based on request
        if update.status == ImportStatus.PAUSED:
            import_service.pause_import(db, import_job)
            event_type = "import_paused"
            message = f"Приостановлен импорт контента из {import_job.platform.value}"
        elif update.status == ImportStatus.IN_PROGRESS:
            import_service.resume_import(db, import_job)
            event_type = "import_resumed"
            message = f"Возобновлён импорт контента из {import_job.platform.value}"
        elif update.status == ImportStatus.CANCELLED:
            import_service.cancel_import(db, import_job)
            event_type = "import_cancelled"
            message = f"Отменён импорт контента из {import_job.platform.value}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition to {update.status.value}"
            )

        # Log status update event
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type=event_type,
            message=message,
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "import_job_id": str(import_job.id),
                "platform": import_job.platform.value,
                "new_status": update.status.value
            }
        )

        # Notify WebSocket clients
        ws_module = _get_ws_module()
        if ws_module:
            background_tasks.add_task(
                ws_module.notify_import_updated,
                import_job,
                str(current_user.id)
            )

        return {"ok": True, "status": import_job.status.value}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update import job: {str(e)}"
        )


@router.get("/{job_id}/summary")
async def get_import_summary(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a summary of import job results.
    """
    import_job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id
    ).first()

    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found"
        )

    summary = import_service.get_import_summary(import_job)
    return summary
