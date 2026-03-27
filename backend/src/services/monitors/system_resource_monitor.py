"""
System Resource Monitor Service

Сервис для мониторинга системных ресурсов (CPU, memory, disk)
и предупреждения о высоком использовании.

Функционал:
- Мониторинг использования CPU, памяти, диска
- Проверка порогов warning и critical
- Отслеживание consecutive triggers для алертов
- Хранение истории метрик в Redis
- Callbacks для событий предупреждений и восстановления

Storage: Redis Hash (system_resource:{host}) для хранения метрик,
         Redis List (system_resource:{host}:history) для истории

Использование:
    monitor = SystemResourceMonitor()
    await monitor.check_resources()  # Проверить все ресурсы
    status = await monitor.get_resource_status()  # Получить статус
    await monitor.start_monitoring()  # Запустить фоновый мониторинг
"""

import asyncio
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any, Dict, List

import redis.asyncio as redis
from prometheus_api_client import PrometheusConnect

from src.config import settings

log = logging.getLogger(__name__)


class SystemResourceMonitorError(Exception):
    """Базовое исключение для ошибок SystemResourceMonitor."""
    pass


@dataclass
class SystemResourceStatus:
    """Статус системных ресурсов."""
    host: str
    cpu_usage: float  # Процент использования CPU
    memory_usage: float  # Процент использования памяти
    disk_usage: float  # Процент использования диска
    last_check: datetime
    cpu_warning: bool
    cpu_critical: bool
    memory_warning: bool
    memory_critical: bool
    disk_warning: bool
    disk_critical: bool
    consecutive_cpu_triggers: int = 0
    consecutive_memory_triggers: int = 0
    consecutive_disk_triggers: int = 0
    total_checks: int = 0
    cpu_average: float = 0.0
    memory_average: float = 0.0
    disk_average: float = 0.0
    peak_cpu: float = 0.0
    peak_memory: float = 0.0
    peak_disk: float = 0.0

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data.get('last_check'):
            data['last_check'] = data['last_check'].isoformat()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'SystemResourceStatus':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        return cls(**data)


@dataclass
class SystemResourceConfig:
    """Конфигурация мониторинга системных ресурсов."""
    check_interval_seconds: int = 30          # Интервал автоматических проверок
    cpu_warning_threshold: float = 70.0        # Порог warning для CPU (%)
    cpu_critical_threshold: float = 90.0       # Порог critical для CPU (%)
    memory_warning_threshold: float = 75.0     # Порог warning для памяти (%)
    memory_critical_threshold: float = 90.0    # Порог critical для памяти (%)
    disk_warning_threshold: float = 80.0       # Порог warning для диска (%)
    disk_critical_threshold: float = 95.0      # Порог critical для диска (%)
    trigger_count: int = 3                     # Количество проверок для алерта
    alert_cooldown_seconds: int = 300          # Минимальное время между алертами
    history_size: int = 100                    # Размер истории для расчета среднего
    prometheus_url: Optional[str] = None       # URL Prometheus (по умолчанию из настроек)


class SystemResourceMonitor:
    """
    Сервис мониторинга системных ресурсов.

    Использует Prometheus для получения метрик и Redis для хранения состояния.

    Attributes:
        config: Конфигурация мониторинга
        on_cpu_warning_callback: Callback при warning для CPU (host, usage, threshold)
        on_cpu_critical_callback: Callback при critical для CPU (host, usage, threshold)
        on_memory_warning_callback: Callback при warning для памяти (host, usage, threshold)
        on_memory_critical_callback: Callback при critical для памяти (host, usage, threshold)
        on_disk_warning_callback: Callback при warning для диска (host, usage, threshold)
        on_disk_critical_callback: Callback при critical для диска (host, usage, threshold)
        on_recovery_callback: Callback при восстановлении (host, resource_type)
    """

    # Redis key patterns
    RESOURCE_KEY_PREFIX = "system_resource"
    HISTORY_KEY_SUFFIX = "history"
    ALERT_LAST_SENT_PREFIX = "system_resource_alert_last"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[SystemResourceConfig] = None,
        on_cpu_warning_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_cpu_critical_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_memory_warning_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_memory_critical_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_disk_warning_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_disk_critical_callback: Optional[Callable[[str, float, float], Awaitable[None]]] = None,
        on_recovery_callback: Optional[Callable[[str, str], Awaitable[None]]] = None
    ):
        """
        Инициализация SystemResourceMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга
            on_cpu_warning_callback: Callback при warning для CPU (host, usage, threshold)
            on_cpu_critical_callback: Callback при critical для CPU (host, usage, threshold)
            on_memory_warning_callback: Callback при warning для памяти (host, usage, threshold)
            on_memory_critical_callback: Callback при critical для памяти (host, usage, threshold)
            on_disk_warning_callback: Callback при warning для диска (host, usage, threshold)
            on_disk_critical_callback: Callback при critical для диска (host, usage, threshold)
            on_recovery_callback: Callback при восстановлении (host, resource_type)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or SystemResourceConfig()
        self.on_cpu_warning_callback = on_cpu_warning_callback
        self.on_cpu_critical_callback = on_cpu_critical_callback
        self.on_memory_warning_callback = on_memory_warning_callback
        self.on_memory_critical_callback = on_memory_critical_callback
        self.on_disk_warning_callback = on_disk_warning_callback
        self.on_disk_critical_callback = on_disk_critical_callback
        self.on_recovery_callback = on_recovery_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._prometheus: Optional[PrometheusConnect] = None

        # Get hostname
        self.host = os.getenv('HOSTNAME', 'localhost')

        log.info(
            f"SystemResourceMonitor initialized for host '{self.host}': "
            f"check_interval={self.config.check_interval_seconds}s, "
            f"cpu_warning={self.config.cpu_warning_threshold}%, "
            f"memory_warning={self.config.memory_warning_threshold}%, "
            f"disk_warning={self.config.disk_warning_threshold}%"
        )

    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis

    def _get_prometheus(self) -> PrometheusConnect:
        """Получение Prometheus клиента."""
        if self._prometheus is None:
            prometheus_url = self.config.prometheus_url or os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
            self._prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        return self._prometheus

    @staticmethod
    def _get_resource_key(host: str) -> str:
        """Генерация Redis ключа для статуса ресурсов."""
        return f"{SystemResourceMonitor.RESOURCE_KEY_PREFIX}:{host}"

    @staticmethod
    def _get_history_key(host: str) -> str:
        """Генерация Redis ключа для истории метрик."""
        return f"{SystemResourceMonitor.RESOURCE_KEY_PREFIX}:{host}:{SystemResourceMonitor.HISTORY_KEY_SUFFIX}"

    @staticmethod
    def _get_alert_last_sent_key(host: str, alert_type: str) -> str:
        """Генерация Redis ключа для времени последнего алерта."""
        return f"{SystemResourceMonitor.ALERT_LAST_SENT_PREFIX}:{host}:{alert_type}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить монитор
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ========== Resource Monitoring ==========

    async def _get_current_metrics(self) -> Dict[str, float]:
        """
        Получить текущие метрики из Prometheus.

        Returns:
            Словарь с метриками cpu_usage, memory_usage, disk_usage
        """
        try:
            prom = self._get_prometheus()
            metrics = {}

            # CPU usage query
            cpu_query = '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
            try:
                result = prom.custom_query(query=cpu_query)
                if result and len(result) > 0:
                    metrics['cpu_usage'] = float(result[0]['value'][1])
                else:
                    metrics['cpu_usage'] = 0.0
            except Exception as e:
                log.warning(f"Ошибка получения CPU метрики: {e}")
                metrics['cpu_usage'] = 0.0

            # Memory usage query
            memory_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
            try:
                result = prom.custom_query(query=memory_query)
                if result and len(result) > 0:
                    metrics['memory_usage'] = float(result[0]['value'][1])
                else:
                    metrics['memory_usage'] = 0.0
            except Exception as e:
                log.warning(f"Ошибка получения memory метрики: {e}")
                metrics['memory_usage'] = 0.0

            # Disk usage query
            disk_query = '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100'
            try:
                result = prom.custom_query(query=disk_query)
                if result and len(result) > 0:
                    metrics['disk_usage'] = float(result[0]['value'][1])
                else:
                    metrics['disk_usage'] = 0.0
            except Exception as e:
                log.warning(f"Ошибка получения disk метрики: {e}")
                metrics['disk_usage'] = 0.0

            return metrics

        except Exception as e:
            log.error(f"Ошибка получения метрик из Prometheus: {e}")
            return {'cpu_usage': 0.0, 'memory_usage': 0.0, 'disk_usage': 0.0}

    async def check_resources(self) -> SystemResourceStatus:
        """
        Проверить системные ресурсы и обновить статус.

        Returns:
            SystemResourceStatus с результатами проверки
        """
        r = await self._get_redis()
        key = self._get_resource_key(self.host)
        history_key = self._get_history_key(self.host)

        # Получить текущие метрики
        metrics = await self._get_current_metrics()
        cpu_usage = metrics.get('cpu_usage', 0.0)
        memory_usage = metrics.get('memory_usage', 0.0)
        disk_usage = metrics.get('disk_usage', 0.0)

        # Получить текущий статус
        current_status = await self.get_resource_status()

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = SystemResourceStatus(
                host=self.host,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                last_check=datetime.now(timezone.utc),
                cpu_warning=False,
                cpu_critical=False,
                memory_warning=False,
                memory_critical=False,
                disk_warning=False,
                disk_critical=False,
                consecutive_cpu_triggers=0,
                consecutive_memory_triggers=0,
                consecutive_disk_triggers=0,
                total_checks=0,
                cpu_average=cpu_usage,
                memory_average=memory_usage,
                disk_average=disk_usage,
                peak_cpu=cpu_usage,
                peak_memory=memory_usage,
                peak_disk=disk_usage
            )

        # Добавить в историю
        history_entry = f"{cpu_usage}:{memory_usage}:{disk_usage}:{int(datetime.now(timezone.utc).timestamp())}"
        await r.lpush(history_key, history_entry)
        await r.ltrim(history_key, 0, self.config.history_size - 1)
        await r.expire(history_key, 86400)  # TTL: 24 часа

        # Получить историю для расчетов
        history_data = await r.lrange(history_key, 0, self.config.history_size - 1)
        cpu_values = []
        memory_values = []
        disk_values = []

        for item in history_data:
            try:
                cpu_str, memory_str, disk_str, _ = item.split(':')
                cpu_values.append(float(cpu_str))
                memory_values.append(float(memory_str))
                disk_values.append(float(disk_str))
            except (ValueError, IndexError):
                continue

        # Расчет средних и пиковых значений
        cpu_average = sum(cpu_values) / len(cpu_values) if cpu_values else cpu_usage
        memory_average = sum(memory_values) / len(memory_values) if memory_values else memory_usage
        disk_average = sum(disk_values) / len(disk_values) if disk_values else disk_usage

        peak_cpu = max(cpu_values) if cpu_values else cpu_usage
        peak_memory = max(memory_values) if memory_values else memory_usage
        peak_disk = max(disk_values) if disk_values else disk_usage

        # Сохранить предыдущие состояния
        was_cpu_warning = current_status.cpu_warning
        was_cpu_critical = current_status.cpu_critical
        was_memory_warning = current_status.memory_warning
        was_memory_critical = current_status.memory_critical
        was_disk_warning = current_status.disk_warning
        was_disk_critical = current_status.disk_critical

        # Обновить статус
        now = datetime.now(timezone.utc)
        current_status.cpu_usage = cpu_usage
        current_status.memory_usage = memory_usage
        current_status.disk_usage = disk_usage
        current_status.last_check = now
        current_status.total_checks += 1
        current_status.cpu_average = cpu_average
        current_status.memory_average = memory_average
        current_status.disk_average = disk_average
        current_status.peak_cpu = peak_cpu
        current_status.peak_memory = peak_memory
        current_status.peak_disk = peak_disk

        # Проверка порогов CPU
        cpu_critical = cpu_usage >= self.config.cpu_critical_threshold
        cpu_warning = cpu_usage >= self.config.cpu_warning_threshold and not cpu_critical

        current_status.cpu_critical = cpu_critical
        current_status.cpu_warning = cpu_warning

        if cpu_critical or cpu_warning:
            current_status.consecutive_cpu_triggers += 1
        else:
            current_status.consecutive_cpu_triggers = 0

        # Проверка порогов memory
        memory_critical = memory_usage >= self.config.memory_critical_threshold
        memory_warning = memory_usage >= self.config.memory_warning_threshold and not memory_critical

        current_status.memory_critical = memory_critical
        current_status.memory_warning = memory_warning

        if memory_critical or memory_warning:
            current_status.consecutive_memory_triggers += 1
        else:
            current_status.consecutive_memory_triggers = 0

        # Проверка порогов disk
        disk_critical = disk_usage >= self.config.disk_critical_threshold
        disk_warning = disk_usage >= self.config.disk_warning_threshold and not disk_critical

        current_status.disk_critical = disk_critical
        current_status.disk_warning = disk_warning

        if disk_critical or disk_warning:
            current_status.consecutive_disk_triggers += 1
        else:
            current_status.consecutive_disk_triggers = 0

        # Callbacks для CPU
        if cpu_critical and not was_cpu_critical:
            if current_status.consecutive_cpu_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "cpu_critical"):
                    log.error(
                        f"Host {self.host}: CPU critical threshold reached: "
                        f"{cpu_usage:.1f}% >= {self.config.cpu_critical_threshold}%"
                    )
                    if self.on_cpu_critical_callback:
                        try:
                            await self.on_cpu_critical_callback(
                                self.host, cpu_usage, self.config.cpu_critical_threshold
                            )
                            await self._mark_alert_sent(self.host, "cpu_critical")
                        except Exception as e:
                            log.error(f"Error in cpu_critical callback: {e}")

        elif cpu_warning and not was_cpu_warning:
            if current_status.consecutive_cpu_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "cpu_warning"):
                    log.warning(
                        f"Host {self.host}: CPU warning threshold reached: "
                        f"{cpu_usage:.1f}% >= {self.config.cpu_warning_threshold}%"
                    )
                    if self.on_cpu_warning_callback:
                        try:
                            await self.on_cpu_warning_callback(
                                self.host, cpu_usage, self.config.cpu_warning_threshold
                            )
                            await self._mark_alert_sent(self.host, "cpu_warning")
                        except Exception as e:
                            log.error(f"Error in cpu_warning callback: {e}")

        # Callbacks для memory
        if memory_critical and not was_memory_critical:
            if current_status.consecutive_memory_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "memory_critical"):
                    log.error(
                        f"Host {self.host}: Memory critical threshold reached: "
                        f"{memory_usage:.1f}% >= {self.config.memory_critical_threshold}%"
                    )
                    if self.on_memory_critical_callback:
                        try:
                            await self.on_memory_critical_callback(
                                self.host, memory_usage, self.config.memory_critical_threshold
                            )
                            await self._mark_alert_sent(self.host, "memory_critical")
                        except Exception as e:
                            log.error(f"Error in memory_critical callback: {e}")

        elif memory_warning and not was_memory_warning:
            if current_status.consecutive_memory_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "memory_warning"):
                    log.warning(
                        f"Host {self.host}: Memory warning threshold reached: "
                        f"{memory_usage:.1f}% >= {self.config.memory_warning_threshold}%"
                    )
                    if self.on_memory_warning_callback:
                        try:
                            await self.on_memory_warning_callback(
                                self.host, memory_usage, self.config.memory_warning_threshold
                            )
                            await self._mark_alert_sent(self.host, "memory_warning")
                        except Exception as e:
                            log.error(f"Error in memory_warning callback: {e}")

        # Callbacks для disk
        if disk_critical and not was_disk_critical:
            if current_status.consecutive_disk_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "disk_critical"):
                    log.error(
                        f"Host {self.host}: Disk critical threshold reached: "
                        f"{disk_usage:.1f}% >= {self.config.disk_critical_threshold}%"
                    )
                    if self.on_disk_critical_callback:
                        try:
                            await self.on_disk_critical_callback(
                                self.host, disk_usage, self.config.disk_critical_threshold
                            )
                            await self._mark_alert_sent(self.host, "disk_critical")
                        except Exception as e:
                            log.error(f"Error in disk_critical callback: {e}")

        elif disk_warning and not was_disk_warning:
            if current_status.consecutive_disk_triggers >= self.config.trigger_count:
                if await self._can_send_alert(self.host, "disk_warning"):
                    log.warning(
                        f"Host {self.host}: Disk warning threshold reached: "
                        f"{disk_usage:.1f}% >= {self.config.disk_warning_threshold}%"
                    )
                    if self.on_disk_warning_callback:
                        try:
                            await self.on_disk_warning_callback(
                                self.host, disk_usage, self.config.disk_warning_threshold
                            )
                            await self._mark_alert_sent(self.host, "disk_warning")
                        except Exception as e:
                            log.error(f"Error in disk_warning callback: {e}")

        # Callback при восстановлении CPU
        if (was_cpu_critical or was_cpu_warning) and not cpu_critical and not cpu_warning:
            if current_status.consecutive_cpu_triggers == 0:
                log.info(f"Host {self.host}: CPU usage recovered to {cpu_usage:.1f}%")
                if self.on_recovery_callback:
                    try:
                        await self.on_recovery_callback(self.host, "cpu")
                    except Exception as e:
                        log.error(f"Error in recovery callback: {e}")

        # Callback при восстановлении memory
        if (was_memory_critical or was_memory_warning) and not memory_critical and not memory_warning:
            if current_status.consecutive_memory_triggers == 0:
                log.info(f"Host {self.host}: Memory usage recovered to {memory_usage:.1f}%")
                if self.on_recovery_callback:
                    try:
                        await self.on_recovery_callback(self.host, "memory")
                    except Exception as e:
                        log.error(f"Error in recovery callback: {e}")

        # Callback при восстановлении disk
        if (was_disk_critical or was_disk_warning) and not disk_critical and not disk_warning:
            if current_status.consecutive_disk_triggers == 0:
                log.info(f"Host {self.host}: Disk usage recovered to {disk_usage:.1f}%")
                if self.on_recovery_callback:
                    try:
                        await self.on_recovery_callback(self.host, "disk")
                    except Exception as e:
                        log.error(f"Error in recovery callback: {e}")

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_status

    async def get_resource_status(self, host: Optional[str] = None) -> Optional[SystemResourceStatus]:
        """
        Получить статус системных ресурсов для хоста.

        Args:
            host: Имя хоста (по умолчанию текущий)

        Returns:
            SystemResourceStatus или None если нет данных
        """
        r = await self._get_redis()
        host = host or self.host
        key = self._get_resource_key(host)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return SystemResourceStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing resource status data for host {host}: {e}")
            return None

    async def get_resource_history(
        self,
        host: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получить историю метрик ресурсов для хоста.

        Args:
            host: Имя хоста (по умолчанию текущий)
            limit: Максимальное количество записей

        Returns:
            Список словарей с данными о ресурсах
        """
        r = await self._get_redis()
        host = host or self.host
        history_key = self._get_history_key(host)

        history_data = await r.lrange(history_key, 0, limit - 1)
        history = []

        for item in history_data:
            try:
                cpu_str, memory_str, disk_str, timestamp_str = item.split(':')
                history.append({
                    'cpu_usage': float(cpu_str),
                    'memory_usage': float(memory_str),
                    'disk_usage': float(disk_str),
                    'timestamp': datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
                })
            except (ValueError, IndexError):
                continue

        return history

    # ========== Background Monitoring ==========

    async def start_monitoring(self) -> None:
        """Запустить фоновый мониторинг системных ресурсов."""
        # Остановить существующий монитор
        await self.stop_monitoring()

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop())
        self._monitor_task = task

        log.info(f"Started background system resource monitoring for host {self.host}")

    async def stop_monitoring(self) -> None:
        """Остановить мониторинг системных ресурсов."""
        task = self._monitor_task
        if task:
            self._monitor_task = None
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info(f"Stopped system resource monitoring for host {self.host}")

    async def _monitor_loop(self) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                try:
                    await self.check_resources()
                except Exception as e:
                    log.error(f"Error checking system resources for host {self.host}: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for host {self.host}: {e}")

    # ========== Alert Cooldown ==========

    async def _can_send_alert(self, host: str, alert_type: str) -> bool:
        """
        Проверить можно ли отправить алерт (cooldown).

        Args:
            host: Имя хоста
            alert_type: Тип алерта (cpu_warning, cpu_critical, memory_warning, etc.)

        Returns:
            True если можно отправить алерт
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(host, alert_type)

        last_sent_str = await r.get(key)
        if not last_sent_str:
            return True

        try:
            last_sent = datetime.fromtimestamp(int(last_sent_str), tz=timezone.utc)
            cooldown_expiry = last_sent + timedelta(seconds=self.config.alert_cooldown_seconds)
            return datetime.now(timezone.utc) >= cooldown_expiry
        except (ValueError, OSError):
            return True

    async def _mark_alert_sent(self, host: str, alert_type: str) -> None:
        """
        Отметить что алерт был отправлен.

        Args:
            host: Имя хоста
            alert_type: Тип алерта
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(host, alert_type)

        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        await r.set(key, now_timestamp, ex=self.config.alert_cooldown_seconds)

    # ========== Statistics ==========

    async def get_all_critical_hosts(self) -> List[SystemResourceStatus]:
        """
        Получить все хосты с критическим использованием ресурсов.

        Returns:
            Список статусов хостов с critical thresholds
        """
        r = await self._get_redis()
        pattern = f"{self.RESOURCE_KEY_PREFIX}:*"
        keys = []

        async for key in r.scan_iter(match=pattern):
            # Исключаем ключи истории
            if not key.endswith(f":{self.HISTORY_KEY_SUFFIX}"):
                keys.append(key)

        critical = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                try:
                    status = SystemResourceStatus.from_redis_dict(data)
                    if status.cpu_critical or status.memory_critical or status.disk_critical:
                        critical.append(status)
                except Exception as e:
                    log.error(f"Error parsing resource data from {key}: {e}")

        return critical

    async def reset_resource_status(self, host: Optional[str] = None) -> bool:
        """
        Сбросить статус системных ресурсов для хоста.

        Args:
            host: Имя хоста (по умолчанию текущий)

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        host = host or self.host
        resource_key = self._get_resource_key(host)
        history_key = self._get_history_key(host)

        # Удалить из Redis
        deleted_resource = await r.delete(resource_key)
        deleted_history = await r.delete(history_key)

        if deleted_resource or deleted_history:
            log.info(f"Reset system resource status for host {host}")
            return True
        else:
            log.warning(f"No system resource status to reset for host {host}")
            return False


# Singleton instance
_system_resource_monitor: Optional[SystemResourceMonitor] = None


def get_system_resource_monitor() -> SystemResourceMonitor:
    """Получить singleton экземпляр SystemResourceMonitor."""
    global _system_resource_monitor
    if _system_resource_monitor is None:
        _system_resource_monitor = SystemResourceMonitor()
    return _system_resource_monitor


async def shutdown_system_resource_monitor() -> None:
    """Закрыть SystemResourceMonitor при завершении приложения."""
    global _system_resource_monitor
    if _system_resource_monitor is not None:
        await _system_resource_monitor.close()
        _system_resource_monitor = None
