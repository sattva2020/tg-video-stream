"""
Metrics API Endpoints

Предоставляет:
- /metrics — Prometheus формат (OpenMetrics)
- /api/v1/metrics/system — JSON формат для фронтенда

Интеграция с prometheus_client для сбора метрик.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
    CollectorRegistry,
    REGISTRY,
)

from src.services.prometheus_metrics import prometheus_helper

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics endpoint",
    description="Returns metrics in Prometheus/OpenMetrics format for scraping",
    response_class=Response,
    tags=["Metrics"]
)
async def prometheus_metrics():
    """
    Возвращает метрики в формате Prometheus.
    
    Используется Prometheus для периодического scraping.
    Формат: OpenMetrics (text/plain).
    
    Returns:
        Response: Метрики в формате Prometheus
    """
    try:
        # Генерируем метрики из default registry
        metrics_output = generate_latest(REGISTRY)
        
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        log.error(f"Failed to generate Prometheus metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )


@router.get(
    "/api/v1/metrics/system",
    summary="System metrics in JSON format",
    description="Returns system metrics for frontend dashboards",
    response_model=Dict[str, Any],
    tags=["Metrics"]
)
async def system_metrics_json():
    """
    Возвращает системные метрики в JSON формате.
    
    Предназначен для frontend дашбордов.
    Включает:
    - CPU usage
    - Memory usage
    - Disk usage
    - Stream statistics
    - Queue statistics
    
    Returns:
        Dict: Системные метрики
    """
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        memory = psutil.virtual_memory()
        
        # Disk
        disk = psutil.disk_usage('/')
        
        # Stream/Queue статистика из Prometheus метрик
        stream_stats = prometheus_helper.get_current_values()
        
        return {
            "status": "ok",
            "system": {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": cpu_count
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total_bytes": disk.total,
                    "used_bytes": disk.used,
                    "free_bytes": disk.free,
                    "percent": disk.percent
                }
            },
            "streams": stream_stats.get("streams", {}),
            "queue": stream_stats.get("queue", {}),
            "http": stream_stats.get("http", {})
        }
        
    except Exception as e:
        log.error(f"Failed to get system metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get(
    "/api/v1/metrics/streams",
    summary="Stream-specific metrics",
    description="Returns metrics specific to active streams",
    response_model=Dict[str, Any],
    tags=["Metrics"]
)
async def stream_metrics():
    """
    Возвращает метрики по активным стримам.
    
    Returns:
        Dict: Метрики стримов
    """
    try:
        stats = prometheus_helper.get_current_values()
        
        return {
            "status": "ok",
            "active_streams": stats.get("streams", {}).get("active", 0),
            "total_listeners": stats.get("streams", {}).get("listeners", 0),
            "queue_size": stats.get("queue", {}).get("size", 0),
            "auto_end_triggers": stats.get("auto_end", {}).get("triggers", 0)
        }
        
    except Exception as e:
        log.error(f"Failed to get stream metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
