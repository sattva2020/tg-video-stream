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
import logging
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

    async def select_account(self) -> Optional[AccountInfo]:
        """
        Выбрать аккаунт для выполнения запроса.

        Использует настроенную стратегию выбора (least-used, round-robin, etc.)

        Returns:
            AccountInfo или None если нет доступных аккаунтов
        """
        available = await self.get_available_accounts()

        if not available:
            logger.warning("[MultiAccount] No available accounts")
            return None

        selected_account: Optional[AccountInfo] = None

        if self.selection_strategy == SelectionStrategy.LEAST_USED:
            # Выбираем аккаунт с наименьшим количеством запросов
            selected_account = min(available, key=lambda a: a.request_count)

        elif self.selection_strategy == SelectionStrategy.ROUND_ROBIN:
            # Выбираем по очереди
            r = await self._get_redis()
            try:
                # Инкрементируем счётчик и получаем индекс
                index = await r.incr(self.ROUND_ROBIN_COUNTER) - 1
                # Зацикливаем на количестве доступных аккаунтов
                index = index % len(available)
                selected_account = available[index]
            finally:
                await r.close()

        elif self.selection_strategy == SelectionStrategy.WEIGHTED:
            # Выбираем с весами (меньше отказов = выше приоритет)
            def weight(account: AccountInfo) -> float:
                base = 1.0
                # Штраф за количество запросов
                base /= (account.request_count + 1)
                # Штраф за отказы
                base /= (account.failure_count + 1)
                return base

            selected_account = max(available, key=weight)

        if selected_account:
            logger.info(f"[MultiAccount] Selected account {selected_account.account_id} "
                       f"(strategy: {self.selection_strategy.value})")

        return selected_account

    async def mark_account_used(self, account_id: str) -> None:
        """
        Отметить аккаунт как использованный.

        Args:
            account_id: Идентификатор аккаунта
        """
        account = await self.get_account(account_id)
        if not account:
            logger.warning(f"[MultiAccount] Account {account_id} not found")
            return

        account.request_count += 1
        account.last_used = datetime.now()

        await self._save_account(account)
        logger.debug(f"[MultiAccount] Marked account {account_id} as used "
                    f"(total: {account.request_count})")

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
