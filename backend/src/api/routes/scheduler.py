"""
API routes for scheduled playlist management.

Endpoints:
  POST /api/v1/scheduler/schedules - Create a new scheduled playlist
  GET /api/v1/scheduler/schedules - List all scheduled playlists
  GET /api/v1/scheduler/schedules/{schedule_id} - Get schedule details
  PUT /api/v1/scheduler/schedules/{schedule_id} - Update schedule
  DELETE /api/v1/scheduler/schedules/{schedule_id} - Delete schedule
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ..dependencies import get_current_user, require_admin
from ...services.scheduler_service import SchedulerService
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


# Request/Response Models
class CreateScheduleRequest(BaseModel):
    """Request to create a scheduled playlist."""
    playlist_id: int = Field(description="ID of the playlist to schedule")
    time: str = Field(description="Time to play (HH:MM format or cron expression)")
    recurrence: Optional[str] = Field(None, description="Recurrence pattern (daily, weekly, daily:mon,wed,fri)")
    timezone: str = Field(default="UTC", description="Timezone for scheduling (e.g., 'Europe/Moscow')")
    enabled: bool = Field(default=True, description="Whether schedule is enabled")
    channel_id: Optional[int] = Field(None, description="Telegram channel ID for multi-channel support")


class UpdateScheduleRequest(BaseModel):
    """Request to update a scheduled playlist."""
    time: Optional[str] = Field(None, description="New time (HH:MM format)")
    recurrence: Optional[str] = Field(None, description="New recurrence pattern")
    timezone: Optional[str] = Field(None, description="New timezone")
    enabled: Optional[bool] = Field(None, description="Enable/disable schedule")


class ScheduleResponse(BaseModel):
    """Response with scheduled playlist information."""
    id: int
    playlist_id: int
    playlist_name: str
    time: str
    recurrence: Optional[str]
    timezone: str
    enabled: bool
    triggered_count: int
    last_triggered: Optional[str]
    created_at: str
    updated_at: str


class ScheduleListResponse(BaseModel):
    """Response with list of scheduled playlists."""
    total: int
    schedules: List[ScheduleResponse]
    active_count: int
    next_trigger: Optional[str]


class ScheduleCreatedResponse(BaseModel):
    """Response after creating a schedule."""
    id: int
    message: str
    playlist_id: int
    time: str


# Route Handlers

@router.post("/schedules", response_model=ScheduleCreatedResponse, status_code=201)
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: User = Depends(require_admin),
    scheduler_service: SchedulerService = Depends(lambda: SchedulerService())
):
    """
    Create a new scheduled playlist.
    
    **Permission**: Admin only
    
    **Rate Limit**: 20 requests/minute per admin (Strict)
    
    **Time Format**:
    - `HH:MM` - Daily at specific time (e.g., "08:30")
    - Cron expression - Custom recurrence (e.g., "0 8 * * *")
    
    **Recurrence Options**:
    - `daily` - Every day
    - `weekly` - Every week (same day)
    - `daily:mon,wed,fri` - Specific days of week
    - `monthly` - Same day each month
    - Custom cron expression
    
    **Example**:
    ```json
    {
      "playlist_id": 5,
      "time": "08:00",
      "recurrence": "daily",
      "timezone": "Europe/Moscow",
      "enabled": true
    }
    ```
    """
    try:
        # Create schedule via service
        schedule = await scheduler_service.schedule_playlist(
            playlist_id=request.playlist_id,
            time=request.time,
            recurrence=request.recurrence,
            timezone=request.timezone,
            enabled=request.enabled,
            channel_id=request.channel_id or current_user.id
        )
        
        logger.info(f"Admin {current_user.id} created schedule for playlist {request.playlist_id}")
        
        return ScheduleCreatedResponse(
            id=schedule.get("id"),
            message=f"Schedule created for playlist at {request.time}",
            playlist_id=request.playlist_id,
            time=request.time
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create schedule")


@router.get("/schedules", response_model=ScheduleListResponse, status_code=200)
async def list_schedules(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    active_only: bool = Query(False, description="Show only active schedules"),
    current_user: User = Depends(get_current_user),
    scheduler_service: SchedulerService = Depends(lambda: SchedulerService())
):
    """
    List all scheduled playlists.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 20, max 100)
    - `active_only`: Show only enabled schedules (default false)
    """
    try:
        result = await scheduler_service.list_schedules(
            page=page,
            page_size=page_size,
            active_only=active_only
        )
        
        schedules = [ScheduleResponse(**s) for s in result.get("schedules", [])]
        
        logger.info(f"User {current_user.id} listed schedules (page {page})")
        
        return ScheduleListResponse(
            total=result.get("total", 0),
            schedules=schedules,
            active_count=result.get("active_count", 0),
            next_trigger=result.get("next_trigger")
        )
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list schedules")


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse, status_code=200)
async def get_schedule(
    schedule_id: int = Path(gt=0, description="Schedule ID"),
    current_user: User = Depends(get_current_user),
    scheduler_service: SchedulerService = Depends(lambda: SchedulerService())
):
    """
    Get details of a specific scheduled playlist.
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    """
    try:
        schedule = await scheduler_service.get_schedule(schedule_id=schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        
        return ScheduleResponse(**schedule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get schedule")


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse, status_code=200)
async def update_schedule(
    schedule_id: int = Path(gt=0, description="Schedule ID"),
    request: UpdateScheduleRequest = None,
    current_user: User = Depends(require_admin),
    scheduler_service: SchedulerService = Depends(lambda: SchedulerService())
):
    """
    Update a scheduled playlist.
    
    **Permission**: Admin only
    
    **Rate Limit**: 20 requests/minute per admin (Strict)
    
    **Example**:
    ```json
    {
      "time": "09:00",
      "enabled": true
    }
    ```
    """
    try:
        schedule = await scheduler_service.update_schedule(
            schedule_id=schedule_id,
            time=request.time,
            recurrence=request.recurrence,
            timezone=request.timezone,
            enabled=request.enabled
        )
        
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        
        logger.info(f"Admin {current_user.id} updated schedule {schedule_id}")
        
        return ScheduleResponse(**schedule)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update schedule")


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int = Path(gt=0, description="Schedule ID"),
    current_user: User = Depends(require_admin),
    scheduler_service: SchedulerService = Depends(lambda: SchedulerService())
):
    """
    Delete a scheduled playlist.
    
    **Permission**: Admin only
    
    **Rate Limit**: 20 requests/minute per admin (Strict)
    """
    try:
        success = await scheduler_service.cancel_schedule(schedule_id=schedule_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        
        logger.info(f"Admin {current_user.id} deleted schedule {schedule_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete schedule")
