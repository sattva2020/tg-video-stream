"""
Feature 009 Phase 2: Adaptive Streaming Service

Сервис для управления адаптивным битрейтом потоков с автоматическим выбором качества.
Использует BandwidthMonitor для измерения пропускной способности и AdaptiveStreamConfig для настроек.
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.adaptive_stream_config import AdaptiveStreamConfig
from src.models.stream import Stream
from src.services.bandwidth_monitor import (
    BandwidthMonitor,
    BandwidthStatus,
    get_bandwidth_monitor,
    NetworkCondition
)
from src.schemas.adaptive_streaming import (
    QualityLevel,
    DeviceType,
    QualityProfile,
    AdaptiveStreamingStatus,
    BandwidthMeasurement
)

log = logging.getLogger(__name__)


class QualityChangeReason(str, Enum):
    """Причины изменения качества."""
    BANDWIDTH = "bandwidth"      # Изменение пропускной способности
    DEVICE = "device"           # Смена устройства
    MANUAL = "manual"           # Ручное изменение
    STARTUP = "startup"         # Инициализация
    CONFIG_CHANGE = "config_change"  # Изменение конфигурации


@dataclass
class QualityDecision:
    """Решение о выборе качества."""
    quality: QualityLevel
    reason: QualityChangeReason
    bandwidth_kbps: Optional[float] = None
    device_type: DeviceType = DeviceType.UNKNOWN
    confidence: float = 1.0

    def to_dict(self) -> dict:
        """Конвертировать в словарь."""
        return {
            "quality": self.quality.value,
            "reason": self.reason.value,
            "bandwidth_kbps": self.bandwidth_kbps,
            "device_type": self.device_type.value,
            "confidence": self.confidence
        }


class AdaptiveStreamingService:
    """
    Feature 009 Phase 2: Сервис для управления адаптивным битрейтом

    Предоставляет API для:
    - Выбора оптимального качества на основе пропускной способности
    - Применения правил для различных устройств
    - Автоматического изменения качества при изменении условий
    - Логирования изменений качества
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация сервиса."""
        self._bandwidth_monitor: Optional[BandwidthMonitor] = None
        self._quality_history: Dict[str, List[Dict]] = {}  # stream_id -> history
        self._current_quality: Dict[str, QualityLevel] = {}  # stream_id -> current quality

    def _get_bandwidth_monitor(self) -> BandwidthMonitor:
        """Получить экземпляр BandwidthMonitor."""
        if self._bandwidth_monitor is None:
            self._bandwidth_monitor = get_bandwidth_monitor()
        return self._bandwidth_monitor

    async def get_stream_config(
        self,
        stream_id: str,
        db: AsyncSession
    ) -> Optional[AdaptiveStreamConfig]:
        """
        Получить конфигурацию адаптивного стрима для потока.

        Args:
            stream_id: ID потока (GUID)
            db: Сессия базы данных

        Returns:
            AdaptiveStreamConfig или None
        """
        try:
            result = await db.execute(
                select(AdaptiveStreamConfig).where(
                    AdaptiveStreamConfig.stream_id == stream_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            log.error(f"Error loading config for stream {stream_id}: {e}")
            return None

    async def select_quality_for_stream(
        self,
        stream_id: str,
        device_type: DeviceType = DeviceType.UNKNOWN,
        user_agent: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        force_measurement: bool = False
    ) -> QualityDecision:
        """
        Выбрать оптимальное качество для потока.

        Args:
            stream_id: ID потока
            device_type: Тип устройства
            user_agent: User Agent строка для детекции устройства
            db: Сессия базы данных (опционально)
            force_measurement: Принудительно измерить пропускную способность

        Returns:
            QualityDecision с выбранным качеством
        """
        # Детектируем тип устройства если не указан
        if user_agent and device_type == DeviceType.UNKNOWN:
            device_type = self._detect_device_type(user_agent)

        # Получаем конфигурацию потока
        config = None
        if db:
            config = await self.get_stream_config(stream_id, db)

        # Получаем статус пропускной способности
        bandwidth_status = None
        bandwidth_kbps = None

        if config and config.enable_bandwidth_monitoring:
            monitor = self._get_bandwidth_monitor()

            if force_measurement:
                bandwidth_status = await monitor.measure_bandwidth(stream_id)
            else:
                bandwidth_status = await monitor.get_bandwidth_status(stream_id)

            if bandwidth_status:
                bandwidth_kbps = bandwidth_status.smoothed_bandwidth_kbps

        # Выбираем качество на основе конфигурации и условий
        decision = self._make_quality_decision(
            stream_id=stream_id,
            config=config,
            bandwidth_kbps=bandwidth_kbps,
            device_type=device_type,
            bandwidth_status=bandwidth_status
        )

        # Обновляем текущее качество
        self._current_quality[stream_id] = decision.quality

        # Логируем изменение качества
        await self._log_quality_change(
            stream_id=stream_id,
            decision=decision,
            config=config
        )

        return decision

    def _detect_device_type(self, user_agent: str) -> DeviceType:
        """
        Определить тип устройства по User Agent.

        Args:
            user_agent: User Agent строка

        Returns:
            DeviceType
        """
        user_agent_lower = user_agent.lower()

        # Mobile
        if any(keyword in user_agent_lower for keyword in ['mobile', 'android', 'iphone', 'ipod']):
            return DeviceType.MOBILE

        # Tablet
        if any(keyword in user_agent_lower for keyword in ['ipad', 'tablet']):
            return DeviceType.TABLET

        # TV
        if any(keyword in user_agent_lower for keyword in ['tv', 'television', 'smart-tv']):
            return DeviceType.TV

        # Desktop по умолчанию
        if any(keyword in user_agent_lower for keyword in ['macintosh', 'windows', 'linux', 'x11']):
            return DeviceType.DESKTOP

        return DeviceType.UNKNOWN

    def _make_quality_decision(
        self,
        stream_id: str,
        config: Optional[AdaptiveStreamConfig],
        bandwidth_kbps: Optional[float],
        device_type: DeviceType,
        bandwidth_status: Optional[BandwidthStatus]
    ) -> QualityDecision:
        """
        Принять решение о выборе качества.

        Args:
            stream_id: ID потока
            config: Конфигурация адаптивного стрима
            bandwidth_kbps: Пропускная способность в Kbps
            device_type: Тип устройства
            bandwidth_status: Статус пропускной способности

        Returns:
            QualityDecision
        """
        # Получаем ограничения по качеству
        min_quality = QualityLevel.LOW
        max_quality = QualityLevel.ULTRA
        default_quality = QualityLevel.HIGH

        if config:
            min_quality = QualityLevel(config.min_quality)
            max_quality = QualityLevel(config.max_quality)
            default_quality = QualityLevel(config.default_quality)

        # Проверяем правила для устройства
        device_max_quality = max_quality
        bandwidth_multiplier = 1.0

        if config and config.device_rules and device_type.value in config.device_rules:
            device_rule = config.device_rules[device_type.value]
            device_max_quality = QualityLevel(device_rule.get('max_quality', max_quality.value))
            bandwidth_multiplier = device_rule.get('bandwidth_multiplier', 1.0)

        # Ограничиваем max_quality правилами устройства
        max_quality = min(max_quality, device_max_quality)

        # Если нет данных о пропускной способности, используем default
        if bandwidth_kbps is None or config is None or not config.enable_bandwidth_monitoring:
            return QualityDecision(
                quality=default_quality,
                reason=QualityChangeReason.STARTUP,
                device_type=device_type,
                confidence=0.5
            )

        # Применяем множитель пропускной способности для устройства
        adjusted_bandwidth = bandwidth_kbps * bandwidth_multiplier

        # Выбираем качество на основе порогов
        selected_quality = self._select_quality_by_bandwidth(
            bandwidth_kbps=adjusted_bandwidth,
            config=config,
            min_quality=min_quality,
            max_quality=max_quality
        )

        # Определяем причину изменения
        current_quality = self._current_quality.get(stream_id)
        reason = QualityChangeReason.STARTUP

        if current_quality and current_quality != selected_quality:
            reason = QualityChangeReason.BANDWIDTH
        elif bandwidth_status and bandwidth_status.network_condition == NetworkCondition.POOR:
            # Оставляем текущее качество если сеть плохая для предотвращения скачков
            selected_quality = current_quality or selected_quality
            reason = QualityChangeReason.BANDWIDTH

        # Рассчитываем уверенность в решении
        confidence = self._calculate_confidence(
            bandwidth_status=bandwidth_status,
            config=config
        )

        return QualityDecision(
            quality=selected_quality,
            reason=reason,
            bandwidth_kbps=bandwidth_kbps,
            device_type=device_type,
            confidence=confidence
        )

    def _select_quality_by_bandwidth(
        self,
        bandwidth_kbps: float,
        config: AdaptiveStreamConfig,
        min_quality: QualityLevel,
        max_quality: QualityLevel
    ) -> QualityLevel:
        """
        Выбрать качество на основе пропускной способности.

        Args:
            bandwidth_kbps: Пропускная способность в Kbps
            config: Конфигурация с порогами
            min_quality: Минимальное качество
            max_quality: Максимальное качество

        Returns:
            QualityLevel
        """
        # Получаем пороги из конфигурации
        thresholds = {
            QualityLevel.LOW: config.bandwidth_threshold_low_kbps,
            QualityLevel.MEDIUM: config.bandwidth_threshold_medium_kbps,
            QualityLevel.HIGH: config.bandwidth_threshold_high_kbps,
            QualityLevel.ULTRA: config.bandwidth_threshold_ultra_kbps
        }

        # Определяем порядок качества
        quality_order = [QualityLevel.LOW, QualityLevel.MEDIUM, QualityLevel.HIGH, QualityLevel.ULTRA]

        # Находим минимальный и максимальный индекс
        min_idx = quality_order.index(min_quality)
        max_idx = quality_order.index(max_quality)

        # Выбираем качество на основе порогов
        for quality in reversed(quality_order[min_idx:max_idx + 1]):
            if bandwidth_kbps >= thresholds[quality]:
                return quality

        # Если не подошло ни один порог, возвращаем минимальное
        return min_quality

    def _calculate_confidence(
        self,
        bandwidth_status: Optional[BandwidthStatus],
        config: Optional[AdaptiveStreamConfig]
    ) -> float:
        """
        Рассчитать уверенность в решении о качестве.

        Args:
            bandwidth_status: Статус пропускной способности
            config: Конфигурация

        Returns:
            Confidence score (0.0 - 1.0)
        """
        if not bandwidth_status or not config:
            return 0.5

        # Базовая уверенность
        confidence = 0.5

        # Увеличиваем уверенность при стабильной сети
        if bandwidth_status.network_condition == NetworkCondition.STABLE:
            confidence += 0.3
        elif bandwidth_status.network_condition == NetworkCondition.POOR:
            confidence -= 0.2

        # Увеличиваем уверенность при наличии достаточно измерений
        required = config.consecutive_measurements_required or 3
        if bandwidth_status.measurements_count >= required:
            confidence += 0.2

        # Ограничиваем диапазон
        return max(0.0, min(1.0, confidence))

    async def _log_quality_change(
        self,
        stream_id: str,
        decision: QualityDecision,
        config: Optional[AdaptiveStreamConfig]
    ) -> None:
        """
        Логировать изменение качества.

        Args:
            stream_id: ID потока
            decision: Решение о качестве
            config: Конфигурация
        """
        if not config or not config.enable_quality_logging:
            return

        # Добавляем в историю
        if stream_id not in self._quality_history:
            self._quality_history[stream_id] = []

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quality": decision.quality.value,
            "reason": decision.reason.value,
            "bandwidth_kbps": decision.bandwidth_kbps,
            "device_type": decision.device_type.value,
            "confidence": decision.confidence
        }

        self._quality_history[stream_id].append(event)

        # Ограничиваем размер истории
        max_history = 100
        if len(self._quality_history[stream_id]) > max_history:
            self._quality_history[stream_id] = self._quality_history[stream_id][-max_history:]

        log.info(
            f"Stream {stream_id}: Quality={decision.quality.value}, "
            f"Reason={decision.reason.value}, Bandwidth={decision.bandwidth_kbps:.0f}Kbps"
        )

    async def get_stream_status(
        self,
        stream_id: str,
        db: AsyncSession,
        device_type: DeviceType = DeviceType.UNKNOWN
    ) -> AdaptiveStreamingStatus:
        """
        Получить полный статус адаптивного стрима.

        Args:
            stream_id: ID потока
            db: Сессия базы данных
            device_type: Тип устройства

        Returns:
            AdaptiveStreamingStatus
        """
        # Получаем конфигурацию
        config = await self.get_stream_config(stream_id, db)
        config_dict = None
        if config:
            config_dict = {
                "id": config.id,
                "stream_id": config.stream_id,
                "enabled": config.enabled,
                "default_quality": config.default_quality,
                "min_quality": config.min_quality,
                "max_quality": config.max_quality,
                "bandwidth_threshold_low_kbps": config.bandwidth_threshold_low_kbps,
                "bandwidth_threshold_medium_kbps": config.bandwidth_threshold_medium_kbps,
                "bandwidth_threshold_high_kbps": config.bandwidth_threshold_high_kbps,
                "bandwidth_threshold_ultra_kbps": config.bandwidth_threshold_ultra_kbps,
                "adaptation_interval_seconds": config.adaptation_interval_seconds,
                "bandwidth_smoothing_factor": config.bandwidth_smoothing_factor,
                "consecutive_measurements_required": config.consecutive_measurements_required,
                "device_rules": config.device_rules,
                "quality_profiles": config.quality_profiles,
                "enable_bandwidth_monitoring": config.enable_bandwidth_monitoring,
                "enable_quality_logging": config.enable_quality_logging,
                "statistics": config.statistics,
                "created_at": config.created_at,
                "updated_at": config.updated_at
            }

        # Получаем статус пропускной способности
        monitor = self._get_bandwidth_monitor()
        bandwidth_status = await monitor.get_bandwidth_status(stream_id)

        current_bandwidth = None
        smoothed_bandwidth = None
        last_measurement = None

        if bandwidth_status:
            current_bandwidth = bandwidth_status.current_bandwidth_kbps
            smoothed_bandwidth = bandwidth_status.smoothed_bandwidth_kbps
            last_measurement = bandwidth_status.last_measurement

        # Текущее качество
        current_quality = self._current_quality.get(stream_id, QualityLevel.HIGH)

        # История изменений
        history = self._quality_history.get(stream_id, [])
        total_changes = len(history)

        last_quality_change = None
        if history:
            last_quality_change = datetime.fromisoformat(history[-1]["timestamp"])

        # Рекомендуемое качество
        decision = await self.select_quality_for_stream(
            stream_id=stream_id,
            device_type=device_type,
            db=db
        )

        # Название потока (если есть)
        stream_name = None
        if config and config.stream:
            stream_name = getattr(config.stream, 'name', None)

        return AdaptiveStreamingStatus(
            stream_id=stream_id,
            stream_name=stream_name,
            config=config_dict,
            current_quality=current_quality,
            current_bandwidth_kbps=current_bandwidth,
            smoothed_bandwidth_kbps=smoothed_bandwidth,
            device_type=device_type,
            adaptive_enabled=config.enabled if config else False,
            monitoring_enabled=config.enable_bandwidth_monitoring if config else False,
            is_adapting=False,  # TODO: Определить есть ли активная адаптация
            total_quality_changes=total_changes,
            last_quality_change=last_quality_change,
            last_bandwidth_measurement=last_measurement,
            recommended_quality=decision.quality,
            recommended_action=self._get_recommended_action(decision, current_quality),
            updated_at=datetime.now(timezone.utc)
        )

    def _get_recommended_action(
        self,
        decision: QualityDecision,
        current_quality: QualityLevel
    ) -> Optional[str]:
        """
        Получить рекомендованное действие на основе решения.

        Args:
            decision: Решение о качестве
            current_quality: Текущее качество

        Returns:
            Строка с рекомендацией или None
        """
        if decision.quality != current_quality:
            quality_order = ['low', 'medium', 'high', 'ultra']
            current_idx = quality_order.index(current_quality.value)
            new_idx = quality_order.index(decision.quality.value)

            if new_idx > current_idx:
                return f"Increase quality to {decision.quality.value} for better experience"
            else:
                return f"Decrease quality to {decision.quality.value} to prevent buffering"

        return None

    def get_default_quality_profiles(self) -> Dict[str, QualityProfile]:
        """
        Получить профили качества по умолчанию.

        Returns:
            Dict с профилями качества
        """
        return {
            "low": QualityProfile(
                resolution="640x360",
                video_bitrate_kbps=500,
                audio_bitrate_kbps=64,
                fps=24.0,
                codec="h264"
            ),
            "medium": QualityProfile(
                resolution="854x480",
                video_bitrate_kbps=1500,
                audio_bitrate_kbps=96,
                fps=30.0,
                codec="h264"
            ),
            "high": QualityProfile(
                resolution="1280x720",
                video_bitrate_kbps=3000,
                audio_bitrate_kbps=128,
                fps=30.0,
                codec="h264"
            ),
            "ultra": QualityProfile(
                resolution="1920x1080",
                video_bitrate_kbps=6000,
                audio_bitrate_kbps=192,
                fps=60.0,
                codec="h264"
            )
        }

    async def update_stream_statistics(
        self,
        stream_id: str,
        db: AsyncSession
    ) -> None:
        """
        Обновить статистику адаптивного стрима в базе данных.

        Args:
            stream_id: ID потока
            db: Сессия базы данных
        """
        config = await self.get_stream_config(stream_id, db)
        if not config:
            return

        # Собираем статистику
        history = self._quality_history.get(stream_id, [])
        current_quality = self._current_quality.get(stream_id)

        monitor = self._get_bandwidth_monitor()
        bandwidth_status = await monitor.get_bandwidth_status(stream_id)

        stats = {
            "quality_changes": len(history),
            "last_quality": current_quality.value if current_quality else None,
            "avg_bandwidth_kbps": bandwidth_status.avg_bandwidth_kbps if bandwidth_status else None,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        # Обновляем в базе
        config.statistics = stats
        db.add(config)

        try:
            await db.commit()
        except Exception as e:
            log.error(f"Error updating statistics for stream {stream_id}: {e}")
            await db.rollback()

    async def clear_stream_history(self, stream_id: str) -> None:
        """
        Очистить историю изменений качества для потока.

        Args:
            stream_id: ID потока
        """
        if stream_id in self._quality_history:
            self._quality_history[stream_id].clear()
            log.debug(f"Cleared quality history for stream {stream_id}")

    async def get_quality_history(
        self,
        stream_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Получить историю изменений качества.

        Args:
            stream_id: ID потока
            limit: Максимальное количество записей

        Returns:
            Список событий изменений качества
        """
        history = self._quality_history.get(stream_id, [])
        return history[-limit:]


# Singleton instance
adaptive_streaming_service = AdaptiveStreamingService()


# Dependency для FastAPI

async def get_adaptive_streaming_service() -> AdaptiveStreamingService:
    """FastAPI dependency для получения сервиса адаптивного стрима."""
    return adaptive_streaming_service
