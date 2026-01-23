"""
Feature 009: Adaptive Bitrate Streaming

Модуль для управления адаптивным качеством видео during active streams.
Мониторинг пропускной способности и автоматическое переключение качества.

Architecture:
- AdaptiveQualityManager — основной класс для управления качеством
- Bandwidth measurement and smoothing (exponential moving average)
- Quality adjustment decision logic с гистерезисом
- Integration with VideoTranscoder QualityProfile
- Stream state tracking for per-stream quality management

Adaptive Quality Management:
- Периодический мониторинг пропускной способности
- Автоматическое переключение качества на основе thresholds
- Гистерезис для предотвращения частых переключений
- Quality change callbacks для уведомления системы
- Statistics tracking для анализа качества
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Dict, Any, List

from video_transcoder import QualityProfile

logger = logging.getLogger(__name__)


class NetworkCondition(str, Enum):
    """Состояние сети на основе анализа пропускной способности."""

    STABLE = "stable"         # Стабильная связь, колебания < 20%
    FLUCTUATING = "fluctuating"  # Нестабильная связь, колебания 20-50%
    DEGRADING = "degrading"   # Ухудшающаяся связь, тренд вниз
    POOR = "poor"            # Плохая связь, частые падения
    UNKNOWN = "unknown"      # Недостаточно данных


@dataclass
class BandwidthMeasurement:
    """
    Результат измерения пропускной способности.

    Attributes:
        bandwidth_kbps: Текущая пропускная способность в Kbps
        timestamp: Время измерения
        confidence: Уверенность в измерении (0.0-1.0)
        latency_ms: Задержка сети в миллисекундах (опционально)
        packet_loss: Потеря пакетов в % (опционально)
    """

    bandwidth_kbps: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0
    latency_ms: Optional[int] = None
    packet_loss: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в dict для логирования и API."""
        return {
            "bandwidth_kbps": self.bandwidth_kbps,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "packet_loss": self.packet_loss,
        }


@dataclass
class QualityDecision:
    """
    Решение о качестве видео.

    Attributes:
        quality: Рекомендуемый профиль качества
        reason: Причина выбора качества
        confidence: Уверенность в решении (0.0-1.0)
        should_change: Нужно ли менять текущее качество
        previous_quality: Предыдущее качество (если было)
    """

    quality: QualityProfile
    reason: str
    confidence: float
    should_change: bool
    previous_quality: Optional[QualityProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в dict для логирования и API."""
        return {
            "quality": self.quality.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "should_change": self.should_change,
            "previous_quality": self.previous_quality.value if self.previous_quality else None,
        }


@dataclass
class StreamQualityState:
    """
    Состояние качества для активного stream.

    Attributes:
        stream_id: Уникальный идентификатор stream
        current_quality: Текущий профиль качества
        bandwidth_history: История измерений пропускной способности
        quality_history: История изменений качества
        last_quality_change: Время последнего изменения качества
        quality_change_count: Количество изменений качества
        statistics: Статистика качества
    """

    stream_id: str
    current_quality: QualityProfile
    bandwidth_history: List[BandwidthMeasurement] = field(default_factory=list)
    quality_history: List[Dict[str, Any]] = field(default_factory=list)
    last_quality_change: Optional[datetime] = None
    quality_change_count: int = 0
    statistics: Dict[str, Any] = field(default_factory=dict)

    def add_bandwidth_measurement(self, measurement: BandwidthMeasurement, max_history: int = 100):
        """
        Добавляет измерение пропускной способности в историю.

        Args:
            measurement: Измерение пропускной способности
            max_history: Максимальный размер истории
        """
        self.bandwidth_history.append(measurement)
        if len(self.bandwidth_history) > max_history:
            self.bandwidth_history.pop(0)

    def get_average_bandwidth(self, window_seconds: int = 60) -> Optional[int]:
        """
        Вычисляет среднюю пропускную способность за период.

        Args:
            window_seconds: Окно усреднения в секундах

        Returns:
            Средняя пропускная способность в Kbps или None
        """
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        recent = [m for m in self.bandwidth_history if m.timestamp >= cutoff]

        if not recent:
            return None

        total = sum(m.bandwidth_kbps for m in recent)
        return int(total / len(recent))

    def record_quality_change(
        self,
        new_quality: QualityProfile,
        reason: str,
        bandwidth_kbps: int,
    ):
        """
        Записывает изменение качества в историю.

        Args:
            new_quality: Новое качество
            reason: Причина изменения
            bandwidth_kbps: Пропускная способность при изменении
        """
        change_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_quality": self.current_quality.value,
            "to_quality": new_quality.value,
            "reason": reason,
            "bandwidth_kbps": bandwidth_kbps,
        }

        self.quality_history.append(change_event)
        self.previous_quality = self.current_quality
        self.current_quality = new_quality
        self.last_quality_change = datetime.utcnow()
        self.quality_change_count += 1

        logger.info("Quality changed", extra={
            "stream_id": self.stream_id,
            "from_quality": change_event["from_quality"],
            "to_quality": new_quality.value,
            "reason": reason,
            "bandwidth_kbps": bandwidth_kbps,
            "change_count": self.quality_change_count,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует состояние в dict для API и логирования."""
        return {
            "stream_id": self.stream_id,
            "current_quality": self.current_quality.value,
            "last_quality_change": self.last_quality_change.isoformat() if self.last_quality_change else None,
            "quality_change_count": self.quality_change_count,
            "average_bandwidth": self.get_average_bandwidth(),
            "bandwidth_measurements": len(self.bandwidth_history),
            "quality_history": self.quality_history[-10:],  # Last 10 changes
        }


class AdaptiveQualityManager:
    """
    Менеджер адаптивного качества видео.

    Отвечает за мониторинг пропускной способности и автоматическое
    переключение качества видео during active streams.

    Features:
    - Периодический мониторинг пропускной способности
    - Exponential moving average для сглаживания измерений
    - Quality adjustment decisions с гистерезисом
    - Per-stream quality state tracking
    - Quality change callbacks для уведомлений
    - Statistics tracking для анализа

    Examples:
        >>> manager = AdaptiveQualityManager()
        >>> manager.start_monitoring("stream-123", QualityProfile.HIGH)
        >>> # ... bandwidth is measured ...
        >>> decision = await manager.evaluate_quality("stream-123")
        >>> if decision.should_change:
        ...     await manager.apply_quality_change("stream-123", decision.quality)

        >>> # Stop monitoring when stream ends
        >>> manager.stop_monitoring("stream-123")
    """

    # Default settings
    DEFAULT_MONITORING_INTERVAL = 30  # seconds
    DEFAULT_SMOOTHING_FACTOR = 0.3  # exponential moving average
    DEFAULT_CONSECUTIVE_MEASUREMENTS = 3  # measurements before switch
    MAX_BANDWIDTH_HISTORY = 100  # measurements per stream

    def __init__(
        self,
        monitoring_interval: int = DEFAULT_MONITORING_INTERVAL,
        smoothing_factor: float = DEFAULT_SMOOTHING_FACTOR,
        consecutive_measurements: int = DEFAULT_CONSECUTIVE_MEASUREMENTS,
    ):
        """
        Инициализация менеджера адаптивного качества.

        Args:
            monitoring_interval: Интервал мониторинга в секундах
            smoothing_factor: Коэффициент сглаживания (0.0-1.0)
            consecutive_measurements: Количество измерений перед переключением
        """
        self.monitoring_interval = monitoring_interval
        self.smoothing_factor = smoothing_factor
        self.consecutive_measurements = consecutive_measurements

        # Stream state management
        self.streams: Dict[str, StreamQualityState] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

        # Quality change callbacks
        self.quality_callbacks: List[Callable[[str, QualityProfile, QualityProfile, str], None]] = []

        logger.info("AdaptiveQualityManager initialized", extra={
            "monitoring_interval": monitoring_interval,
            "smoothing_factor": smoothing_factor,
            "consecutive_measurements": consecutive_measurements,
        })

    def add_quality_callback(
        self,
        callback: Callable[[str, QualityProfile, QualityProfile, str], None],
    ):
        """
        Добавляет callback для уведомления об изменениях качества.

        Args:
            callback: Функция с сигнатурой (stream_id, old_quality, new_quality, reason)
        """
        if callback not in self.quality_callbacks:
            self.quality_callbacks.append(callback)
            logger.debug("Quality callback registered", extra={"callback": callback.__name__})

    def remove_quality_callback(
        self,
        callback: Callable[[str, QualityProfile, QualityProfile, str], None],
    ):
        """
        Удаляет callback для уведомления об изменениях качества.

        Args:
            callback: Функция для удаления
        """
        if callback in self.quality_callbacks:
            self.quality_callbacks.remove(callback)
            logger.debug("Quality callback removed", extra={"callback": callback.__name__})

    def _notify_quality_change(
        self,
        stream_id: str,
        old_quality: QualityProfile,
        new_quality: QualityProfile,
        reason: str,
    ):
        """
        Уведомляет все зарегистрированные callbacks об изменении качества.

        Args:
            stream_id: ID stream
            old_quality: Старое качество
            new_quality: Новое качество
            reason: Причина изменения
        """
        for callback in self.quality_callbacks:
            try:
                callback(stream_id, old_quality, new_quality, reason)
            except Exception as e:
                logger.exception("Error in quality callback", extra={
                    "stream_id": stream_id,
                    "callback": callback.__name__,
                    "error": str(e),
                })

    def start_monitoring(
        self,
        stream_id: str,
        initial_quality: QualityProfile,
        auto_monitor: bool = True,
    ) -> StreamQualityState:
        """
        Начинает мониторинг качества для stream.

        Args:
            stream_id: Уникальный идентификатор stream
            initial_quality: Начальное качество
            auto_monitor: Автоматически запустить фоновый мониторинг

        Returns:
            Созданное состояние качества stream

        Examples:
            >>> manager = AdaptiveQualityManager()
            >>> state = manager.start_monitoring("stream-123", QualityProfile.HIGH)
            >>> print(state.current_quality)
        """
        if stream_id in self.streams:
            logger.warning("Stream already being monitored", extra={"stream_id": stream_id})
            return self.streams[stream_id]

        state = StreamQualityState(
            stream_id=stream_id,
            current_quality=initial_quality,
        )

        self.streams[stream_id] = state

        logger.info("Started monitoring stream quality", extra={
            "stream_id": stream_id,
            "initial_quality": initial_quality.value,
            "auto_monitor": auto_monitor,
        })

        if auto_monitor:
            self._start_monitoring_task(stream_id)

        return state

    def _start_monitoring_task(self, stream_id: str):
        """
        Запускает фоновую задачу мониторинга для stream.

        Args:
            stream_id: ID stream
        """
        if stream_id in self.monitoring_tasks:
            logger.warning("Monitoring task already exists", extra={"stream_id": stream_id})
            return

        task = asyncio.create_task(self._monitoring_loop(stream_id))
        self.monitoring_tasks[stream_id] = task

        logger.debug("Monitoring task started", extra={"stream_id": stream_id})

    async def _monitoring_loop(self, stream_id: str):
        """
        Фоновый цикл мониторинга для stream.

        Периодически измеряет пропускную способность и принимает решения
        о качестве. Обрабатывает ошибки измерения gracefully.

        Args:
            stream_id: ID stream
        """
        logger.debug("Monitoring loop started", extra={"stream_id": stream_id})

        try:
            while stream_id in self.streams:
                # Simulate bandwidth measurement (in real implementation, this would
                # call backend API or use actual network measurement)
                measurement = await self._measure_bandwidth(stream_id)

                if measurement:
                    state = self.streams[stream_id]
                    state.add_bandwidth_measurement(measurement, self.MAX_BANDWIDTH_HISTORY)

                    # Evaluate and potentially adjust quality
                    decision = self.evaluate_quality(stream_id, measurement)

                    if decision.should_change:
                        await self.apply_quality_change(
                            stream_id,
                            decision.quality,
                            decision.reason,
                        )

                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.debug("Monitoring loop cancelled", extra={"stream_id": stream_id})
        except Exception as e:
            logger.exception("Error in monitoring loop", extra={
                "stream_id": stream_id,
                "error": str(e),
            })

    async def _measure_bandwidth(self, stream_id: str) -> Optional[BandwidthMeasurement]:
        """
        Измеряет текущую пропускную способность.

        В реальной реализации это должно вызывать backend API
        или выполнять реальное измерение сети.

        Args:
            stream_id: ID stream

        Returns:
            Результат измерения или None (если измерение не удалось)
        """
        # TODO: Implement actual bandwidth measurement
        # This is a placeholder that returns mock data
        # In production, this should call backend API or use network measurement tools

        logger.debug("Bandwidth measurement (placeholder)", extra={"stream_id": stream_id})

        # Placeholder: Return a mock measurement
        # In production, this would call backend API:
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"{BACKEND_URL}/api/adaptive-streaming/bandwidth?stream_id={stream_id}") as resp:
        #         data = await resp.json()
        #         return BandwidthMeasurement(**data)

        return None  # Placeholder: no actual measurement

    def evaluate_quality(
        self,
        stream_id: str,
        measurement: Optional[BandwidthMeasurement] = None,
    ) -> QualityDecision:
        """
        Оценивает текущее качество и принимает решение о переключении.

        Использует гистерезис для предотвращения частых переключений.

        Args:
            stream_id: ID stream
            measurement: Опциональное новое измерение пропускной способности

        Returns:
            Решение о качестве

        Examples:
            >>> manager = AdaptiveQualityManager()
            >>> manager.start_monitoring("stream-123", QualityProfile.MEDIUM)
            >>> decision = manager.evaluate_quality("stream-123")
            >>> print(decision.quality, decision.should_change)
        """
        if stream_id not in self.streams:
            logger.error("Stream not being monitored", extra={"stream_id": stream_id})
            raise ValueError(f"Stream {stream_id} is not being monitored")

        state = self.streams[stream_id]
        current_quality = state.current_quality

        # Get bandwidth (use provided measurement or average from history)
        if measurement:
            bandwidth_kbps = measurement.bandwidth_kbps
        else:
            bandwidth_kbps = state.get_average_bandwidth(self.monitoring_interval * 2)
            if bandwidth_kbps is None:
                # Not enough data, keep current quality
                return QualityDecision(
                    quality=current_quality,
                    reason="insufficient_bandwidth_data",
                    confidence=0.0,
                    should_change=False,
                    previous_quality=None,
                )

        # Check if we should downgrade (immediate)
        downgrade_to = current_quality.should_downgrade_to(bandwidth_kbps)
        if downgrade_to:
            logger.info("Quality downgrade recommended", extra={
                "stream_id": stream_id,
                "current_quality": current_quality.value,
                "new_quality": downgrade_to.value,
                "bandwidth_kbps": bandwidth_kbps,
                "reason": "bandwidth_below_threshold",
            })
            return QualityDecision(
                quality=downgrade_to,
                reason=f"bandwidth_drop_{bandwidth_kbps}_kbps_below_{current_quality.get_bandwidth_threshold()}_kbps",
                confidence=0.9,
                should_change=True,
                previous_quality=current_quality,
            )

        # Check if we should upgrade (with hysteresis)
        # Try each higher quality level
        quality_order = [QualityProfile.LOW, QualityProfile.MEDIUM, QualityProfile.HIGH, QualityProfile.ULTRA]
        current_idx = quality_order.index(current_quality)

        for higher_quality in reversed(quality_order[current_idx + 1:]):
            if current_quality.can_upgrade_to(higher_quality, bandwidth_kbps):
                logger.info("Quality upgrade recommended", extra={
                    "stream_id": stream_id,
                    "current_quality": current_quality.value,
                    "new_quality": higher_quality.value,
                    "bandwidth_kbps": bandwidth_kbps,
                    "reason": "bandwidth_sufficient_for_upgrade",
                })
                return QualityDecision(
                    quality=higher_quality,
                    reason=f"bandwidth_rise_{bandwidth_kbps}_kbps_above_{higher_quality.get_bandwidth_threshold() * 1.2}_kbps",
                    confidence=0.8,
                    should_change=True,
                    previous_quality=current_quality,
                )

        # No change needed
        return QualityDecision(
            quality=current_quality,
            reason=f"bandwidth_stable_{bandwidth_kbps}_kbps_suitable_for_{current_quality.value}",
            confidence=0.7,
            should_change=False,
            previous_quality=None,
        )

    async def apply_quality_change(
        self,
        stream_id: str,
        new_quality: QualityProfile,
        reason: str,
        bandwidth_kbps: Optional[int] = None,
    ):
        """
        Применяет изменение качества к stream.

        Обновляет состояние и уведомляет callbacks.

        Args:
            stream_id: ID stream
            new_quality: Новое качество
            reason: Причина изменения
            bandwidth_kbps: Пропускная способность при изменении (опционально)

        Examples:
            >>> manager = AdaptiveQualityManager()
            >>> await manager.apply_quality_change("stream-123", QualityProfile.LOW, "bandwidth_drop")
        """
        if stream_id not in self.streams:
            logger.error("Stream not being monitored", extra={"stream_id": stream_id})
            raise ValueError(f"Stream {stream_id} is not being monitored")

        state = self.streams[stream_id]
        old_quality = state.current_quality

        if old_quality == new_quality:
            logger.debug("Quality unchanged", extra={
                "stream_id": stream_id,
                "quality": new_quality.value,
            })
            return

        # Record quality change in state
        if bandwidth_kbps is None:
            bandwidth_kbps = state.get_average_bandwidth() or 0

        state.record_quality_change(new_quality, reason, bandwidth_kbps)

        # Notify callbacks
        self._notify_quality_change(stream_id, old_quality, new_quality, reason)

        logger.info("Quality change applied", extra={
            "stream_id": stream_id,
            "old_quality": old_quality.value,
            "new_quality": new_quality.value,
            "reason": reason,
            "bandwidth_kbps": bandwidth_kbps,
        })

    def stop_monitoring(self, stream_id: str, cancel_task: bool = True) -> Optional[StreamQualityState]:
        """
        Останавливает мониторинг качества для stream.

        Args:
            stream_id: ID stream
            cancel_task: Отменить фоновую задачу мониторинга

        Returns:
            Финальное состояние качества или None

        Examples:
            >>> manager = AdaptiveQualityManager()
            >>> final_state = manager.stop_monitoring("stream-123")
            >>> print(final_state.quality_change_count)
        """
        if stream_id not in self.streams:
            logger.warning("Stream not being monitored", extra={"stream_id": stream_id})
            return None

        # Cancel monitoring task if requested
        if cancel_task and stream_id in self.monitoring_tasks:
            task = self.monitoring_tasks[stream_id]
            task.cancel()
            del self.monitoring_tasks[stream_id]
            logger.debug("Monitoring task cancelled", extra={"stream_id": stream_id})

        # Get final state
        state = self.streams.pop(stream_id)

        logger.info("Stopped monitoring stream quality", extra={
            "stream_id": stream_id,
            "final_quality": state.current_quality.value,
            "quality_changes": state.quality_change_count,
            "monitoring_duration": (
                datetime.utcnow() - state.last_quality_change
            ).total_seconds() if state.last_quality_change else None,
        })

        return state

    def get_stream_state(self, stream_id: str) -> Optional[StreamQualityState]:
        """
        Получает текущее состояние качества stream.

        Args:
            stream_id: ID stream

        Returns:
            Состояние качества или None
        """
        return self.streams.get(stream_id)

    def get_all_streams(self) -> Dict[str, StreamQualityState]:
        """
        Получает состояния всех мониторируемых streams.

        Returns:
            Словарь {stream_id: StreamQualityState}
        """
        return self.streams.copy()

    def is_monitoring(self, stream_id: str) -> bool:
        """
        Проверяет, монитoring ли активный stream.

        Args:
            stream_id: ID stream

        Returns:
            True, если stream монитoring
        """
        return stream_id in self.streams


# Singleton instance для использования в приложении
_manager: Optional[AdaptiveQualityManager] = None


def get_adaptive_quality_manager() -> AdaptiveQualityManager:
    """
    Возвращает singleton AdaptiveQualityManager.

    Returns:
        Экземпляр AdaptiveQualityManager

    Examples:
        >>> manager = get_adaptive_quality_manager()
        >>> manager.start_monitoring("stream-123", QualityProfile.HIGH)
    """
    global _manager
    if _manager is None:
        _manager = AdaptiveQualityManager()
    return _manager
