"""
Feature 019 Phase 3: Latency Monitoring Service

Сервис для мониторинга задержки (latency) live streams, сохранения истории и управления alerts.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from src.models.live_stream import LiveStream, LiveStreamStatus

logger = logging.getLogger(__name__)


class LatencyMonitorService:
    """Singleton сервис для управления мониторингом задержки"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def record_latency_measurement(
        self,
        db: Session,
        live_stream_id: str,
        latency_ms: int,
        viewer_count: Optional[int] = None,
        measurement_source: str = "system",
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> Optional[LiveStream]:
        """
        Записывает измерение задержки в live stream

        Args:
            db: Сессия БД
            live_stream_id: ID live stream
            latency_ms: Задержка в миллисекундах
            viewer_count: Количество зрителей (опционально)
            measurement_source: Источник измерения (system, client, rtmp, webrtc)
            success: Успешно ли измерение
            error_message: Сообщение об ошибке если есть

        Returns:
            Обновленный LiveStream или None если не найден
        """
        try:
            live_stream = db.query(LiveStream).filter(
                LiveStream.id == live_stream_id
            ).first()

            if not live_stream:
                logger.warning(f"LiveStream {live_stream_id} not found for latency measurement")
                return None

            # Обновляем latency_ms
            live_stream.latency_ms = latency_ms

            # Обновляем viewer_count если предоставлен
            if viewer_count is not None:
                live_stream.viewer_count = viewer_count
                live_stream.last_viewer_update = datetime.utcnow()

            # Если измерение неудачно, обновляем error поля
            if not success:
                live_stream.last_error = error_message or "Latency measurement failed"
                live_stream.error_count += 1

            live_stream.updated_at = datetime.utcnow()

            db.add(live_stream)
            db.commit()
            db.refresh(live_stream)

            logger.debug(f"Recorded latency {latency_ms}ms for {live_stream_id}")

            # После записи проверяем пороги и alerts
            await self._check_and_trigger_alerts(db, live_stream_id, latency_ms)

            return live_stream
        except Exception as e:
            logger.error(f"Error recording latency measurement: {e}")
            db.rollback()
            raise

    async def get_current_latency(
        self,
        db: Session,
        live_stream_id: str,
    ) -> Optional[Dict]:
        """
        Получает текущую задержку потока

        Args:
            db: Сессия БД
            live_stream_id: ID live stream

        Returns:
            Словарь с информацией о задержке или None
        """
        try:
            live_stream = db.query(LiveStream).filter(
                LiveStream.id == live_stream_id
            ).first()

            if not live_stream:
                logger.warning(f"LiveStream {live_stream_id} not found")
                return None

            return {
                "live_stream_id": str(live_stream.id),
                "title": live_stream.title,
                "latency_ms": live_stream.latency_ms,
                "viewer_count": live_stream.viewer_count,
                "status": live_stream.status.value,
                "ingestion_type": live_stream.ingestion_type.value,
                "last_viewer_update": live_stream.last_viewer_update.isoformat() if live_stream.last_viewer_update else None,
                "is_over_threshold": live_stream.latency_ms is not None and live_stream.latency_ms > 5000,  # 5s threshold
            }
        except Exception as e:
            logger.error(f"Error getting current latency: {e}")
            raise

    async def get_latency_trend(
        self,
        db: Session,
        live_stream_id: str,
        hours: int = 1,
    ) -> Dict:
        """
        Получает тренд задержки за последние N часов

        Note: Поскольку у нас нет отдельной таблицы истории задержки,
        этот метод возвращает агрегированную статистику из текущего состояния.

        Args:
            db: Сессия БД
            live_stream_id: ID live stream
            hours: Количество часов (для будущей истории)

        Returns:
            Словарь со статистикой задержки
        """
        try:
            live_stream = db.query(LiveStream).filter(
                LiveStream.id == live_stream_id
            ).first()

            if not live_stream:
                logger.warning(f"LiveStream {live_stream_id} not found")
                return {
                    "live_stream_id": live_stream_id,
                    "current_latency_ms": None,
                    "average_latency_ms": None,
                    "max_latency_ms": None,
                    "min_latency_ms": None,
                    "samples_count": 0,
                    "period_start": datetime.utcnow() - timedelta(hours=hours),
                    "period_end": datetime.utcnow(),
                    "is_healthy": False,
                }

            # TODO: Когда будет добавлена таблица latency_history, здесь будет запрос к истории
            # Сейчас возвращаем текущие значения
            current_latency = live_stream.latency_ms

            return {
                "live_stream_id": str(live_stream.id),
                "title": live_stream.title,
                "current_latency_ms": current_latency,
                "average_latency_ms": current_latency,  # TODO: Calculate from history
                "max_latency_ms": current_latency,  # TODO: Calculate from history
                "min_latency_ms": current_latency,  # TODO: Calculate from history
                "samples_count": 1 if current_latency else 0,
                "period_start": datetime.utcnow() - timedelta(hours=hours),
                "period_end": datetime.utcnow(),
                "is_healthy": current_latency is None or current_latency <= 5000,  # 5s threshold
                "status": live_stream.status.value,
                "ingestion_type": live_stream.ingestion_type.value,
                "viewer_count": live_stream.viewer_count,
            }
        except Exception as e:
            logger.error(f"Error getting latency trend: {e}")
            raise

    async def get_all_streams_latency(
        self,
        db: Session,
        active_only: bool = True,
    ) -> List[Dict]:
        """
        Получает задержку для всех live streams

        Args:
            db: Сессия БД
            active_only: Только активные потоки

        Returns:
            Список словарей с информацией о задержке
        """
        try:
            query = db.query(LiveStream)

            if active_only:
                query = query.filter(LiveStream.status == LiveStreamStatus.ACTIVE)

            streams = query.all()

            result = []
            for stream in streams:
                result.append({
                    "live_stream_id": str(stream.id),
                    "title": stream.title,
                    "chat_id": stream.chat_id,
                    "latency_ms": stream.latency_ms,
                    "viewer_count": stream.viewer_count,
                    "status": stream.status.value,
                    "ingestion_type": stream.ingestion_type.value,
                    "is_over_threshold": stream.latency_ms is not None and stream.latency_ms > 5000,
                    "last_viewer_update": stream.last_viewer_update.isoformat() if stream.last_viewer_update else None,
                })

            return result
        except Exception as e:
            logger.error(f"Error getting all streams latency: {e}")
            raise

    async def update_latency_from_ingest(
        self,
        db: Session,
        live_stream_id: str,
        latency_ms: int,
        source_type: str,
    ) -> Optional[LiveStream]:
        """
        Обновляет задержку из ingest сервера (RTMP/SRT/WebRTC)

        Args:
            db: Сессия БД
            live_stream_id: ID live stream
            latency_ms: Задержка в миллисекундах
            source_type: Тип источника (rtmp, srt, webrtc)

        Returns:
            Обновленный LiveStream или None
        """
        try:
            return await self.record_latency_measurement(
                db=db,
                live_stream_id=live_stream_id,
                latency_ms=latency_ms,
                measurement_source=source_type,
                success=True,
            )
        except Exception as e:
            logger.error(f"Error updating latency from ingest: {e}")
            raise

    async def check_latency_health(
        self,
        db: Session,
        live_stream_id: str,
        threshold_ms: int = 5000,
    ) -> Dict:
        """
        Проверяет здоровье задержки потока

        Args:
            db: Сессия БД
            live_stream_id: ID live stream
            threshold_ms: Порог задержки в миллисекундах (по умолчанию 5s)

        Returns:
            Словарь с информацией о здоровье
        """
        try:
            live_stream = db.query(LiveStream).filter(
                LiveStream.id == live_stream_id
            ).first()

            if not live_stream:
                return {
                    "live_stream_id": live_stream_id,
                    "is_healthy": False,
                    "reason": "Stream not found",
                }

            if live_stream.latency_ms is None:
                return {
                    "live_stream_id": str(live_stream.id),
                    "is_healthy": True,  # Нет данных = не было проблем
                    "reason": "No latency measurements yet",
                    "latency_ms": None,
                    "threshold_ms": threshold_ms,
                }

            is_over_threshold = live_stream.latency_ms > threshold_ms

            return {
                "live_stream_id": str(live_stream.id),
                "is_healthy": not is_over_threshold,
                "latency_ms": live_stream.latency_ms,
                "threshold_ms": threshold_ms,
                "over_by_ms": live_stream.latency_ms - threshold_ms if is_over_threshold else 0,
                "reason": f"Latency {'over' if is_over_threshold else 'under'} threshold",
            }
        except Exception as e:
            logger.error(f"Error checking latency health: {e}")
            raise

    async def _check_and_trigger_alerts(
        self,
        db: Session,
        live_stream_id: str,
        current_latency_ms: int,
    ) -> Optional[Dict]:
        """
        Проверяет пороги и генерирует alert если нужно

        Note: Это упрощенная версия. В будущем можно добавить:
        - Конфигурируемые пороги для каждого потока
        - Отправку уведомлений (telegram, email)
        - Историю alerts

        Args:
            db: Сессия БД
            live_stream_id: ID live stream
            current_latency_ms: Текущая задержка

        Returns:
            Alert event или None
        """
        try:
            # Порог задержки по умолчанию: 5 секунд
            threshold_ms = 5000

            if current_latency_ms > threshold_ms:
                alert = {
                    "live_stream_id": live_stream_id,
                    "alert_type": "high_latency",
                    "severity": "warning" if current_latency_ms < 10000 else "error",
                    "message": f"Stream latency {current_latency_ms}ms exceeds threshold {threshold_ms}ms",
                    "current_latency_ms": current_latency_ms,
                    "threshold_ms": threshold_ms,
                    "over_by_ms": current_latency_ms - threshold_ms,
                    "triggered_at": datetime.utcnow().isoformat(),
                }

                logger.warning(f"Latency alert triggered for {live_stream_id}: {alert['message']}")
                return alert

            return None
        except Exception as e:
            logger.error(f"Error checking latency alerts: {e}")
            return None

    async def get_latency_stats(
        self,
        db: Session,
        live_stream_id: str,
    ) -> Dict:
        """
        Получает статистику задержки потока

        Args:
            db: Сессия БД
            live_stream_id: ID live stream

        Returns:
            Словарь со статистикой
        """
        try:
            live_stream = db.query(LiveStream).filter(
                LiveStream.id == live_stream_id
            ).first()

            if not live_stream:
                return {
                    "live_stream_id": live_stream_id,
                    "exists": False,
                }

            return {
                "live_stream_id": str(live_stream.id),
                "exists": True,
                "title": live_stream.title,
                "status": live_stream.status.value,
                "ingestion_type": live_stream.ingestion_type.value,
                "current_latency_ms": live_stream.latency_ms,
                "viewer_count": live_stream.viewer_count,
                "error_count": live_stream.error_count,
                "last_error": live_stream.last_error,
                "last_viewer_update": live_stream.last_viewer_update.isoformat() if live_stream.last_viewer_update else None,
                "created_at": live_stream.created_at.isoformat() if live_stream.created_at else None,
                "started_at": live_stream.started_at.isoformat() if live_stream.started_at else None,
                "went_live_at": live_stream.went_live_at.isoformat() if live_stream.went_live_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting latency stats: {e}")
            raise


def get_latency_monitor_service() -> LatencyMonitorService:
    """FastAPI dependency для инъекции сервиса"""
    return LatencyMonitorService()
