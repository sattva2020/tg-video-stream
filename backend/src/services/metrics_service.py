"""
Metrics Service
Spec: 015-real-system-monitoring

Сервис для сбора системных метрик через psutil и pg_stat_activity.
Используется для отображения в блоке "Здоровье системы" на Dashboard.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional

import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.schemas.system import SystemMetricsResponse


logger = logging.getLogger(__name__)

# Время старта приложения для расчёта uptime
_app_start_time: float = time.time()


class MetricsService:
    """
    Сервис сбора системных метрик.
    
    Собирает:
    - CPU usage (psutil.cpu_percent)
    - RAM usage (psutil.virtual_memory)
    - Disk usage (psutil.disk_usage)
    - DB connections (pg_stat_activity)
    - Uptime
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Инициализация сервиса.
        
        Args:
            db: SQLAlchemy сессия для запросов к pg_stat_activity
        """
        self.db = db

    def collect_metrics(self) -> SystemMetricsResponse:
        """
        Собирает все метрики системы.
        
        Returns:
            SystemMetricsResponse с актуальными данными
        """
        try:
            # CPU — использует интервал 0.1 сек для точного измерения
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to get CPU metrics: {e}")
            cpu_percent = 0.0

        try:
            # RAM
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
        except Exception as e:
            logger.warning(f"Failed to get RAM metrics: {e}")
            ram_percent = 0.0

        try:
            # Disk — корневой раздел
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
        except Exception as e:
            logger.warning(f"Failed to get disk metrics: {e}")
            disk_percent = 0.0

        # DB connections
        db_active, db_idle = self._get_db_connections()

        # Uptime
        uptime_seconds = int(time.time() - _app_start_time)

        return SystemMetricsResponse(
            cpu_percent=round(cpu_percent, 1),
            ram_percent=round(ram_percent, 1),
            disk_percent=round(disk_percent, 1),
            db_connections_active=db_active,
            db_connections_idle=db_idle,
            uptime_seconds=uptime_seconds,
            collected_at=datetime.now(timezone.utc)
        )

    def _get_db_connections(self) -> tuple[int, int]:
        """
        Получает количество подключений к PostgreSQL.
        
        Returns:
            Tuple (active, idle) — количество активных и неактивных подключений
        """
        if not self.db:
            return 0, 0

        try:
            # pg_stat_activity — системная view PostgreSQL
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE state = 'active') as active,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle
                FROM pg_stat_activity
                WHERE datname = current_database()
            """))
            row = result.fetchone()
            if row:
                return int(row[0] or 0), int(row[1] or 0)
        except Exception as e:
            logger.warning(f"Failed to get DB connections: {e}")

        return 0, 0

    @staticmethod
    def get_system_uptime() -> int:
        """
        Получает uptime операционной системы.
        
        Returns:
            Uptime в секундах
        """
        try:
            boot_time = psutil.boot_time()
            return int(time.time() - boot_time)
        except Exception as e:
            logger.warning(f"Failed to get system uptime: {e}")
            return 0


def get_metrics_service(db: Optional[Session] = None) -> MetricsService:
    """
    Фабричная функция для создания MetricsService.
    
    Args:
        db: SQLAlchemy сессия (опционально)
    
    Returns:
        Экземпляр MetricsService
    """
    return MetricsService(db=db)
