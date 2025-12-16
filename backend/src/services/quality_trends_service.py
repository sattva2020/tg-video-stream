"""
Feature 022 Phase 3: Stream Quality Trends Service

Сервис для анализа трендов качества потока, сохранения истории и управления alerts.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from src.models.stream_quality import StreamQualityHistory, QualityAlertConfig, QualityTrendSnapshot
from src.schemas.stream_quality import (
    QualityTrendData, 
    QualityHistoryPoint,
    QualityAlertConfigUpdate,
    QualityAlertConfigResponse,
    QualityAlertEvent,
)

logger = logging.getLogger(__name__)


class QualityTrendsService:
    """Singleton сервис для управления трендами качества"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def record_quality_analysis(
        self,
        db: Session,
        stream_url: str,
        stream_name: Optional[str] = None,
        audio_codec: Optional[str] = None,
        audio_bitrate_kbps: Optional[int] = None,
        audio_sample_rate_hz: Optional[int] = None,
        audio_channels: Optional[int] = None,
        audio_quality: Optional[str] = None,
        video_codec: Optional[str] = None,
        video_bitrate_kbps: Optional[int] = None,
        video_resolution: Optional[str] = None,
        video_fps: Optional[float] = None,
        video_quality: Optional[str] = None,
        overall_quality: str = "unknown",
        is_audio_only: bool = False,
        is_video_only: bool = False,
        analysis_duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        raw_data: Optional[Dict] = None,
    ) -> StreamQualityHistory:
        """
        Сохраняет результат анализа качества в историю
        
        Args:
            db: Сессия БД
            stream_url: URL потока
            stream_name: Человеческое имя потока
            audio_codec, audio_bitrate_kbps, ...: Метрики качества
            overall_quality: Общее качество
            success: Успешен ли анализ
            raw_data: JSON с исходными данными
            
        Returns:
            Созданная запись в БД
        """
        try:
            history = StreamQualityHistory(
                stream_url=stream_url,
                stream_name=stream_name,
                audio_codec=audio_codec,
                audio_bitrate_kbps=audio_bitrate_kbps,
                audio_sample_rate_hz=audio_sample_rate_hz,
                audio_channels=audio_channels,
                audio_quality=audio_quality,
                video_codec=video_codec,
                video_bitrate_kbps=video_bitrate_kbps,
                video_resolution=video_resolution,
                video_fps=video_fps,
                video_quality=video_quality,
                overall_quality=overall_quality,
                is_audio_only=is_audio_only,
                is_video_only=is_video_only,
                analysis_duration_ms=analysis_duration_ms,
                success=success,
                error_message=error_message,
                raw_data=raw_data,
                analyzed_at=datetime.utcnow(),
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            
            logger.debug(f"Recorded quality for {stream_url}: {overall_quality}")
            
            # После записи проверяем alerts
            await self._check_and_trigger_alerts(db, stream_url, overall_quality)
            
            return history
        except Exception as e:
            logger.error(f"Error recording quality analysis: {e}")
            db.rollback()
            raise
    
    async def get_quality_trend(
        self,
        db: Session,
        stream_url: str,
        hours: int = 24,
    ) -> QualityTrendData:
        """
        Получает тренд качества за последние N часов
        
        Args:
            db: Сессия БД
            stream_url: URL потока
            hours: Количество часов истории (по умолчанию 24)
            
        Returns:
            QualityTrendData с историей и статистикой
        """
        try:
            # Получаем записи за период
            period_start = datetime.utcnow() - timedelta(hours=hours)
            
            histories = db.query(StreamQualityHistory).filter(
                and_(
                    StreamQualityHistory.stream_url == stream_url,
                    StreamQualityHistory.analyzed_at >= period_start,
                    StreamQualityHistory.success == True,
                )
            ).order_by(StreamQualityHistory.analyzed_at).all()
            
            if not histories:
                logger.warning(f"No quality history found for {stream_url}")
                return QualityTrendData(
                    stream_url=stream_url,
                    history=[],
                    average_quality="unknown",
                    min_quality="unknown",
                    max_quality="unknown",
                    success_rate=0.0,
                    period_start=period_start,
                    period_end=datetime.utcnow(),
                    samples_count=0,
                )
            
            # Конвертируем в QualityHistoryPoint
            history_points = [
                QualityHistoryPoint(
                    timestamp=h.analyzed_at,
                    overall_quality=h.overall_quality,
                    audio_quality=h.audio_quality,
                    audio_bitrate_kbps=h.audio_bitrate_kbps,
                    video_quality=h.video_quality,
                    video_bitrate_kbps=h.video_bitrate_kbps,
                    video_resolution=h.video_resolution,
                    video_fps=h.video_fps,
                    success=h.success,
                    error_message=h.error_message,
                )
                for h in histories
            ]
            
            # Вычисляем статистику
            quality_levels = [self._quality_to_number(h.overall_quality) for h in histories]
            audio_bitrates = [h.audio_bitrate_kbps for h in histories if h.audio_bitrate_kbps]
            video_bitrates = [h.video_bitrate_kbps for h in histories if h.video_bitrate_kbps]
            
            avg_quality_num = sum(quality_levels) / len(quality_levels) if quality_levels else 0
            min_quality_num = min(quality_levels) if quality_levels else 0
            max_quality_num = max(quality_levels) if quality_levels else 0
            
            # Получаем count успешных анализов
            total_count = db.query(StreamQualityHistory).filter(
                and_(
                    StreamQualityHistory.stream_url == stream_url,
                    StreamQualityHistory.analyzed_at >= period_start,
                )
            ).count()
            
            success_rate = len(histories) / total_count if total_count > 0 else 0.0
            
            return QualityTrendData(
                stream_url=stream_url,
                stream_name=histories[0].stream_name,
                history=history_points,
                average_quality=self._number_to_quality(avg_quality_num),
                min_quality=self._number_to_quality(min_quality_num),
                max_quality=self._number_to_quality(max_quality_num),
                audio_avg_bitrate_kbps=int(sum(audio_bitrates) / len(audio_bitrates)) if audio_bitrates else None,
                video_avg_bitrate_kbps=int(sum(video_bitrates) / len(video_bitrates)) if video_bitrates else None,
                success_rate=success_rate,
                period_start=period_start,
                period_end=datetime.utcnow(),
                samples_count=len(histories),
            )
        except Exception as e:
            logger.error(f"Error getting quality trend: {e}")
            raise
    
    async def set_alert_config(
        self,
        db: Session,
        config_update: QualityAlertConfigUpdate,
    ) -> QualityAlertConfigResponse:
        """
        Создаёт или обновляет конфигурацию alert для потока
        
        Args:
            db: Сессия БД
            config_update: Данные для обновления
            
        Returns:
            Обновленная конфигурация
        """
        try:
            # Получаем существующий или создаём новый
            config = db.query(QualityAlertConfig).filter(
                QualityAlertConfig.stream_url == config_update.stream_url
            ).first()
            
            if not config:
                config = QualityAlertConfig(
                    stream_url=config_update.stream_url,
                    stream_name=config_update.stream_name,
                    min_overall_quality=config_update.min_overall_quality or "medium",
                )
            
            # Обновляем поля
            if config_update.stream_name is not None:
                config.stream_name = config_update.stream_name
            if config_update.min_overall_quality is not None:
                config.min_overall_quality = config_update.min_overall_quality
            if config_update.min_audio_quality is not None:
                config.min_audio_quality = config_update.min_audio_quality
            if config_update.min_video_quality is not None:
                config.min_video_quality = config_update.min_video_quality
            if config_update.min_audio_bitrate_kbps is not None:
                config.min_audio_bitrate_kbps = config_update.min_audio_bitrate_kbps
            if config_update.min_video_bitrate_kbps is not None:
                config.min_video_bitrate_kbps = config_update.min_video_bitrate_kbps
            if config_update.min_video_resolution is not None:
                config.min_video_resolution = config_update.min_video_resolution
            if config_update.min_video_fps is not None:
                config.min_video_fps = config_update.min_video_fps
            if config_update.enabled is not None:
                config.enabled = config_update.enabled
            if config_update.notify_on_degradation is not None:
                config.notify_on_degradation = config_update.notify_on_degradation
            if config_update.notify_on_recovery is not None:
                config.notify_on_recovery = config_update.notify_on_recovery
            if config_update.consecutive_failures is not None:
                config.consecutive_failures = config_update.consecutive_failures
            if config_update.alert_channels is not None:
                config.alert_channels = config_update.alert_channels
            
            config.updated_at = datetime.utcnow()
            
            db.add(config)
            db.commit()
            db.refresh(config)
            
            logger.info(f"Updated alert config for {config_update.stream_url}")
            
            return QualityAlertConfigResponse.from_orm(config)
        except Exception as e:
            logger.error(f"Error setting alert config: {e}")
            db.rollback()
            raise
    
    async def get_alert_config(
        self,
        db: Session,
        stream_url: str,
    ) -> Optional[QualityAlertConfigResponse]:
        """Получает конфигурацию alert для потока"""
        try:
            config = db.query(QualityAlertConfig).filter(
                QualityAlertConfig.stream_url == stream_url
            ).first()
            
            if not config:
                return None
            
            return QualityAlertConfigResponse.from_orm(config)
        except Exception as e:
            logger.error(f"Error getting alert config: {e}")
            raise
    
    async def _check_and_trigger_alerts(
        self,
        db: Session,
        stream_url: str,
        current_quality: str,
    ) -> Optional[QualityAlertEvent]:
        """
        Проверяет пороги и генерирует alert если нужно
        
        Может быть вызвано асинхронно в фоне
        """
        try:
            config = db.query(QualityAlertConfig).filter(
                QualityAlertConfig.stream_url == stream_url
            ).first()
            
            if not config or not config.enabled:
                return None
            
            # Проверяем пороги
            failed_checks = []
            
            if self._quality_to_number(current_quality) < self._quality_to_number(config.min_overall_quality):
                failed_checks.append(f"overall_quality_{current_quality}<{config.min_overall_quality}")
            
            if failed_checks:
                config.consecutive_failures_count += 1
                
                # Если количество падений достаточно, генерируем alert
                if config.consecutive_failures_count >= config.consecutive_failures:
                    alert = QualityAlertEvent(
                        stream_url=stream_url,
                        stream_name=config.stream_name,
                        alert_type="degradation",
                        severity="warning",
                        message=f"Stream quality degraded to {current_quality}",
                        previous_quality=None,
                        current_quality=current_quality,
                        failed_checks=failed_checks,
                        triggered_at=datetime.utcnow(),
                    )
                    
                    config.last_alert_at = datetime.utcnow()
                    config.last_alert_type = "degradation"
                    
                    db.add(config)
                    db.commit()
                    
                    logger.warning(f"Alert triggered for {stream_url}: {alert.message}")
                    return alert
            else:
                # Качество восстановилось
                if config.consecutive_failures_count > 0 and config.notify_on_recovery:
                    alert = QualityAlertEvent(
                        stream_url=stream_url,
                        stream_name=config.stream_name,
                        alert_type="recovery",
                        severity="info",
                        message=f"Stream quality recovered to {current_quality}",
                        previous_quality=None,
                        current_quality=current_quality,
                        failed_checks=[],
                        triggered_at=datetime.utcnow(),
                    )
                    
                    config.consecutive_failures_count = 0
                    config.last_alert_at = datetime.utcnow()
                    config.last_alert_type = "recovery"
                    
                    db.add(config)
                    db.commit()
                    
                    logger.info(f"Recovery alert for {stream_url}")
                    return alert
                
                config.consecutive_failures_count = 0
                db.add(config)
                db.commit()
            
            return None
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return None
    
    @staticmethod
    def _quality_to_number(quality: str) -> float:
        """Конвертирует качество в число для сравнения"""
        mapping = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "lossless": 4,
            "ultra": 5,
            "unknown": 0,
        }
        return float(mapping.get(quality.lower(), 0))
    
    @staticmethod
    def _number_to_quality(num: float) -> str:
        """Конвертирует число обратно в качество"""
        if num < 0.5:
            return "low"
        elif num < 1.5:
            return "low"
        elif num < 2.5:
            return "medium"
        elif num < 3.5:
            return "high"
        elif num < 4.5:
            return "lossless"
        else:
            return "ultra"


def get_quality_trends_service() -> QualityTrendsService:
    """FastAPI dependency для инъекции сервиса"""
    return QualityTrendsService()
