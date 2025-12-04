"""
API routes for backup and system administration.

Endpoints:
  POST /api/v1/backup/trigger - Trigger immediate backup
  GET /api/v1/backup/status - Get backup status and statistics
  GET /api/v1/backup/history - List recent backups
  GET /api/v1/backup/download/{backup_id} - Download backup file
  DELETE /api/v1/backup/{backup_id} - Delete backup
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ..dependencies import require_admin
from ...services.backup_service import BackupService
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/backup", tags=["backup"])


# Request/Response Models
class TriggerBackupRequest(BaseModel):
    """Request to trigger a backup."""
    include_database: bool = Field(default=True, description="Include PostgreSQL database")
    include_redis: bool = Field(default=True, description="Include Redis data")
    include_config: bool = Field(default=True, description="Include configuration files")
    include_logs: bool = Field(default=False, description="Include application logs")


class BackupInfo(BaseModel):
    """Information about a backup."""
    id: str
    created_at: str
    size_mb: float
    status: str  # 'completed', 'failed', 'partial'
    database_backup: bool
    redis_backup: bool
    config_backup: bool
    logs_backup: bool
    retention_days: int


class BackupStatusResponse(BaseModel):
    """Response with backup status."""
    last_backup: Optional[BackupInfo] = None
    last_backup_status: str  # 'success', 'failed', 'pending', 'none'
    backup_enabled: bool
    auto_rotation_enabled: bool
    total_backups: int
    storage_used_mb: float
    oldest_backup_age_days: Optional[int] = None
    next_backup_time: Optional[str] = None


class BackupHistoryResponse(BaseModel):
    """Response with backup history."""
    total: int
    backups: List[BackupInfo]
    page: int
    page_size: int


class TriggerBackupResponse(BaseModel):
    """Response after triggering backup."""
    backup_id: str
    message: str
    status: str
    estimated_duration_seconds: int


# Route Handlers

@router.post("/trigger", response_model=TriggerBackupResponse, status_code=202)
async def trigger_backup(
    request: TriggerBackupRequest,
    current_user: User = Depends(require_admin),
    backup_service: BackupService = Depends(lambda: BackupService())
):
    """
    Trigger an immediate backup of system data.
    
    **Permission**: Admin only
    
    **Rate Limit**: 5 requests/minute per admin (Strict)
    
    **Components**:
    - `include_database`: PostgreSQL database dump (usually 50-500 MB)
    - `include_redis`: Redis data export
    - `include_config`: Configuration files and secrets
    - `include_logs`: Application logs (can be large)
    
    **Retention Policy**: Backups kept for 30 days (rolling window)
    
    **Example**:
    ```json
    {
      "include_database": true,
      "include_redis": true,
      "include_config": true,
      "include_logs": false
    }
    ```
    """
    try:
        # Start backup process (async)
        backup_id = await backup_service.backup_database(
            include_database=request.include_database,
            include_redis=request.include_redis,
            include_config=request.include_config,
            include_logs=request.include_logs
        )
        
        logger.info(
            f"Admin {current_user.id} triggered backup {backup_id} "
            f"(db={request.include_database}, redis={request.include_redis}, "
            f"config={request.include_config}, logs={request.include_logs})"
        )
        
        return TriggerBackupResponse(
            backup_id=backup_id,
            message="Backup started in background",
            status="pending",
            estimated_duration_seconds=300  # 5 minutes estimate
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering backup: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trigger backup")


@router.get("/status", response_model=BackupStatusResponse, status_code=200)
async def get_backup_status(
    current_user: User = Depends(require_admin),
    backup_service: BackupService = Depends(lambda: BackupService())
):
    """
    Get backup system status and statistics.
    
    **Permission**: Admin only
    
    **Rate Limit**: 50 requests/minute per admin (Standard)
    
    **Returns**:
    - `last_backup`: Most recent backup information
    - `last_backup_status`: Overall status of last backup
    - `backup_enabled`: Whether automatic backups are enabled
    - `auto_rotation_enabled`: Whether old backups are auto-deleted
    - `total_backups`: Number of backups in storage
    - `storage_used_mb`: Total storage used by backups
    - `oldest_backup_age_days`: Age of oldest backup in days
    - `next_backup_time`: Scheduled time for next automatic backup
    """
    try:
        status_data = await backup_service.get_status()
        
        logger.info(f"Admin {current_user.id} retrieved backup status")
        
        return BackupStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get backup status")


@router.get("/history", response_model=BackupHistoryResponse, status_code=200)
async def get_backup_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(require_admin),
    backup_service: BackupService = Depends(lambda: BackupService())
):
    """
    Get list of recent backups.
    
    **Permission**: Admin only
    
    **Rate Limit**: 50 requests/minute per admin (Standard)
    
    **Query Parameters**:
    - `page`: Page number (default 1)
    - `page_size`: Results per page (default 10, max 50)
    
    **Returns**:
    - `total`: Total number of backups
    - `backups`: List of backup information
    - `page`: Current page
    - `page_size`: Results per page
    """
    try:
        if page_size > 50:
            page_size = 50
        
        result = await backup_service.list_backups(page=page, page_size=page_size)
        
        backups = [BackupInfo(**b) for b in result.get("backups", [])]
        
        logger.info(f"Admin {current_user.id} retrieved backup history page {page}")
        
        return BackupHistoryResponse(
            total=result.get("total", 0),
            backups=backups,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error getting backup history: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get backup history")


@router.delete("/{backup_id}", status_code=204)
async def delete_backup(
    backup_id: str = Path(description="Backup ID"),
    current_user: User = Depends(require_admin),
    backup_service: BackupService = Depends(lambda: BackupService())
):
    """
    Delete a specific backup.
    
    **Permission**: Admin only
    
    **Rate Limit**: 20 requests/minute per admin (Strict)
    
    **Note**: Deleting backups is permanent and cannot be undone
    """
    try:
        success = await backup_service.delete_backup(backup_id=backup_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
        
        logger.warning(f"Admin {current_user.id} deleted backup {backup_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete backup")
