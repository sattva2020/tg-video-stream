"""
Bandwidth Monitor Service

Сервис для обнаружения доступной пропускной способности и сетевых условий.

Функционал:
- Периодическое измерение пропускной способности сети
- Определение сетевых условий (stable, fluctuating, degrading, poor)
- Сглаживание измерений для предотвращения скачков качества
- Интеграция с CircuitBreaker для предотвращения каскадных сбоев
- Хранение состояния в Redis
- Callbacks для событий изменения качества

Storage: Redis Hash (bandwidth:{stream_id}) для хранения метрик пропускной способности

Использование:
    monitor = BandwidthMonitor()
    await monitor.measure_bandwidth(stream_id)  # Измерить пропускную способность
    status = await monitor.get_bandwidth_status(stream_id)  # Получить статус
    await monitor.start_monitoring(stream_id)  # Запустить фоновый мониторинг
"""

import asyncio
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Dict, List
from enum import Enum

import redis.asyncio as redis
import httpx

from src.config import settings
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

log = logging.getLogger(__name__)


class BandwidthMonitorError(Exception):
    """Базовое исключение для ошибок BandwidthMonitor."""
    pass


class NetworkCondition(Enum):
    """Состояние сети."""
    STABLE = "stable"          # Стабильная сеть, минимальные колебания
    FLUCTUATING = "fluctuating"  # Колеблющаяся сеть
    DEGRADING = "degrading"    # Ухудшающаяся сеть
    POOR = "poor"              # Плохая сеть, низкая пропускная способность
    UNKNOWN = "unknown"        # Не удалось определить


@dataclass
class BandwidthMeasurement:
    """Результат измерения пропускной способности."""
    timestamp: datetime
    bandwidth_kbps: float      # Пропускная способность в Kbps
    latency_ms: float          # Задержка в миллисекундах
    packet_loss: float = 0.0   # Потеря пакетов в процентах
    jitter_ms: float = 0.0     # Вариация задержки (jitter)

    def to_dict(self) -> dict:
        """Конвертировать в dict."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'BandwidthMeasurement':
        """Создать из dict."""
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class BandwidthStatus:
    """Статус пропускной способности потока."""
    stream_id: str
    current_bandwidth_kbps: float
    smoothed_bandwidth_kbps: float    # Сглаженная пропускная способность
    network_condition: NetworkCondition
    last_measurement: datetime
    measurements_count: int = 0

    # Статистика
    min_bandwidth_kbps: Optional[float] = None
    max_bandwidth_kbps: Optional[float] = None
    avg_bandwidth_kbps: Optional[float] = None
    avg_latency_ms: Optional[float] = None

    # История измерений (последние N)
    measurement_history: List[BandwidthMeasurement] = field(default_factory=list)

    # Recommendation
    recommended_quality: Optional[str] = None

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime и enum
        if data['last_measurement']:
            data['last_measurement'] = data['last_measurement'].isoformat()
        data['network_condition'] = self.network_condition.value

        # Конвертируем историю измерений
        if data['measurement_history']:
            data['measurement_history'] = [
                m.to_dict() for m in self.measurement_history
            ]
        else:
            data['measurement_history'] = []

        # Удаляем None значения
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'BandwidthStatus':
        """Создать из dict из Redis."""
        if data.get('last_measurement'):
            data['last_measurement'] = datetime.fromisoformat(data['last_measurement'])

        # Конвертируем enum
        if 'network_condition' in data:
            data['network_condition'] = NetworkCondition(data['network_condition'])

        # Конвертируем историю измерений
        if 'measurement_history' in data and data['measurement_history']:
            data['measurement_history'] = [
                BandwidthMeasurement.from_dict(m) for m in data['measurement_history']
            ]
        else:
            data['measurement_history'] = []

        return cls(**data)


@dataclass
class BandwidthMonitorConfig:
    """Конфигурация мониторинга пропускной способности."""
    # Измерения
    measurement_interval_seconds: int = 30        # Интервал автоматических измерений
    measurement_timeout_seconds: int = 15         # Таймаут измерения
    history_size: int = 10                        # Размер истории измерений

    # Пороги сетевых условий (Kbps)
    poor_bandwidth_threshold_kbps: float = 500    # Ниже этого - poor condition
    stable_bandwidth_threshold_kbps: float = 2000  # Выше этого - stable condition

    # Пороги для определения колебаний (%)
    fluctuation_threshold_percent: float = 20.0   # Разница для detection fluctuating

    # Сглаживание
    smoothing_factor: float = 0.3                 # Экспоненциальное сглаживание (0-1)

    # Circuit Breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_success_threshold: int = 2

    # Test endpoints для измерения
    test_urls: List[str] = field(default_factory=lambda: [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://detectportal.firefox.com"
    ])
    test_download_size_bytes: int = 1024 * 100   # 100 KB для теста


class BandwidthMonitor:
    """
    Сервис мониторинга пропускной способности.

    Использует Redis для хранения состояния и Circuit Breaker для предотвращения сбоев.

    Attributes:
        config: Конфигурация мониторинга
        on_quality_change_callback: Callback при изменении рекомендуемого качества
                                     (stream_id, old_quality, new_quality, bandwidth_kbps)
    """

    # Redis key patterns
    BANDWIDTH_KEY_PREFIX = "bandwidth"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[BandwidthMonitorConfig] = None,
        on_quality_change_callback: Optional[Callable[[str, str, str, float], Awaitable[None]]] = None
    ):
        """
        Инициализация BandwidthMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга
            on_quality_change_callback: Callback при изменении качества
                                        (stream_id, old_quality, new_quality, bandwidth_kbps)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or BandwidthMonitorConfig()
        self.on_quality_change_callback = on_quality_change_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

        log.info(
            f"BandwidthMonitor initialized: interval={self.config.measurement_interval_seconds}s, "
            f"poor_threshold={self.config.poor_bandwidth_threshold_kbps}Kbps"
        )

    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis

    def _get_http_client(self) -> httpx.AsyncClient:
        """Получение HTTP клиента."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.config.measurement_timeout_seconds)
        return self._http_client

    def _get_circuit_breaker(self, stream_id: str) -> CircuitBreaker:
        """Получить или создать Circuit Breaker для потока."""
        if stream_id not in self._circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                success_threshold=self.config.circuit_breaker_success_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
            self._circuit_breakers[stream_id] = CircuitBreaker(
                name=f"bandwidth-{stream_id}",
                config=cb_config
            )
        return self._circuit_breakers[stream_id]

    @staticmethod
    def _get_bandwidth_key(stream_id: str) -> str:
        """Генерация Redis ключа для статуса пропускной способности."""
        return f"{BandwidthMonitor.BANDWIDTH_KEY_PREFIX}:{stream_id}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        self._circuit_breakers.clear()

    # ========== Bandwidth Measurement Operations ==========

    async def measure_bandwidth(self, stream_id: str) -> BandwidthStatus:
        """
        Измерить пропускную способность потока.

        Args:
            stream_id: ID потока

        Returns:
            BandwidthStatus с результатами измерения
        """
        r = await self._get_redis()
        key = self._get_bandwidth_key(stream_id)

        # Получить текущий статус
        current_status = await self.get_bandwidth_status(stream_id)

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = BandwidthStatus(
                stream_id=stream_id,
                current_bandwidth_kbps=0.0,
                smoothed_bandwidth_kbps=0.0,
                network_condition=NetworkCondition.UNKNOWN,
                last_measurement=datetime.now(timezone.utc),
                measurements_count=0,
                measurement_history=[]
            )

        # Выполнить измерение
        cb = self._get_circuit_breaker(stream_id)
        measurement: Optional[BandwidthMeasurement] = None
        old_quality = current_status.recommended_quality

        try:
            if not cb.allow_request():
                log.warning(f"Stream {stream_id}: Circuit breaker OPEN, using cached data")
                # Используем сглаженное значение как текущее
                measurement = BandwidthMeasurement(
                    timestamp=datetime.now(timezone.utc),
                    bandwidth_kbps=current_status.smoothed_bandwidth_kbps,
                    latency_ms=current_status.avg_latency_ms or 0.0
                )
            else:
                # Выполняем реальное измерение
                measurement = await self._perform_bandwidth_measurement(stream_id)
                cb.record_success()

        except Exception as exc:
            log.error(f"Error measuring bandwidth for stream {stream_id}: {exc}")
            cb.record_failure()

            # Используем последнее известное значение
            measurement = BandwidthMeasurement(
                timestamp=datetime.now(timezone.utc),
                bandwidth_kbps=current_status.smoothed_bandwidth_kbps,
                latency_ms=current_status.avg_latency_ms or 100.0  # Default latency
            )

        # Обновить статус
        current_status.last_measurement = measurement.timestamp
        current_status.measurements_count += 1

        # Обновить текущую пропускную способность
        current_status.current_bandwidth_kbps = measurement.bandwidth_kbps

        # Применить сглаживание (exponential moving average)
        if current_status.measurements_count == 1:
            # Первое измерение
            current_status.smoothed_bandwidth_kbps = measurement.bandwidth_kbps
        else:
            # EMA: smoothed = alpha * new + (1 - alpha) * old
            alpha = self.config.smoothing_factor
            current_status.smoothed_bandwidth_kbps = (
                alpha * measurement.bandwidth_kbps +
                (1 - alpha) * current_status.smoothed_bandwidth_kbps
            )

        # Обновить статистику
        self._update_statistics(current_status, measurement)

        # Добавить в историю
        current_status.measurement_history.append(measurement)
        if len(current_status.measurement_history) > self.config.history_size:
            current_status.measurement_history.pop(0)

        # Определить состояние сети
        current_status.network_condition = self._determine_network_condition(current_status)

        # Определить рекомендуемое качество
        current_status.recommended_quality = self._calculate_recommended_quality(
            current_status.smoothed_bandwidth_kbps
        )

        # Callback при изменении качества
        if (old_quality != current_status.recommended_quality and
            current_status.recommended_quality is not None and
            self.on_quality_change_callback):
            try:
                await self.on_quality_change_callback(
                    stream_id,
                    old_quality or "unknown",
                    current_status.recommended_quality,
                    current_status.smoothed_bandwidth_kbps
                )
                log.info(
                    f"Stream {stream_id}: Quality changed from {old_quality} to "
                    f"{current_status.recommended_quality} (bandwidth: {current_status.smoothed_bandwidth_kbps:.0f} Kbps)"
                )
            except Exception as e:
                log.error(f"Error in quality change callback: {e}")

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 3600)  # TTL: 1 час

        return current_status

    async def _perform_bandwidth_measurement(self, stream_id: str) -> BandwidthMeasurement:
        """
        Выполнить фактическое измерение пропускной способности.

        Использует HTTP download speed test для измерения.

        Returns:
            BandwidthMeasurement с результатами
        """
        http_client = self._get_http_client()

        # Пробуем несколько endpoints для надежности
        successful_measurements = []

        for url in self.config.test_urls:
            try:
                start_time = time.time()

                # Выполняем HEAD запрос для измерения latency
                response = await http_client.head(url)
                latency_ms = (time.time() - start_time) * 1000

                # Если доступно, выполняем небольшой GET запрос для измерения throughput
                if response.status_code == 200:
                    download_start = time.time()
                    download_response = await http_client.get(
                        url,
                        headers={"Range": "bytes=0-{}".format(self.config.test_download_size_bytes - 1)}
                    )
                    download_time = time.time() - download_start

                    if download_response.status_code == 200:
                        bytes_downloaded = len(download_response.content)
                        bits_per_second = (bytes_downloaded * 8) / download_time if download_time > 0 else 0
                        bandwidth_kbps = bits_per_second / 1000

                        successful_measurements.append({
                            'bandwidth_kbps': bandwidth_kbps,
                            'latency_ms': latency_ms
                        })

                        log.debug(
                            f"Stream {stream_id}: Measured {bandwidth_kbps:.0f} Kbps, "
                            f"{latency_ms:.0f} ms latency from {url}"
                        )
                        break  # Используем первое успешное измерение

            except Exception as e:
                log.debug(f"Failed to measure bandwidth from {url}: {e}")
                continue

        # Если не удалось измерить, возвращаем дефолтные значения
        if not successful_measurements:
            log.warning(f"Could not measure bandwidth for stream {stream_id}, using defaults")
            return BandwidthMeasurement(
                timestamp=datetime.now(timezone.utc),
                bandwidth_kbps=1000.0,  # Default 1 Mbps
                latency_ms=50.0
            )

        # Используем среднее значение если несколько измерений
        avg_bandwidth = sum(m['bandwidth_kbps'] for m in successful_measurements) / len(successful_measurements)
        avg_latency = sum(m['latency_ms'] for m in successful_measurements) / len(successful_measurements)

        return BandwidthMeasurement(
            timestamp=datetime.now(timezone.utc),
            bandwidth_kbps=avg_bandwidth,
            latency_ms=avg_latency
        )

    def _update_statistics(self, status: BandwidthStatus, measurement: BandwidthMeasurement) -> None:
        """Обновить статистику на основе нового измерения."""
        # Min/Max bandwidth
        if status.min_bandwidth_kbps is None:
            status.min_bandwidth_kbps = measurement.bandwidth_kbps
            status.max_bandwidth_kbps = measurement.bandwidth_kbps
        else:
            status.min_bandwidth_kbps = min(status.min_bandwidth_kbps, measurement.bandwidth_kbps)
            status.max_bandwidth_kbps = max(status.max_bandwidth_kbps, measurement.bandwidth_kbps)

        # Average bandwidth
        if status.measurements_count == 1:
            status.avg_bandwidth_kbps = measurement.bandwidth_kbps
            status.avg_latency_ms = measurement.latency_ms
        else:
            # Скользящее среднее
            n = status.measurements_count
            status.avg_bandwidth_kbps = (
                (status.avg_bandwidth_kbps * (n - 1) + measurement.bandwidth_kbps) / n
            )
            status.avg_latency_ms = (
                (status.avg_latency_ms * (n - 1) + measurement.latency_ms) / n
            )

    def _determine_network_condition(self, status: BandwidthStatus) -> NetworkCondition:
        """
        Определить состояние сети на основе измерений.

        Args:
            status: Текущий статус

        Returns:
            NetworkCondition
        """
        bandwidth = status.smoothed_bandwidth_kbps

        # Poor: очень низкая пропускная способность
        if bandwidth < self.config.poor_bandwidth_threshold_kbps:
            return NetworkCondition.POOR

        # Stable: высокая пропускная способность
        if bandwidth >= self.config.stable_bandwidth_threshold_kbps:
            return NetworkCondition.STABLE

        # Проверяем колебания
        if len(status.measurement_history) >= 3:
            recent = [m.bandwidth_kbps for m in status.measurement_history[-3:]]
            avg = sum(recent) / len(recent)
            max_deviation = max(abs(m - avg) for m in recent)
            deviation_percent = (max_deviation / avg * 100) if avg > 0 else 0

            if deviation_percent > self.config.fluctuation_threshold_percent:
                return NetworkCondition.FLUCTUATING

            # Проверяем тренд (ухудшается или нет)
            if len(status.measurement_history) >= 5:
                recent_5 = [m.bandwidth_kbps for m in status.measurement_history[-5:]]
                first_half_avg = sum(recent_5[:2]) / 2
                second_half_avg = sum(recent_5[3:]) / 2

                if second_half_avg < first_half_avg * 0.8:  # Ухудшение на 20%+
                    return NetworkCondition.DEGRADING

        # По умолчанию
        return NetworkCondition.STABLE

    def _calculate_recommended_quality(self, bandwidth_kbps: float) -> str:
        """
        Рассчитать рекомендуемое качество на основе пропускной способности.

        Args:
            bandwidth_kbps: Пропускная способность в Kbps

        Returns:
            Recommended quality level (low, medium, high, ultra)
        """
        # Пороги качества (Kbps)
        # low (360p): 500 Kbps
        # medium (480p): 1500 Kbps
        # high (720p): 3000 Kbps
        # ultra (1080p): 6000 Kbps

        if bandwidth_kbps >= 6000:
            return "ultra"
        elif bandwidth_kbps >= 3000:
            return "high"
        elif bandwidth_kbps >= 1500:
            return "medium"
        else:
            return "low"

    async def get_bandwidth_status(self, stream_id: str) -> Optional[BandwidthStatus]:
        """
        Получить статус пропускной способности потока.

        Args:
            stream_id: ID потока

        Returns:
            BandwidthStatus или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_bandwidth_key(stream_id)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return BandwidthStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing bandwidth data for stream {stream_id}: {e}")
            return None

    async def get_current_bandwidth(self, stream_id: str) -> Optional[float]:
        """
        Получить текущую пропускную способность (упрощенная проверка).

        Args:
            stream_id: ID потока

        Returns:
            Пропускная способность в Kbps или None
        """
        status = await self.get_bandwidth_status(stream_id)
        return status.smoothed_bandwidth_kbps if status else None

    # ========== Background Monitoring ==========

    async def start_monitoring(self, stream_id: str) -> None:
        """
        Запустить фоновый мониторинг пропускной способности.

        Args:
            stream_id: ID потока
        """
        # Остановить существующий монитор
        await self.stop_monitoring(stream_id)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(stream_id))
        self._monitor_tasks[stream_id] = task

        log.info(f"Started bandwidth monitoring for stream {stream_id}")

    async def stop_monitoring(self, stream_id: str) -> None:
        """
        Остановить мониторинг пропускной способности.

        Args:
            stream_id: ID потока
        """
        task = self._monitor_tasks.pop(stream_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info(f"Stopped bandwidth monitoring for stream {stream_id}")

    async def _monitor_loop(self, stream_id: str) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                await self.measure_bandwidth(stream_id)
                await asyncio.sleep(self.config.measurement_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for stream {stream_id}: {e}")

    # ========== Utility Methods ==========

    async def reset_bandwidth_status(self, stream_id: str) -> bool:
        """
        Сбросить статус пропускной способности.

        Args:
            stream_id: ID потока

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        key = self._get_bandwidth_key(stream_id)

        # Удалить из Redis
        deleted = await r.delete(key)

        # Сбросить Circuit Breaker
        if stream_id in self._circuit_breakers:
            self._circuit_breakers[stream_id].reset()

        if deleted:
            log.info(f"Reset bandwidth status for stream {stream_id}")
        else:
            log.warning(f"No bandwidth status to reset for stream {stream_id}")

        return deleted > 0

    def get_circuit_breaker_info(self, stream_id: str) -> Optional[dict]:
        """
        Получить информацию о Circuit Breaker для потока.

        Args:
            stream_id: ID потока

        Returns:
            Словарь с информацией о Circuit Breaker или None
        """
        cb = self._circuit_breakers.get(stream_id)
        if cb:
            return cb.get_state_info()
        return None


# Singleton instance
_bandwidth_monitor: Optional[BandwidthMonitor] = None


def get_bandwidth_monitor() -> BandwidthMonitor:
    """Получить singleton экземпляр BandwidthMonitor."""
    global _bandwidth_monitor
    if _bandwidth_monitor is None:
        _bandwidth_monitor = BandwidthMonitor()
    return _bandwidth_monitor


async def shutdown_bandwidth_monitor() -> None:
    """Закрыть BandwidthMonitor при завершении приложения."""
    global _bandwidth_monitor
    if _bandwidth_monitor is not None:
        await _bandwidth_monitor.close()
        _bandwidth_monitor = None
