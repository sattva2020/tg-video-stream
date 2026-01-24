"""
Rate Limit Predictor Service
ML-сервис для предсказания достижения лимитов Telegram API.

Отслеживает использование API по каждому аккаунту и типу запроса.
Предсказывает время достижения лимитов на основе скользящего окна и трендов.

Автор: Jarvis
Дата: 2025-01-24
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

import redis.asyncio as redis
from src.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
REDIS_URL = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
PREDICTION_WINDOW_MINUTES = int(os.getenv('PREDICTION_WINDOW_MINUTES', '60'))
ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', '0.75'))  # 75%
SLIDING_WINDOW_SIZE = int(os.getenv('SLIDING_WINDOW_SIZE', '3600'))  # 1 час в секундах


class EndpointType(Enum):
    """Типы запросов к Telegram API"""
    MESSAGES = "messages"              # Отправка сообщений
    MEDIA = "media"                    # Загрузка медиа
    GET_CHAT = "get_chat"              # Получение информации о чатах
    GET_HISTORY = "get_history"        # Получение истории сообщений
    JOIN_CHANNEL = "join_channel"      # Вступление в каналы
    OTHER = "other"                    # Прочие запросы


@dataclass
class UsageStats:
    """Статистика использования API"""
    account_id: str
    endpoint_type: EndpointType
    request_count: int = 0
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    requests_per_minute: float = 0.0
    trend: str = "stable"  # increasing, stable, decreasing


@dataclass
class Prediction:
    """Предсказание достижения лимита"""
    account_id: str
    endpoint_type: EndpointType
    limit: int
    current_usage: int
    usage_percent: float
    predicted_breach_time: Optional[datetime]
    time_until_breach_seconds: Optional[int]
    trend: str
    confidence: float  # 0.0 to 1.0
    alert_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "endpoint_type": self.endpoint_type.value,
            "limit": self.limit,
            "current_usage": self.current_usage,
            "usage_percent": round(self.usage_percent, 2),
            "predicted_breach_time": self.predicted_breach_time.isoformat() if self.predicted_breach_time else None,
            "time_until_breach_seconds": self.time_until_breach_seconds,
            "trend": self.trend,
            "confidence": round(self.confidence, 2),
            "alert_triggered": self.alert_triggered,
            "is_critical": self.usage_percent >= 90,
        }


class UsageTracker:
    """Трекер использования API с скользящим окном"""

    REDIS_PREFIX = "rate_limit_usage"
    TIMESTAMP_KEY = "timestamps"

    def __init__(self):
        self.redis_url = REDIS_URL

    async def _get_redis(self) -> redis.Redis:
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def record_request(
        self,
        account_id: str,
        endpoint_type: EndpointType,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Записать запрос в скользящее окно.

        Args:
            account_id: ID аккаунта Telegram
            endpoint_type: Тип запроса
            timestamp: Время запроса (по умолчанию текущее)
        """
        if timestamp is None:
            timestamp = datetime.now()

        r = await self._get_redis()
        try:
            # Ключ для хранения временных меток запросов
            key = f"{self.REDIS_PREFIX}:{account_id}:{endpoint_type.value}"

            # Добавляем timestamp в отсортированное множество
            timestamp_ms = int(timestamp.timestamp() * 1000)
            await r.zadd(key, {str(timestamp_ms): timestamp_ms})

            # Удаляем старые записи вне окна
            cutoff_time = (datetime.now() - timedelta(seconds=SLIDING_WINDOW_SIZE)).timestamp() * 1000
            await r.zremrangebyscore(key, 0, cutoff_time)

            # Устанавливаем TTL
            await r.expire(key, SLIDING_WINDOW_SIZE + 60)

            logger.debug(f"[UsageTracker] Recorded request for {account_id}:{endpoint_type.value}")

        finally:
            await r.close()

    async def get_usage_stats(
        self,
        account_id: str,
        endpoint_type: EndpointType,
        window_seconds: int = SLIDING_WINDOW_SIZE
    ) -> UsageStats:
        """
        Получить статистику использования за окно.

        Args:
            account_id: ID аккаунта
            endpoint_type: Тип запроса
            window_seconds: Размер окна в секундах

        Returns:
            UsageStats со статистикой
        """
        r = await self._get_redis()
        try:
            key = f"{self.REDIS_PREFIX}:{account_id}:{endpoint_type.value}"

            now = datetime.now()
            window_start = now - timedelta(seconds=window_seconds)

            # Получаем все записи в окне
            cutoff_ms = int(window_start.timestamp() * 1000)
            timestamps = await r.zrangebyscore(key, cutoff_ms, "+inf")

            request_count = len(timestamps)
            requests_per_minute = request_count / (window_seconds / 60) if window_seconds > 0 else 0

            # Определяем тренд
            trend = await self._calculate_trend(timestamps, window_seconds)

            return UsageStats(
                account_id=account_id,
                endpoint_type=endpoint_type,
                request_count=request_count,
                window_start=window_start,
                window_end=now,
                requests_per_minute=round(requests_per_minute, 2),
                trend=trend
            )

        finally:
            await r.close()

    async def _calculate_trend(
        self,
        timestamps: List[str],
        window_seconds: int
    ) -> str:
        """
        Рассчитать тренд использования.

        Args:
            timestamps: Список timestamp в миллисекундах
            window_seconds: Размер окна

        Returns:
            'increasing', 'stable', или 'decreasing'
        """
        if len(timestamps) < 10:
            return "stable"

        try:
            # Разбиваем окно на две половины
            ts = [int(ts) for ts in timestamps]
            mid_point = (datetime.now() - timedelta(seconds=window_seconds / 2)).timestamp() * 1000

            first_half = len([t for t in ts if t < mid_point])
            second_half = len([t for t in ts if t >= mid_point])

            # Сравниваем количество запросов в каждой половине
            if second_half > first_half * 1.2:
                return "increasing"
            elif first_half > second_half * 1.2:
                return "decreasing"
            else:
                return "stable"

        except Exception as e:
            logger.warning(f"Error calculating trend: {e}")
            return "stable"

    async def get_account_usage_summary(
        self,
        account_id: str
    ) -> Dict[str, UsageStats]:
        """
        Получить сводку использования по всем типам запросов.

        Args:
            account_id: ID аккаунта

        Returns:
            Словарь {endpoint_type: UsageStats}
        """
        summary = {}
        for endpoint in EndpointType:
            stats = await self.get_usage_stats(account_id, endpoint)
            summary[endpoint.value] = stats
        return summary


class RateLimitPredictor:
    """ML-модель для предсказания достижения лимитов"""

    # Стандартные лимиты Telegram API (зависят от типа аккаунта)
    DEFAULT_LIMITS = {
        EndpointType.MESSAGES: 30,      # 30 сообщений в секунду (bot)
        EndpointType.MEDIA: 20,         # 20 медиа в минуту
        EndpointType.GET_CHAT: 60,      # 60 запросов в секунду
        EndpointType.GET_HISTORY: 50,   # 50 запросов в секунду для истории
        EndpointType.JOIN_CHANNEL: 50,  # 50 вступлений в день
        EndpointType.OTHER: 100,        # Общий лимит
    }

    def __init__(self):
        self.tracker = UsageTracker()
        self.redis_url = REDIS_URL
        self.alert_threshold = ALERT_THRESHOLD

    async def predict_breach_time(
        self,
        account_id: str,
        endpoint_type: EndpointType,
        custom_limit: Optional[int] = None
    ) -> Prediction:
        """
        Предсказать время достижения лимита.

        Args:
            account_id: ID аккаунта
            endpoint_type: Тип запроса
            custom_limit: Кастомный лимит (если есть)

        Returns:
            Prediction с предсказанием
        """
        # Получаем статистику использования
        stats = await self.tracker.get_usage_stats(account_id, endpoint_type)

        # Определяем лимит
        limit = custom_limit or self.DEFAULT_LIMITS.get(endpoint_type, 100)

        # Текущее использование в процентах
        usage_percent = (stats.request_count / limit * 100) if limit > 0 else 0

        # Параметры предсказания
        current_rpm = stats.requests_per_minute
        trend = stats.trend

        # Рассчитываем предсказание
        predicted_breach_time = None
        time_until_breach = None
        confidence = 0.5
        alert_triggered = usage_percent >= self.alert_threshold * 100

        if usage_percent >= 100:
            # Лимит уже превышен
            predicted_breach_time = datetime.now()
            time_until_breach = 0
            confidence = 1.0
        elif current_rpm > 0 and usage_percent > 50:
            # Предсказываем время достижения на основе текущей скорости
            remaining_requests = limit - stats.request_count

            # Корректируем скорость на основе тренда
            adjusted_rpm = current_rpm
            if trend == "increasing":
                adjusted_rpm *= 1.2  # Ожидаем увеличение на 20%
                confidence = 0.7
            elif trend == "decreasing":
                adjusted_rpm *= 0.8  # Ожидаем уменьшение на 20%
                confidence = 0.6
            else:
                confidence = 0.8  # Стабильный тренд - выше уверенность

            # Рассчитываем минуты до достижения лимита
            if adjusted_rpm > 0:
                minutes_until_breach = remaining_requests / adjusted_rpm
                time_until_breach = int(minutes_until_breach * 60)
                predicted_breach_time = datetime.now() + timedelta(seconds=time_until_breach)

        return Prediction(
            account_id=account_id,
            endpoint_type=endpoint_type,
            limit=limit,
            current_usage=stats.request_count,
            usage_percent=usage_percent,
            predicted_breach_time=predicted_breach_time,
            time_until_breach_seconds=time_until_breach,
            trend=trend,
            confidence=confidence,
            alert_triggered=alert_triggered
        )

    async def predict_all_endpoints(
        self,
        account_id: str,
        custom_limits: Optional[Dict[EndpointType, int]] = None
    ) -> List[Prediction]:
        """
        Предсказать для всех типов запросов аккаунта.

        Args:
            account_id: ID аккаунта
            custom_limits: Кастомные лимиты для некоторых типов

        Returns:
            Список Prediction для всех типов
        """
        predictions = []

        for endpoint in EndpointType:
            custom_limit = custom_limits.get(endpoint) if custom_limits else None
            prediction = await self.predict_breach_time(account_id, endpoint, custom_limit)
            predictions.append(prediction)

        return predictions

    async def save_predictions(self, predictions: List[Prediction]) -> None:
        """
        Сохранить предсказания в Redis для дашборда.

        Args:
            predictions: Список предсказаний
        """
        r = await self._get_redis()
        try:
            for prediction in predictions:
                key = f"rate_limit_prediction:{prediction.account_id}:{prediction.endpoint_type.value}"

                # Сохраняем предсказание
                await r.hset(key, mapping={
                    "limit": str(prediction.limit),
                    "current_usage": str(prediction.current_usage),
                    "usage_percent": str(prediction.usage_percent),
                    "predicted_breach_time": prediction.predicted_breach_time.isoformat() if prediction.predicted_breach_time else "",
                    "time_until_breach_seconds": str(prediction.time_until_breach_seconds) if prediction.time_until_breach_seconds else "",
                    "trend": prediction.trend,
                    "confidence": str(prediction.confidence),
                    "alert_triggered": "1" if prediction.alert_triggered else "0",
                    "updated_at": datetime.now().isoformat(),
                })

                # TTL на 5 минут
                await r.expire(key, 300)

            # Сохраняем сводный ключ для аккаунта
            if predictions:
                account_id = predictions[0].account_id
                summary_key = f"rate_limit_prediction:{account_id}:summary"
                await r.set(summary_key, json.dumps({
                    "predictions": [p.to_dict() for p in predictions],
                    "updated_at": datetime.now().isoformat(),
                }))
                await r.expire(summary_key, 300)

            logger.debug(f"[Predictor] Saved {len(predictions)} predictions")

        finally:
            await r.close()

    async def _get_redis(self) -> redis.Redis:
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def get_predictions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Получить сохраненные предсказания для аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            Список предсказаний в виде словарей
        """
        r = await self._get_redis()
        try:
            summary_key = f"rate_limit_prediction:{account_id}:summary"
            data = await r.get(summary_key)

            if data:
                parsed = json.loads(data)
                return parsed.get("predictions", [])

            return []

        finally:
            await r.close()

    async def get_all_account_predictions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить предсказания для всех аккаунтов.

        Returns:
            Словарь {account_id: [predictions]}
        """
        r = await self._get_redis()
        try:
            pattern = "rate_limit_prediction:*:summary"
            predictions = {}

            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor, match=pattern, count=100)
                for key in keys:
                    try:
                        # Извлекаем account_id из ключа
                        account_id = key.split(":")[2]
                        data = await r.get(key)
                        if data:
                            parsed = json.loads(data)
                            predictions[account_id] = parsed.get("predictions", [])
                    except Exception as e:
                        logger.warning(f"Error parsing prediction key {key}: {e}")

                if cursor == 0:
                    break

            return predictions

        finally:
            await r.close()

    async def get_critical_predictions(self) -> List[Dict[str, Any]]:
        """
        Получить все критические предсказания (usage_percent >= 90%).

        Returns:
            Список критических предсказаний
        """
        all_predictions = await self.get_all_account_predictions()
        critical = []

        for account_id, predictions in all_predictions.items():
            for pred in predictions:
                if pred.get("usage_percent", 0) >= 90:
                    critical.append(pred)

        # Сортируем по usage_percent по убыванию
        critical.sort(key=lambda x: x.get("usage_percent", 0), reverse=True)

        return critical


class RateLimitPredictionService:
    """Основной сервис предсказания лимитов"""

    def __init__(self):
        self.tracker = UsageTracker()
        self.predictor = RateLimitPredictor()

    async def record_request(
        self,
        account_id: str,
        endpoint_type: EndpointType,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Записать запрос и обновить предсказания.

        Args:
            account_id: ID аккаунта
            endpoint_type: Тип запроса
            timestamp: Время запроса
        """
        await self.tracker.record_request(account_id, endpoint_type, timestamp)

    async def update_predictions(self, account_id: str) -> List[Prediction]:
        """
        Обновить предсказания для аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            Список обновленных предсказаний
        """
        predictions = await self.predictor.predict_all_endpoints(account_id)
        await self.predictor.save_predictions(predictions)
        return predictions

    async def get_account_status(self, account_id: str) -> Dict[str, Any]:
        """
        Получить полный статус аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            Словарь со статусом
        """
        # Получаем предсказания
        predictions = await self.predictor.get_predictions(account_id)

        # Получаем использование
        usage_summary = await self.tracker.get_account_usage_summary(account_id)

        # Определяем общий статус
        max_usage = max([p.get("usage_percent", 0) for p in predictions]) if predictions else 0
        any_alert = any([p.get("alert_triggered", False) for p in predictions])

        return {
            "account_id": account_id,
            "status": "critical" if max_usage >= 90 else "warning" if any_alert else "ok",
            "max_usage_percent": round(max_usage, 2),
            "predictions": predictions,
            "usage_summary": {
                k: {
                    "request_count": v.request_count,
                    "requests_per_minute": v.requests_per_minute,
                    "trend": v.trend
                }
                for k, v in usage_summary.items()
            },
            "updated_at": datetime.now().isoformat(),
        }

    async def get_global_status(self) -> Dict[str, Any]:
        """
        Получить глобальный статус всех аккаунтов.

        Returns:
            Словарь с глобальной статистикой
        """
        all_predictions = await self.predictor.get_all_account_predictions()

        total_accounts = len(all_predictions)
        critical_accounts = 0
        warning_accounts = 0

        for account_id, predictions in all_predictions.items():
            max_usage = max([p.get("usage_percent", 0) for p in predictions]) if predictions else 0
            if max_usage >= 90:
                critical_accounts += 1
            elif max_usage >= 75:
                warning_accounts += 1

        # Получаем критические предсказания
        critical = await self.predictor.get_critical_predictions()

        return {
            "total_accounts": total_accounts,
            "critical_accounts": critical_accounts,
            "warning_accounts": warning_accounts,
            "ok_accounts": total_accounts - critical_accounts - warning_accounts,
            "critical_predictions": critical[:10],  # Топ-10 критических
            "status": "critical" if critical_accounts > 0 else "warning" if warning_accounts > 0 else "ok",
            "updated_at": datetime.now().isoformat(),
        }


# Глобальный экземпляр
rate_limit_predictor = RateLimitPredictionService()
