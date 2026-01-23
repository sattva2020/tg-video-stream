from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import require_admin
from src.models.user import User
from src.models.playlist import PlaylistItem
from database import get_db
from sqlalchemy.orm import Session
from uuid import UUID
import redis
import json
import os
from typing import List, Optional, Dict
from pydantic import BaseModel
from src.services.stream_controller import get_stream_controller, StreamController
from src.services.playlist_service import playlist_service
from src.services.activity_service import ActivityService
from src.schemas.stream_quality import (
    StreamQualityResponse,
    StreamQualityStatus,
    QualityTrendData,
    QualityAlertConfigUpdate,
    QualityAlertConfigResponse,
)
from src.services.stream_quality_service import get_stream_quality_service, StreamQualityService
from src.services.quality_trends_service import get_quality_trends_service, QualityTrendsService
from src.api.admin.saml_config import router as saml_config_router
from src.api.admin.ip_whitelist import router as ip_whitelist_router
from src.api.admin.security_policy import router as security_policy_router
from src.api.admin.data_export import router as data_export_router
from src.api.admin.user_deletion import router as user_deletion_router
from src.api.admin.security_dashboard import router as security_dashboard_router
from src.lib.audit import (
    audit_read,
    audit_create,
    audit_update,
    audit_delete,
    audit_approve,
    audit_reject,
    audit_export
)

router = APIRouter()

# ============================================================================
# Feature 025: SAML Configuration Management
# ============================================================================
router.include_router(saml_config_router, prefix="/saml", tags=["SAML Config"])

# ============================================================================
# Feature 025: IP Whitelist Management
# ============================================================================
router.include_router(ip_whitelist_router, prefix="/ip-whitelist", tags=["IP Whitelist"])

# ============================================================================
# Feature 025: Security Policy Management
# ============================================================================
router.include_router(security_policy_router, prefix="/security-policies", tags=["Security Policy"])

# ============================================================================
# Feature 025: Data Export for GDPR Compliance
# ============================================================================
router.include_router(data_export_router, prefix="", tags=["Data Export"])

# ============================================================================
# Feature 025: User Deletion for GDPR Right to Erasure
# ============================================================================
router.include_router(user_deletion_router, prefix="", tags=["User Deletion"])

# ============================================================================
# Feature 025: Security Dashboard
# ============================================================================
router.include_router(security_dashboard_router, prefix="/security", tags=["Security Dashboard"])


class PlaylistUpdate(BaseModel):
    items: List[str]

class PaginatedUsersResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    role: str

# Redis connection
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))


@router.get("/users", response_model=PaginatedUsersResponse)
@audit_read("user")
def list_users(
    status: str | None = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=1000, description="Items per page"),
    search: str | None = Query(None, description="Search by email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List users with pagination and optional filtering.
    """
    query = db.query(User)
    
    # Apply filters
    if status:
        query = query.filter(User.status == status)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Get paginated results
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedUsersResponse(
        items=[{
            "id": str(u.id),
            "email": u.email,
            "status": getattr(u, 'status', None),
            "role": getattr(u, 'role', 'user'),
            "full_name": getattr(u, 'full_name', None),
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/users/{user_id}/approve")
@audit_approve("user", "user_id")
def approve_user(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    # Защита: нельзя изменять superadmin
    if getattr(user, 'role', '').lower() == 'superadmin':
        raise HTTPException(status_code=403, detail="Cannot modify superadmin account")
    user.status = 'approved'
    db.commit()
    db.refresh(user)

    # Логируем событие одобрения
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="user_approved",
        message=f"Пользователь одобрен: {user.email}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={"approved_user_id": str(user.id), "approved_user_email": user.email}
    )

    return {"status": "ok", "id": str(user.id), "new_status": user.status}


@router.post("/users/{user_id}/reject")
@audit_reject("user", "user_id")
def reject_user(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    # Защита: нельзя изменять superadmin
    if getattr(user, 'role', '').lower() == 'superadmin':
        raise HTTPException(status_code=403, detail="Cannot modify superadmin account")
    user.status = 'rejected'
    db.commit()
    db.refresh(user)

    # Логируем событие отклонения
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="user_rejected",
        message=f"Пользователь отклонён: {user.email}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={"rejected_user_id": str(user.id), "rejected_user_email": user.email}
    )

    return {"status": "ok", "id": str(user.id), "new_status": user.status}


@router.put("/users/{user_id}/role")
@audit_update("user", "user_id")
def update_user_role(
    user_id: UUID,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check permissions
    current_role = getattr(current_user, 'role', '').lower()
    target_role = getattr(user, 'role', '').lower()
    new_role = role_data.role.lower()

    # Only superadmin can modify superadmin
    if target_role == 'superadmin' and current_role != 'superadmin':
        raise HTTPException(status_code=403, detail="Only superadmin can modify superadmin accounts")

    # Only superadmin can promote to superadmin
    if new_role == 'superadmin' and current_role != 'superadmin':
        raise HTTPException(status_code=403, detail="Only superadmin can promote to superadmin")

    # Validate role
    valid_roles = ['user', 'admin', 'superadmin', 'moderator', 'operator']
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    user.role = new_role
    db.commit()
    db.refresh(user)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="user_role_updated",
        message=f"Роль пользователя {user.email} изменена на {new_role}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "target_user_id": str(user.id),
            "old_role": target_role,
            "new_role": new_role
        }
    )

    return {"status": "ok", "id": str(user.id), "new_role": user.role}


@router.post("/stream/start")
@audit_update("stream")
def start_stream(db: Session = Depends(get_db), current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    success = controller.start_stream()
    if not success:
        # Логируем ошибку запуска
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="stream_error",
            message="Не удалось запустить трансляцию",
            user_id=current_user.id,
            user_email=current_user.email,
            details={"operation": "start", "error": "Controller returned failure"}
        )
        raise HTTPException(status_code=500, detail="Failed to start stream")
    
    # Логируем событие запуска трансляции
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="stream_started",
        message="Трансляция запущена",
        user_id=current_user.id,
        user_email=current_user.email
    )
    
    return {"status": "success", "message": "Stream started"}

@router.post("/stream/stop")
@audit_update("stream")
def stop_stream(db: Session = Depends(get_db), current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    success = controller.stop_stream()
    if not success:
        # Логируем ошибку остановки
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="stream_error",
            message="Не удалось остановить трансляцию",
            user_id=current_user.id,
            user_email=current_user.email,
            details={"operation": "stop", "error": "Controller returned failure"}
        )
        raise HTTPException(status_code=500, detail="Failed to stop stream")

    # Логируем событие остановки трансляции
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="stream_stopped",
        message="Трансляция остановлена",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {"status": "success", "message": "Stream stopped"}

@router.post("/stream/restart")
@audit_update("stream")
def restart_stream(db: Session = Depends(get_db), current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    """
    Restarts the video stream service.
    Only accessible by admins.
    """
    success = controller.restart_stream()
    if not success:
        # Логируем ошибку перезапуска
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="stream_error",
            message="Не удалось перезапустить трансляцию",
            user_id=current_user.id,
            user_email=current_user.email,
            details={"operation": "restart", "error": "Controller returned failure"}
        )
        raise HTTPException(status_code=500, detail="Failed to restart stream")
    
    # Логируем перезапуск как последовательность stop->start
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="stream_started",
        message="Трансляция перезапущена",
        user_id=current_user.id,
        user_email=current_user.email,
        details={"operation": "restart"}
    )
    
    return {"status": "success", "message": "Stream restarted"}

@router.get("/stream/status")
@audit_read("stream")
def get_stream_status(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Get comprehensive stream status including:
    - Online/offline status
    - Currently playing track
    - Queue length
    - Uptime
    """
    try:
        # Get metrics from Redis
        metrics_json = redis_client.get('streamer:metrics:latest')
        metrics = json.loads(metrics_json) if metrics_json else None
        
        # Get stream state from Redis
        state_json = redis_client.get('streamer:state')
        state = json.loads(state_json) if state_json else {}
        
        # Get currently playing track from database
        current_track = db.query(PlaylistItem).filter(
            PlaylistItem.status == 'playing'
        ).first()
        
        # Get queue stats
        queue_total = db.query(PlaylistItem).count()
        queue_queued = db.query(PlaylistItem).filter(PlaylistItem.status == 'queued').count()
        
        return {
            "online": metrics is not None or state.get("status") == "running",
            "status": state.get("status", "unknown"),
            "uptime_seconds": state.get("uptime_seconds", 0),
            "current_track": {
                "id": str(current_track.id) if current_track else None,
                "title": current_track.title if current_track else None,
                "url": current_track.url if current_track else None,
                "duration": current_track.duration if current_track else None,
                "type": current_track.type if current_track else None,
            } if current_track else None,
            "queue": {
                "total": queue_total,
                "queued": queue_queued,
            },
            "metrics": metrics,
        }
    except Exception as e:
        # Return offline status on error
        return {
            "online": False,
            "status": "error",
            "error": str(e),
            "current_track": None,
            "queue": {"total": 0, "queued": 0},
            "metrics": None,
        }

@router.get("/stream/logs")
def get_stream_logs(lines: int = 100, current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    logs = controller.get_logs(lines)
    return {"logs": logs}

@router.get("/stream/metrics")
def get_stream_metrics(current_user: User = Depends(require_admin)):
    try:
        metrics_json = redis_client.get('streamer:metrics:latest')
        metrics = json.loads(metrics_json) if metrics_json else None
        return {
            "online": metrics is not None,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/playlist")
def get_playlist(current_user: User = Depends(require_admin)):
    items = playlist_service.get_playlist()
    return {"items": items}

@router.post("/playlist")
@audit_update("playlist")
def update_playlist(playlist: PlaylistUpdate, current_user: User = Depends(require_admin)):
    success = playlist_service.update_playlist(playlist.items)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update playlist")
    return {"status": "success", "items": playlist.items}

# ============================================================================
# Feature 022 Phase 2: Stream Quality Monitoring Endpoints
# ============================================================================

@router.get("/stream/quality/{stream_url:path}", response_model=Optional[StreamQualityResponse])
async def get_stream_quality(
    stream_url: str,
    timeout: int = Query(10, ge=1, le=30, description="FFprobe timeout in seconds"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    current_user: User = Depends(require_admin),
    quality_service: StreamQualityService = Depends(get_stream_quality_service)
):
    """
    Feature 022 Phase 2: Получить информацию о качестве потока
    
    Анализирует аудио/видео поток и возвращает метрики качества:
    - Кодек (audio/video)
    - Битрейт
    - Разрешение (для видео)
    - FPS (для видео)
    - Уровень качества (low/medium/high/lossless/ultra)
    
    Parameters:
        stream_url: URL потока для анализа
        timeout: Таймаут FFprobe (1-30 сек)
        use_cache: Использовать кеш результатов (5-мин TTL)
    
    Returns:
        StreamQualityResponse с информацией о качестве или null
    
    Example:
        GET /api/admin/stream/quality/https://example.com/audio.mp3
        Returns:
        {
            "url": "https://example.com/audio.mp3",
            "audio": {
                "codec": "opus",
                "bitrate_kbps": 96,
                "sample_rate_hz": 48000,
                "channels": 2,
                "duration_sec": 180.5,
                "quality": "medium"
            },
            "video": null,
            "is_audio_only": true,
            "overall_quality": "medium"
        }
    """
    try:
        quality = await quality_service.analyze_stream_quality(
            stream_url,
            timeout=timeout,
            use_cache=use_cache,
            force=False
        )
        return quality
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze stream quality: {str(e)}"
        )


@router.get("/streams/quality/batch", response_model=Dict[str, Optional[StreamQualityResponse]])
async def batch_analyze_streams(
    urls: List[str] = Query(..., description="List of stream URLs to analyze"),
    timeout: int = Query(10, ge=1, le=30, description="FFprobe timeout per stream"),
    current_user: User = Depends(require_admin),
    quality_service: StreamQualityService = Depends(get_stream_quality_service)
):
    """
    Feature 022 Phase 2: Batch анализ качества множественных потоков
    
    Параллельно анализирует качество нескольких потоков.
    
    Parameters:
        urls: Список URL потоков для анализа
        timeout: Таймаут FFprobe на каждый поток (1-30 сек)
    
    Returns:
        Dict {url: StreamQualityResponse} для каждого потока
    
    Example:
        GET /api/admin/streams/quality/batch?urls=https://example1.com/audio.mp3&urls=https://example2.com/video.mp4
        Returns:
        {
            "https://example1.com/audio.mp3": {...},
            "https://example2.com/video.mp4": {...}
        }
    """
    try:
        results = await quality_service.analyze_batch_streams(
            urls,
            timeout=timeout
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch analyze streams: {str(e)}"
        )


@router.post("/quality/cache/clear")
@audit_update("stream")
async def clear_quality_cache(
    stream_url: Optional[str] = Query(None, description="Clear cache for specific URL (or all if None)"),
    current_user: User = Depends(require_admin),
    quality_service: StreamQualityService = Depends(get_stream_quality_service)
):
    """
    Feature 022 Phase 2: Очистить кеш результатов анализа качества

    Очищает кешированные результаты анализа потоков.

    Parameters:
        stream_url: URL потока для очистки (None = очистить весь кеш)

    Returns:
        Статус операции
    """
    try:
        quality_service.clear_cache(stream_url)
        return {
            "status": "success",
            "message": f"Cache cleared for {stream_url if stream_url else 'all streams'}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


# ========== Feature 022 Phase 3: Trends & Alerts ==========

@router.get("/stream/quality/trend/{stream_url:path}", response_model=QualityTrendData)
@audit_export("stream")
async def get_quality_trend(
    stream_url: str,
    hours: int = Query(24, ge=1, le=168, description="Number of hours of history (1-168, default 24)"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Feature 022 Phase 3: Получить тренд качества потока за N часов

    Возвращает историческую информацию о качестве потока для построения графиков.

    Parameters:
        stream_url: URL потока
        hours: Количество часов истории (1-168, по умолчанию 24)

    Returns:
        QualityTrendData с историей и статистикой

    Example:
        GET /api/admin/stream/quality/trend/http://stream.local?hours=24

        Response:
        {
            "stream_url": "http://stream.local",
            "stream_name": "My Stream",
            "history": [
                {
                    "timestamp": "2025-12-16T10:00:00",
                    "overall_quality": "high",
                    "audio_quality": "high",
                    "audio_bitrate_kbps": 128,
                    ...
                },
                ...
            ],
            "average_quality": "high",
            "min_quality": "medium",
            "max_quality": "high",
            "success_rate": 0.95,
            "samples_count": 288,
            ...
        }
    """
    try:
        trend = await trends_service.get_quality_trend(db, stream_url, hours)
        return trend
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality trend: {str(e)}"
        )


@router.post("/stream/quality/alert/config", response_model=QualityAlertConfigResponse)
async def set_quality_alert_config(
    config: QualityAlertConfigUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Feature 022 Phase 3: Установить конфигурацию alert для потока
    
    Создаёт или обновляет конфигурацию для отправки alert'ов при падении качества.
    
    Request Body:
        {
            "stream_url": "http://stream.local",
            "stream_name": "My Stream",
            "min_overall_quality": "high",
            "min_audio_bitrate_kbps": 128,
            "min_video_bitrate_kbps": 2000,
            "min_video_resolution": "1280x720",
            "enabled": true,
            "notify_on_degradation": true,
            "notify_on_recovery": true,
            "consecutive_failures": 3,
            "alert_channels": {
                "telegram": [123456789],
                "email": ["admin@example.com"]
            }
        }
    
    Returns:
        QualityAlertConfigResponse с обновленной конфигурацией
    """
    try:
        updated_config = await trends_service.set_alert_config(db, config)
        return updated_config
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set alert config: {str(e)}"
        )


@router.get("/stream/quality/alert/config/{stream_url:path}", response_model=Optional[QualityAlertConfigResponse])
async def get_quality_alert_config(
    stream_url: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    trends_service: QualityTrendsService = Depends(get_quality_trends_service)
):
    """
    Feature 022 Phase 3: Получить конфигурацию alert для потока
    
    Parameters:
        stream_url: URL потока
    
    Returns:
        QualityAlertConfigResponse или null если конфигурация не существует
        
    Example:
        GET /api/admin/stream/quality/alert/config/http://stream.local
    """
    try:
        config = await trends_service.get_alert_config(db, stream_url)
        return config
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alert config: {str(e)}"
        )
