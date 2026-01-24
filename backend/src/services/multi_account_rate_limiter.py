"""
Multi-Account Rate Limiter Service

Сервис для распределения API запросов между несколькими аккаунтами Telegram.
Управляет пулом аккаунтов, отслеживает их состояние и балансирует нагрузку.

Основные функции:
1. Управление пулом аккаунтов с отслеживанием здоровья
2. Выбор аккаунта для запроса (least-used, round-robin)
3. Интеграция с TelegramRateLimiter для отслеживания лимитов
4. Автоматическое отключение проблемных аккаунтов
"""

import asyncio
import enum
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
from src.core.config import settings

logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    """Статус аккаунта"""
    ACTIVE = "active"           # Активен и работает
    RATE_LIMITED = "rate_limited"  # В лимите, временно недоступен
    DISABLED = "disabled"       # Отключён вручную
    FAILED = "failed"           # Ошибка аутентификации
    BANNED = "banned"           # Заблокирован Telegram


class SelectionStrategy(Enum):
    """Стратегия выбора аккаунта"""
    LEAST_USED = "least_used"   # Наименее нагруженный
    ROUND_ROBIN = "round_robin" # По очереди
    WEIGHTED = "weighted"       # С весами (по производительности)


class AccountHealthState(str, enum.Enum):
    """Account health states.

    **State Machine**:
    - HEALTHY -> DEGRADED: When degradation threshold is reached
    - DEGRADED -> FAILED: When failure threshold is reached
    - DEGRADED -> HEALTHY: When recovery threshold is reached
    - FAILED/DEGRADED -> DISABLED: Auto-disabled on too many failures
    """
    HEALTHY = "healthy"       # Account is working well
    DEGRADED = "degraded"     # Account has some failures but still usable
    FAILED = "failed"         # Account has failed too many times
    DISABLED = "disabled"     # Account is automatically disabled


@dataclass
class AccountHealthConfig:
    """Configuration for account health behavior.

    **Purpose**: Define thresholds for health state transitions
    **Layer**: Configuration (dataclass)
    """
    degradation_threshold: int = 3     # Failures before degraded state
    failure_threshold: int = 5         # Failures before failed state
    recovery_threshold: int = 2        # Successes to recover from degraded
    failure_window_seconds: int = 300  # Time window to consider failures (5 min)
    health_check_interval: int = 60    # Seconds between automatic health checks


class AccountHealth:
    """Health tracker for Telegram accounts.

    **Purpose**: Track account health and automatically disable failed accounts
    **Pattern**: Similar to CircuitBreaker but for account health
    **States**: HEALTHY (normal), DEGRADED (some failures), FAILED (many failures), DISABLED (auto-disabled)

    **State Machine**:
    - HEALTHY -> DEGRADED: When degradation threshold is reached
    - DEGRADED -> FAILED: When failure threshold is reached
    - DEGRADED -> HEALTHY: When recovery threshold is reached
    - FAILED -> DISABLED: When maximum failures exceeded

    **Usage**:
        health = AccountHealth("account-123")
        if health.is_available():
            try:
                # Attempt operation
                health.record_success()
            except Exception:
                health.record_failure()

                # Check if account should be disabled
                if health.should_disable():
                    await disable_account(account_id)
    """

    def __init__(
        self,
        account_id: str,
        config: Optional[AccountHealthConfig] = None
    ):
        """Initialize account health tracker.

        Args:
            account_id: Unique identifier for the account
            config: Optional custom configuration
        """
        self.account_id = account_id
        self.config = config or AccountHealthConfig()

        # State tracking
        self._state = AccountHealthState.HEALTHY
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._total_failures = 0
        self._total_successes = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._failure_history: List[float] = []  # Timestamps of recent failures

        logger.info(
            f"AccountHealth '{account_id}' initialized with state={self._state}, "
            f"degradation_threshold={self.config.degradation_threshold}, "
            f"failure_threshold={self.config.failure_threshold}"
        )

    @property
    def state(self) -> AccountHealthState:
        """Get current health state."""
        # Auto-recovery from DEGRADED if enough consecutive successes
        if self._state == AccountHealthState.DEGRADED:
            if self._consecutive_successes >= self.config.recovery_threshold:
                self._transition_to(AccountHealthState.HEALTHY)
                logger.info(
                    f"AccountHealth '{self.account_id}' transitioned "
                    f"DEGRADED -> HEALTHY (recovery threshold reached)"
                )

        return self._state

    @property
    def consecutive_failures(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures

    @property
    def consecutive_successes(self) -> int:
        """Get current consecutive success count."""
        return self._consecutive_successes

    @property
    def total_failures(self) -> int:
        """Get total failure count."""
        return self._total_failures

    @property
    def total_successes(self) -> int:
        """Get total success count."""
        return self._total_successes

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self._total_successes + self._total_failures
        if total == 0:
            return 1.0
        return self._total_successes / total

    def is_available(self) -> bool:
        """Check if account is available for use.

        Returns:
            True if account is HEALTHY or DEGRADED, False if FAILED or DISABLED
        """
        current_state = self.state
        return current_state in [AccountHealthState.HEALTHY, AccountHealthState.DEGRADED]

    def should_disable(self) -> bool:
        """Check if account should be automatically disabled.

        Returns:
            True if account is in FAILED state or exceeded failure threshold
        """
        current_state = self.state
        return current_state in [AccountHealthState.FAILED, AccountHealthState.DISABLED]

    def record_success(self):
        """Record a successful operation.

        May trigger state transition:
        - DEGRADED -> HEALTHY: When recovery threshold is reached
        """
        current_state = self.state

        self._total_successes += 1
        self._consecutive_successes += 1
        self._consecutive_failures = 0  # Reset consecutive failures
        self._last_success_time = time.time()

        if current_state == AccountHealthState.DEGRADED:
            logger.debug(
                f"AccountHealth '{self.account_id}' recorded success "
                f"({self._consecutive_successes}/{self.config.recovery_threshold} in DEGRADED)"
            )
        elif current_state == AccountHealthState.HEALTHY:
            logger.debug(f"AccountHealth '{self.account_id}' recorded success in HEALTHY state")

    def record_failure(self):
        """Record a failed operation.

        May trigger state transitions:
        - HEALTHY -> DEGRADED: When degradation threshold is reached
        - DEGRADED -> FAILED: When failure threshold is reached
        """
        current_state = self.state

        self._total_failures += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0  # Reset consecutive successes
        self._last_failure_time = time.time()

        # Track failure in sliding window
        self._failure_history.append(self._last_failure_time)
        self._cleanup_old_failures()

        if current_state == AccountHealthState.HEALTHY:
            logger.debug(
                f"AccountHealth '{self.account_id}' recorded failure "
                f"({self._consecutive_failures}/{self.config.degradation_threshold})"
            )

            if self._consecutive_failures >= self.config.degradation_threshold:
                self._transition_to(AccountHealthState.DEGRADED)
                logger.warning(
                    f"AccountHealth '{self.account_id}' transitioned "
                    f"HEALTHY -> DEGRADED (degradation threshold reached: "
                    f"{self._consecutive_failures} failures)"
                )

        elif current_state == AccountHealthState.DEGRADED:
            logger.debug(
                f"AccountHealth '{self.account_id}' recorded failure in DEGRADED "
                f"({self._consecutive_failures}/{self.config.failure_threshold})"
            )

            if self._consecutive_failures >= self.config.failure_threshold:
                self._transition_to(AccountHealthState.FAILED)
                logger.error(
                    f"AccountHealth '{self.account_id}' transitioned "
                    f"DEGRADED -> FAILED (failure threshold reached: "
                    f"{self._consecutive_failures} failures)"
                )

    def _cleanup_old_failures(self):
        """Remove failures outside the time window."""
        cutoff_time = time.time() - self.config.failure_window_seconds
        self._failure_history = [
            t for t in self._failure_history if t > cutoff_time
        ]

    def reset(self):
        """Manually reset health tracker to HEALTHY state.

        Useful for manual intervention or after known fixes.
        """
        self._transition_to(AccountHealthState.HEALTHY)
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._failure_history = []
        logger.info(f"AccountHealth '{self.account_id}' manually reset to HEALTHY")

    def disable(self):
        """Manually disable account."""
        self._transition_to(AccountHealthState.DISABLED)
        logger.warning(f"AccountHealth '{self.account_id}' manually DISABLED")

    def _transition_to(self, new_state: AccountHealthState):
        """Internal method to transition to a new state.

        Args:
            new_state: Target state
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        logger.debug(
            f"AccountHealth '{self.account_id}' state transition: "
            f"{old_state} -> {new_state}"
        )

    def __repr__(self) -> str:
        return (
            f"<AccountHealth(account_id={self.account_id}, state={self.state}, "
            f"consecutive_failures={self._consecutive_failures}, "
            f"success_rate={self.success_rate:.2f})>"
        )

    def get_health_info(self) -> Dict[str, Any]:
        """Get detailed health information for monitoring.

        Returns:
            Dictionary with current account health state
        """
        self._cleanup_old_failures()

        return {
            "account_id": self.account_id,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "success_rate": round(self.success_rate, 3),
            "is_available": self.is_available(),
            "should_disable": self.should_disable(),
            "recent_failures_in_window": len(self._failure_history),
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "last_state_change": self._last_state_change,
            "degradation_threshold": self.config.degradation_threshold,
            "failure_threshold": self.config.failure_threshold,
            "recovery_threshold": self.config.recovery_threshold,
        }


@dataclass
class AccountInfo:
    """Информация об аккаунте"""
    account_id: str
    phone: str
    status: AccountStatus = AccountStatus.ACTIVE
    request_count: int = 0
    last_used: Optional[datetime] = None
    rate_limit_until: Optional[datetime] = None
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    success_rate: float = 1.0  # Процент успешных запросов (0.0 - 1.0)
    avg_response_time: float = 0.0  # Среднее время ответа в ms

    @property
    def is_available(self) -> bool:
        """Проверка, доступен ли аккаунт для использования"""
        if self.status != AccountStatus.ACTIVE:
            return False

        # Проверяем, не в лимите ли
        if self.rate_limit_until and datetime.now() < self.rate_limit_until:
            return False

        return True

    @property
    def rate_limit_remaining_seconds(self) -> int:
        """Оставшееся время в лимите"""
        if not self.rate_limit_until:
            return 0
        remaining = (self.rate_limit_until - datetime.now()).total_seconds()
        return max(0, int(remaining))

    @property
    def score(self) -> float:
        """
        Комбинированный скор для взвешенного выбора.
        Учитывает нагрузку, надёжность и скорость.
        """
        # Меньше запросов = лучше
        load_score = 1.0 / (self.request_count + 1)

        # Выше success_rate = лучше
        reliability_score = self.success_rate

        # Меньше response_time = лучше
        speed_score = 1.0 / (self.avg_response_time + 1)

        # Взвешенная комбинация
        return (load_score * 0.4 +
                reliability_score * 0.4 +
                speed_score * 0.2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "phone": self.phone,
            "status": self.status.value,
            "request_count": self.request_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "rate_limit_until": self.rate_limit_until.isoformat() if self.rate_limit_until else None,
            "rate_limit_remaining_seconds": self.rate_limit_remaining_seconds,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "is_available": self.is_available,
            "success_rate": round(self.success_rate, 3),
            "avg_response_time": round(self.avg_response_time, 2),
            "score": round(self.score, 3),
        }


class MultiAccountRateLimiter:
    """Сервис управления пулом аккаунтов с балансировкой нагрузки"""

    # Ключи для Redis
    REDIS_PREFIX = "multi_account"
    ACCOUNT_POOL_KEY = f"{REDIS_PREFIX}:pool"
    ROUND_ROBIN_COUNTER = f"{REDIS_PREFIX}:round_robin"

    # Пороги для автоматического отключения
    MAX_FAILURES = 5
    FAILURE_WINDOW_SECONDS = 300  # 5 минут

    def __init__(self, selection_strategy: SelectionStrategy = SelectionStrategy.LEAST_USED):
        """
        Инициализация сервиса.

        Args:
            selection_strategy: Стратегия выбора аккаунта
        """
        self.redis_url = settings.REDIS_URL
        self.selection_strategy = selection_strategy
        self._local_cache: Dict[str, AccountInfo] = {}
        self._cache_ttl = timedelta(seconds=5)
        self._last_cache_update: Optional[datetime] = None

    async def _get_redis(self) -> redis.Redis:
        """Получить подключение к Redis"""
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def _refresh_cache(self) -> None:
        """Обновить локальный кэш из Redis"""
        now = datetime.now()

        # Обновляем не чаще чем раз в 5 секунд
        if (self._last_cache_update and
            now - self._last_cache_update < self._cache_ttl):
            return

        r = await self._get_redis()
        try:
            accounts = await r.hgetall(self.ACCOUNT_POOL_KEY)

            for account_id, data_json in accounts.items():
                import json
                try:
                    data = json.loads(data_json)

                    # Конвертируем строки datetime обратно в объекты
                    if data.get("last_used"):
                        data["last_used"] = datetime.fromisoformat(data["last_used"])
                    if data.get("rate_limit_until"):
                        data["rate_limit_until"] = datetime.fromisoformat(data["rate_limit_until"])
                    if data.get("last_failure"):
                        data["last_failure"] = datetime.fromisoformat(data["last_failure"])
                    if data.get("created_at"):
                        data["created_at"] = datetime.fromisoformat(data["created_at"])

                    account_info = AccountInfo(**data)
                    self._local_cache[account_id] = account_info

                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"[MultiAccount] Failed to parse account {account_id}: {e}")

            self._last_cache_update = now

        finally:
            await r.close()

    async def _save_account(self, account_info: AccountInfo) -> None:
        """Сохранить информацию об аккаунте в Redis"""
        r = await self._get_redis()
        try:
            import json
            data = account_info.to_dict()
            # Конвертируем datetime в ISO format для JSON
            if data["last_used"]:
                data["last_used"] = account_info.last_used.isoformat()
            if data["rate_limit_until"]:
                data["rate_limit_until"] = account_info.rate_limit_until.isoformat()
            if data["last_failure"]:
                data["last_failure"] = account_info.last_failure.isoformat()

            await r.hset(self.ACCOUNT_POOL_KEY, account_info.account_id, json.dumps(data))

            # Обновляем локальный кэш
            self._local_cache[account_info.account_id] = account_info
            self._last_cache_update = datetime.now()

        finally:
            await r.close()

    async def add_account(self, account_id: str, phone: str) -> AccountInfo:
        """
        Добавить аккаунт в пул.

        Args:
            account_id: Уникальный идентификатор аккаунта
            phone: Номер телефона

        Returns:
            AccountInfo с информацией о созданном аккаунте
        """
        account_info = AccountInfo(
            account_id=account_id,
            phone=phone,
            status=AccountStatus.ACTIVE
        )

        await self._save_account(account_info)
        logger.info(f"[MultiAccount] Added account {account_id} ({phone}) to pool")

        return account_info

    async def remove_account(self, account_id: str) -> bool:
        """
        Удалить аккаунт из пула.

        Args:
            account_id: Идентификатор аккаунта

        Returns:
            True если аккаунт был удалён
        """
        r = await self._get_redis()
        try:
            result = await r.hdel(self.ACCOUNT_POOL_KEY, account_id)

            if account_id in self._local_cache:
                del self._local_cache[account_id]

            if result > 0:
                logger.info(f"[MultiAccount] Removed account {account_id} from pool")
                return True

            return False

        finally:
            await r.close()

    async def get_account(self, account_id: str) -> Optional[AccountInfo]:
        """
        Получить информацию об аккаунте.

        Args:
            account_id: Идентификатор аккаунта

        Returns:
            AccountInfo или None если аккаунт не найден
        """
        await self._refresh_cache()
        return self._local_cache.get(account_id)

    async def get_all_accounts(self) -> List[AccountInfo]:
        """
        Получить список всех аккаунтов.

        Returns:
            Список AccountInfo
        """
        await self._refresh_cache()
        return list(self._local_cache.values())

    async def get_available_accounts(self) -> List[AccountInfo]:
        """
        Получить список доступных для использования аккаунтов.

        Returns:
            Список доступных AccountInfo
        """
        await self._refresh_cache()
        return [acc for acc in self._local_cache.values() if acc.is_available]

    async def select_account(self, fallback_enabled: bool = True) -> Optional[AccountInfo]:
        """
        Выбрать аккаунт для выполнения запроса.

        Использует настроенную стратегию выбора (least-used, round-robin, etc.)
        С поддержкой fallback на альтернативные стратегии.

        Args:
            fallback_enabled: Включить ли fallback на другие стратегии

        Returns:
            AccountInfo или None если нет доступных аккаунтов
        """
        available = await self.get_available_accounts()

        if not available:
            logger.warning("[MultiAccount] No available accounts")
            return None

        # Пробуем основную стратегию
        selected_account = await self._select_by_strategy(
            self.selection_strategy,
            available
        )

        # Если основная стратегия не сработала и fallback включён
        if selected_account is None and fallback_enabled:
            logger.info(f"[MultiAccount] Primary strategy {self.selection_strategy.value} failed, trying fallback")
            selected_account = await self._try_fallback_strategies(available)

        if selected_account:
            logger.info(f"[MultiAccount] Selected account {selected_account.account_id} "
                       f"(strategy: {self.selection_strategy.value}, "
                       f"load: {selected_account.request_count}, "
                       f"success_rate: {selected_account.success_rate:.2f})")
        else:
            logger.error("[MultiAccount] Failed to select account with all strategies")

        return selected_account

    async def _select_by_strategy(
        self,
        strategy: SelectionStrategy,
        available: List[AccountInfo]
    ) -> Optional[AccountInfo]:
        """
        Выбрать аккаунт по конкретной стратегии.

        Args:
            strategy: Стратегия выбора
            available: Список доступных аккаунтов

        Returns:
            Выбранный аккаунт или None
        """
        if not available:
            return None

        try:
            if strategy == SelectionStrategy.LEAST_USED:
                return await self._select_least_used(available)

            elif strategy == SelectionStrategy.ROUND_ROBIN:
                return await self._select_round_robin(available)

            elif strategy == SelectionStrategy.WEIGHTED:
                return await self._select_weighted(available)

        except Exception as e:
            logger.error(f"[MultiAccount] Error in strategy {strategy.value}: {e}")

        return None

    async def _select_least_used(self, available: List[AccountInfo]) -> Optional[AccountInfo]:
        """
        Стратегия: наименее нагруженный аккаунт.

        Сортирует по request_count, при равных значениях учитывает last_used.
        """
        # Сортируем: сначала по request_count, затем по времени последнего использования
        sorted_accounts = sorted(
            available,
            key=lambda a: (a.request_count, a.last_used or datetime.min)
        )

        return sorted_accounts[0]

    async def _select_round_robin(self, available: List[AccountInfo]) -> Optional[AccountInfo]:
        """
        Стратегия: круглый robin.

        Выбирает аккаунты по очереди, используя Redis-счётчик.
        """
        r = await self._get_redis()
        try:
            # Инкрементируем счётчик и получаем индекс
            index = await r.incr(self.ROUND_ROBIN_COUNTER) - 1
            # Зацикливаем на количестве доступных аккаунтов
            index = index % len(available)
            return available[index]
        except Exception as e:
            logger.error(f"[MultiAccount] Round-robin error: {e}")
            # Fallback: возвращаем первый доступный
            return available[0]
        finally:
            await r.close()

    async def _select_weighted(self, available: List[AccountInfo]) -> Optional[AccountInfo]:
        """
        Стратегия: взвешенный выбор.

        Учитывает нагрузку, надёжность (success_rate) и скорость (avg_response_time).
        """
        # Используем предвычисленный score из AccountInfo
        sorted_accounts = sorted(
            available,
            key=lambda a: a.score,
            reverse=True  # Больший score = лучше
        )

        return sorted_accounts[0]

    async def _try_fallback_strategies(
        self,
        available: List[AccountInfo]
    ) -> Optional[AccountInfo]:
        """
        Попробовать альтернативные стратегии в порядке приоритета.

        Fallback порядок:
        1. LEAST_USED (самый надёжный)
        2. WEIGHTED (учитывает множество факторов)
        3. ROUND_ROBIN (простая балансировка)

        Args:
            available: Список доступных аккаунтов

        Returns:
            Выбранный аккаунт или None
        """
        fallback_strategies = [
            SelectionStrategy.LEAST_USED,
            SelectionStrategy.WEIGHTED,
            SelectionStrategy.ROUND_ROBIN,
        ]

        # Исключаем основную стратегию из fallback
        fallback_strategies = [
            s for s in fallback_strategies
            if s != self.selection_strategy
        ]

        for strategy in fallback_strategies:
            logger.debug(f"[MultiAccount] Trying fallback strategy: {strategy.value}")

            account = await self._select_by_strategy(strategy, available)
            if account:
                logger.info(f"[MultiAccount] Fallback to {strategy.value} succeeded")
                return account

        return None

    async def mark_account_used(
        self,
        account_id: str,
        success: bool = True,
        response_time_ms: Optional[float] = None
    ) -> None:
        """
        Отметить аккаунт как использованный.

        Args:
            account_id: Идентификатор аккаунта
            success: Был ли запрос успешным
            response_time_ms: Время ответа в миллисекундах
        """
        account = await self.get_account(account_id)
        if not account:
            logger.warning(f"[MultiAccount] Account {account_id} not found")
            return

        account.request_count += 1
        account.last_used = datetime.now()

        # Обновляем success_rate (экспоненциальное скользящее среднее)
        alpha = 0.1  # Коэффициент сглаживания
        new_value = 1.0 if success else 0.0
        account.success_rate = (alpha * new_value +
                               (1 - alpha) * account.success_rate)

        # Обновляем avg_response_time (экспоненциальное скользящее среднее)
        if response_time_ms is not None:
            account.avg_response_time = (alpha * response_time_ms +
                                        (1 - alpha) * account.avg_response_time)

        await self._save_account(account)
        logger.debug(f"[MultiAccount] Marked account {account_id} as used "
                    f"(total: {account.request_count}, "
                    f"success_rate: {account.success_rate:.2f}, "
                    f"avg_time: {account.avg_response_time:.1f}ms)")

    async def mark_rate_limited(self, account_id: str, wait_seconds: int) -> None:
        """
        Отметить аккаунт как находящийся в лимите.

        Args:
            account_id: Идентификатор аккаунта
            wait_seconds: Время ожидания в секундах
        """
        account = await self.get_account(account_id)
        if not account:
            logger.warning(f"[MultiAccount] Account {account_id} not found")
            return

        account.status = AccountStatus.RATE_LIMITED
        account.rate_limit_until = datetime.now() + timedelta(seconds=wait_seconds)

        await self._save_account(account)
        logger.warning(f"[MultiAccount] Account {account_id} rate limited for {wait_seconds}s")

    async def mark_failure(self, account_id: str, error: str = "") -> None:
        """
        Отметить ошибку аккаунта.

        При достижении порога ошибок аккаунт автоматически отключается.

        Args:
            account_id: Идентификатор аккаунта
            error: Описание ошибки
        """
        account = await self.get_account(account_id)
        if not account:
            logger.warning(f"[MultiAccount] Account {account_id} not found")
            return

        now = datetime.now()
        account.failure_count += 1
        account.last_failure = now

        # Проверяем порог отключения
        window_start = now - timedelta(seconds=self.FAILURE_WINDOW_SECONDS)

        # Если ошибок слишком много в окне, отключаем
        if (account.failure_count >= self.MAX_FAILURES and
            account.last_failure and
            account.last_failure > window_start):

            account.status = AccountStatus.FAILED
            logger.error(f"[MultiAccount] Account {account_id} disabled due to "
                        f"{account.failure_count} failures: {error}")
        else:
            logger.warning(f"[MultiAccount] Account {account_id} failure #{account.failure_count}: {error}")

        await self._save_account(account)

    async def set_account_status(self, account_id: str, status: AccountStatus) -> bool:
        """
        Установить статус аккаунта.

        Args:
            account_id: Идентификатор аккаунта
            status: Новый статус

        Returns:
            True если статус был обновлён
        """
        account = await self.get_account(account_id)
        if not account:
            logger.warning(f"[MultiAccount] Account {account_id} not found")
            return False

        old_status = account.status
        account.status = status

        # Сбрасываем лимиты при активации
        if status == AccountStatus.ACTIVE:
            account.rate_limit_until = None
            account.failure_count = 0

        await self._save_account(account)
        logger.info(f"[MultiAccount] Account {account_id} status: {old_status.value} -> {status.value}")

        return True

    async def clear_rate_limit(self, account_id: str) -> bool:
        """
        Очистить лимит для аккаунта.

        Args:
            account_id: Идентификатор аккаунта

        Returns:
            True если лимит был очищен
        """
        account = await self.get_account(account_id)
        if not account:
            return False

        if account.status == AccountStatus.RATE_LIMITED:
            account.status = AccountStatus.ACTIVE

        account.rate_limit_until = None
        await self._save_account(account)

        logger.info(f"[MultiAccount] Cleared rate limit for account {account_id}")
        return True

    async def get_pool_stats(self) -> Dict[str, Any]:
        """
        Получить статистику пула аккаунтов.

        Returns:
            Словарь со статистикой
        """
        accounts = await self.get_all_accounts()
        available = await self.get_available_accounts()

        status_counts: Dict[str, int] = {}
        for status in AccountStatus:
            status_counts[status.value] = sum(1 for a in accounts if a.status == status)

        total_requests = sum(a.request_count for a in accounts)

        return {
            "total_accounts": len(accounts),
            "available_accounts": len(available),
            "status_distribution": status_counts,
            "total_requests": total_requests,
            "selection_strategy": self.selection_strategy.value,
        }

    async def cleanup_expired_limits(self) -> int:
        """
        Очистить истёкшие лимиты.

        Returns:
            Количество очищенных аккаунтов
        """
        await self._refresh_cache()

        cleaned = 0
        for account in self._local_cache.values():
            if (account.status == AccountStatus.RATE_LIMITED and
                account.rate_limit_until and
                datetime.now() >= account.rate_limit_until):

                account.status = AccountStatus.ACTIVE
                account.rate_limit_until = None
                await self._save_account(account)
                cleaned += 1

        if cleaned > 0:
            logger.info(f"[MultiAccount] Cleaned up {cleaned} expired rate limits")

        return cleaned


# Глобальный экземпляр
multi_account_limiter = MultiAccountRateLimiter()
