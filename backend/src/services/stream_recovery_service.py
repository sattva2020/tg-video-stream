"""Stream Recovery Service.

Сервис для автоматического восстановления потоков с exponential backoff retry logic.
Создан в рамках Feature 001 (Intelligent Auto-Recovery System).

**Purpose**: Автоматическое восстановление stream после различных типов failures
**Layer**: Service (domain logic)
**Features**: Exponential backoff, circuit breaker integration, retry strategies

**Design Decision**:
- Отдельный сервис для координации recovery операций
- Использует CircuitBreaker для предотвращения cascading failures
- Логирует все попытки восстановления в RecoveryLog model
- Поддерживает различные стратегии восстановления (restart, reconnect, fallback)
"""

import logging
import random
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.services.stream_controller import StreamController, get_stream_controller
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from src.models.recovery_log import (
    RecoveryLog,
    RecoveryFailureType,
    RecoveryStrategy,
    RecoveryStatus
)
from src.models.stream import Stream

logger = logging.getLogger(__name__)


@dataclass
class RecoveryConfig:
    """Конфигурация для retry logic и exponential backoff."""
    max_retries: int = 3                # Максимальное количество попыток
    base_delay: int = 60                # Базовая задержка в секундах (1 минута)
    max_backoff: int = 600              # Максимальная задержка (10 минут)
    exponential_base: int = 2           # Экспоненциальная база (каждая попытка умножает на 2)
    jitter: bool = True                 # Добавлять случайную задержку для thundering herd prevention
    jitter_factor: float = 0.1          # Jitter factor (10% от delay)

    # Circuit breaker thresholds
    circuit_breaker_failure_threshold: int = 5      # Failures перед открытием circuit
    circuit_breaker_timeout: int = 300              # Seconds до half-open (5 минут)


class StreamRecoveryService:
    """Сервис для автоматического восстановления stream с exponential backoff.

    **Features**:
    - Exponential backoff retry logic (60s, 120s, 240s, ..., max 600s)
    - Circuit breaker integration для предотвращения cascading failures
    - Детальное логирование всех попыток восстановления
    - Поддержка различных recovery strategies (restart, reconnect, fallback)
    - Jitter для предотвращения thundering herd problem

    **Usage**:
        service = StreamRecoveryService(db_session)
        result = service.recover_stream(
            stream_id=uuid.uuid4(),
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Connection timeout"
        )
        if result["success"]:
            logger.info(f"Stream recovered: {result}")
        else:
            logger.error(f"Recovery failed: {result['error']}")
    """

    def __init__(
        self,
        db_session: Session,
        config: Optional[RecoveryConfig] = None,
        stream_controller: Optional[StreamController] = None
    ):
        """Инициализация сервиса восстановления.

        Args:
            db_session: SQLAlchemy database session
            config: Optional custom recovery configuration
            stream_controller: Optional stream controller (dependency injection)
        """
        self.db = db_session
        self.config = config or RecoveryConfig()
        self.stream_controller = stream_controller or get_stream_controller()

        # Circuit breaker registry (один circuit breaker на stream)
        self._circuit_breakers: Dict[uuid.UUID, CircuitBreaker] = {}

        logger.info(
            f"StreamRecoveryService initialized: "
            f"max_retries={self.config.max_retries}, "
            f"base_delay={self.config.base_delay}s, "
            f"max_backoff={self.config.max_backoff}s"
        )

    def recover_stream(
        self,
        stream_id: uuid.UUID,
        failure_type: RecoveryFailureType,
        failure_reason: str,
        strategy: RecoveryStrategy = RecoveryStrategy.RESTART,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        recovery_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Попытаться восстановить stream с exponential backoff retry logic.

        Args:
            stream_id: UUID stream для восстановления
            failure_type: Тип failure (network, api_rate_limit, codec_error, etc.)
            failure_reason: Детальное описание причины failure
            strategy: Стратегия восстановления (restart, reconnect, fallback)
            error_code: Optional код ошибки
            error_details: Optional детали ошибки (stack trace, context)
            recovery_metadata: Optional контекст восстановления

        Returns:
            Dictionary с результатом восстановления:
            {
                "success": bool,           # Успешно ли восстановлено
                "attempt_number": int,     # Номер успешной попытки
                "total_attempts": int,     # Общее количество попыток
                "recovery_log_id": uuid,   # ID записи в recovery_logs
                "error": Optional[str],    # Ошибка если не удалось
                "circuit_breaker_open": bool  # Открыт ли circuit breaker
            }
        """
        # Проверка circuit breaker
        circuit_breaker = self._get_circuit_breaker(stream_id)

        if not circuit_breaker.allow_request():
            logger.warning(
                f"Circuit breaker OPEN for stream {stream_id}, "
                f"recovery blocked until {circuit_breaker.open_until}"
            )
            return {
                "success": False,
                "error": "Circuit breaker is OPEN, recovery blocked",
                "circuit_breaker_open": True,
                "open_until": circuit_breaker.open_until,
                "attempt_number": 0,
                "total_attempts": 0
            }

        # Загрузка stream из database
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            logger.error(f"Stream {stream_id} not found in database")
            return {
                "success": False,
                "error": "Stream not found",
                "circuit_breaker_open": circuit_breaker.state == CircuitBreakerState.OPEN,
                "attempt_number": 0,
                "total_attempts": 0
            }

        logger.info(
            f"Starting recovery for stream {stream_id}: "
            f"failure_type={failure_type}, strategy={strategy}, "
            f"max_retries={self.config.max_retries}"
        )

        # Retry loop с exponential backoff
        last_error = None

        for attempt_number in range(1, self.config.max_retries + 1):
            # Создание записи в recovery_logs
            backoff_seconds = self._calculate_backoff(attempt_number)

            recovery_log = self._create_recovery_log(
                stream_id=stream_id,
                failure_type=failure_type,
                failure_reason=failure_reason,
                strategy=strategy,
                attempt_number=attempt_number,
                backoff_seconds=backoff_seconds,
                error_code=error_code,
                error_details=error_details,
                recovery_metadata=recovery_metadata,
                circuit_breaker_info=circuit_breaker.get_state_info()
            )

            try:
                # Выполнение попытки восстановления
                logger.info(
                    f"Recovery attempt {attempt_number}/{self.config.max_retries} "
                    f"for stream {stream_id} (backoff={backoff_seconds}s)"
                )

                # Apply backoff delay (не для первой попытки)
                if attempt_number > 1:
                    time.sleep(backoff_seconds)

                # Обновление статуса на IN_PROGRESS
                recovery_log.status = RecoveryStatus.IN_PROGRESS
                self.db.commit()

                # Выполнение recovery операции
                recovery_result = self._execute_recovery(
                    stream=stream,
                    strategy=strategy,
                    failure_type=failure_type
                )

                if recovery_result["success"]:
                    # Успешное восстановление
                    recovery_log.status = RecoveryStatus.SUCCESS
                    recovery_log.completed_at = datetime.now(timezone.utc)
                    recovery_log.duration_ms = int(
                        (recovery_log.completed_at - recovery_log.started_at).total_seconds() * 1000
                    )
                    self.db.commit()

                    # Записываем success в circuit breaker
                    circuit_breaker.record_success()

                    logger.info(
                        f"Successfully recovered stream {stream_id} "
                        f"on attempt {attempt_number}/{self.config.max_retries}"
                    )

                    return {
                        "success": True,
                        "attempt_number": attempt_number,
                        "total_attempts": attempt_number,
                        "recovery_log_id": str(recovery_log.id),
                        "duration_ms": recovery_log.duration_ms,
                        "circuit_breaker_open": False
                    }
                else:
                    # Неудачная попытка
                    last_error = recovery_result.get("error", "Unknown error")
                    logger.warning(
                        f"Recovery attempt {attempt_number}/{self.config.max_retries} "
                        f"failed for stream {stream_id}: {last_error}"
                    )

                    # Проверяем, есть ли еще попытки
                    if attempt_number < self.config.max_retries:
                        recovery_log.status = RecoveryStatus.FAILED
                        recovery_log.completed_at = datetime.now(timezone.utc)
                        recovery_log.duration_ms = int(
                            (recovery_log.completed_at - recovery_log.started_at).total_seconds() * 1000
                        )
                        self.db.commit()

                        # Записываем failure в circuit breaker
                        circuit_breaker.record_failure()

                        # Продолжаем к следующей попытке
                        continue
                    else:
                        # Последняя попытка неудачна
                        recovery_log.status = RecoveryStatus.ABANDONED
                        recovery_log.completed_at = datetime.now(timezone.utc)
                        recovery_log.duration_ms = int(
                            (recovery_log.completed_at - recovery_log.started_at).total_seconds() * 1000
                        )
                        self.db.commit()

                        # Записываем failure в circuit breaker
                        circuit_breaker.record_failure()

                        logger.error(
                            f"Recovery abandoned for stream {stream_id} "
                            f"after {attempt_number} failed attempts"
                        )

                        return {
                            "success": False,
                            "error": f"Recovery failed after {attempt_number} attempts: {last_error}",
                            "attempt_number": attempt_number,
                            "total_attempts": attempt_number,
                            "recovery_log_id": str(recovery_log.id),
                            "circuit_breaker_open": circuit_breaker.state == CircuitBreakerState.OPEN
                        }

            except Exception as e:
                # Непредвиденная ошибка
                last_error = str(e)
                logger.exception(
                    f"Unexpected error during recovery attempt {attempt_number} "
                    f"for stream {stream_id}: {e}"
                )

                recovery_log.status = RecoveryStatus.FAILED
                recovery_log.completed_at = datetime.now(timezone.utc)
                recovery_log.duration_ms = int(
                    (recovery_log.completed_at - recovery_log.started_at).total_seconds() * 1000
                )
                self.db.commit()

                # Записываем failure в circuit breaker
                circuit_breaker.record_failure()

                # Проверяем, есть ли еще попытки
                if attempt_number >= self.config.max_retries:
                    logger.error(
                        f"Recovery abandoned for stream {stream_id} "
                        f"after {attempt_number} failed attempts with exceptions"
                    )
                    return {
                        "success": False,
                        "error": f"Recovery failed with exception: {last_error}",
                        "attempt_number": attempt_number,
                        "total_attempts": attempt_number,
                        "recovery_log_id": str(recovery_log.id) if recovery_log else None,
                        "circuit_breaker_open": circuit_breaker.state == CircuitBreakerState.OPEN
                    }

        # Не должны сюда попасть, но на всякий случай
        return {
            "success": False,
            "error": last_error or "Recovery failed for unknown reason",
            "circuit_breaker_open": circuit_breaker.state == CircuitBreakerState.OPEN,
            "attempt_number": self.config.max_retries,
            "total_attempts": self.config.max_retries
        }

    def _calculate_backoff(self, attempt_number: int) -> int:
        """Рассчитать exponential backoff delay с optional jitter.

        Formula: min(base_delay * (exponential_base ^ (attempt - 1)), max_backoff)

        Args:
            attempt_number: Номер попытки (1-based)

        Returns:
            Задержка в секундах
        """
        # Экспоненциальный backoff: 60s, 120s, 240s, 480s, 600s (capped)
        exponential_delay = self.config.base_delay * (
            self.config.exponential_base ** (attempt_number - 1)
        )

        # Cap at max_backoff
        capped_delay = min(exponential_delay, self.config.max_backoff)

        # Добавить jitter для предотвращения thundering herd
        if self.config.jitter:
            jitter_range = capped_delay * self.config.jitter_factor
            jitter_value = random.uniform(-jitter_range, jitter_range)
            final_delay = int(capped_delay + jitter_value)
        else:
            final_delay = int(capped_delay)

        logger.debug(
            f"Calculated backoff for attempt {attempt_number}: "
            f"exponential={exponential_delay}s, capped={capped_delay}s, final={final_delay}s"
        )

        return max(1, final_delay)  # Минимум 1 секунда

    def _execute_recovery(
        self,
        stream: Stream,
        strategy: RecoveryStrategy,
        failure_type: RecoveryFailureType
    ) -> Dict[str, Any]:
        """Выполнить recovery операцию в соответствии со стратегией.

        Args:
            stream: Stream ORM model
            strategy: Стратегия восстановления
            failure_type: Тип failure

        Returns:
            Результат выполнения операции
        """
        try:
            if strategy == RecoveryStrategy.RESTART:
                # Полный перезапуск потока
                logger.info(f"Executing RESTART strategy for stream {stream.id}")

                # Остановить поток
                stop_success = self.stream_controller.stop_stream()
                if not stop_success:
                    return {
                        "success": False,
                        "error": "Failed to stop stream"
                    }

                # Небольшая задержка перед запуском
                time.sleep(2)

                # Запустить поток
                start_success = self.stream_controller.start_stream()
                if not start_success:
                    return {
                        "success": False,
                        "error": "Failed to start stream"
                    }

                return {"success": True}

            elif strategy == RecoveryStrategy.RECONNECT:
                # Переподключение без остановки (например, переинициализация API client)
                logger.info(f"Executing RECONNECT strategy for stream {stream.id}")

                # В реальной реализации здесь может быть:
                # - Reconnect to Telegram API
                # - Reinitialize FFmpeg pipeline
                # - Refresh session credentials

                # Для примера используем restart
                return self._execute_recovery(stream, RecoveryStrategy.RESTART, failure_type)

            elif strategy == RecoveryStrategy.FALLBACK:
                # Переключение на fallback URL/источник
                logger.info(f"Executing FALLBACK strategy for stream {stream.id}")

                # В реальной реализации здесь может быть:
                # - Switch to backup stream URL
                # - Use alternative video source
                # - Fallback to cached content

                # Пока не реализовано
                return {
                    "success": False,
                    "error": "FALLBACK strategy not implemented yet"
                }

            elif strategy == RecoveryStrategy.MANUAL:
                # Требует ручного вмешательства
                logger.warning(f"MANUAL strategy for stream {stream.id}, skipping auto-recovery")
                return {
                    "success": False,
                    "error": "Manual intervention required"
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown recovery strategy: {strategy}"
                }

        except Exception as e:
            logger.exception(f"Error executing recovery for stream {stream.id}: {e}")
            return {
                "success": False,
                "error": f"Recovery execution failed: {str(e)}"
            }

    def _create_recovery_log(
        self,
        stream_id: uuid.UUID,
        failure_type: RecoveryFailureType,
        failure_reason: str,
        strategy: RecoveryStrategy,
        attempt_number: int,
        backoff_seconds: int,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        recovery_metadata: Optional[Dict[str, Any]] = None,
        circuit_breaker_info: Optional[Dict[str, Any]] = None
    ) -> RecoveryLog:
        """Создать запись в recovery_logs table.

        Args:
            stream_id: UUID stream
            failure_type: Тип failure
            failure_reason: Описание причины
            strategy: Стратегия восстановления
            attempt_number: Номер попытки
            backoff_seconds: Задержка backoff
            error_code: Optional код ошибки
            error_details: Optional детали ошибки
            recovery_metadata: Optional контекст восстановления
            circuit_breaker_info: Optional состояние circuit breaker

        Returns:
            RecoveryLog ORM instance
        """
        recovery_log = RecoveryLog(
            stream_id=stream_id,
            failure_type=failure_type,
            failure_reason=failure_reason,
            error_code=error_code,
            recovery_strategy=strategy,
            status=RecoveryStatus.PENDING,
            attempt_number=attempt_number,
            max_attempts=self.config.max_retries,
            backoff_seconds=backoff_seconds,
            error_details=error_details,
            recovery_metadata=recovery_metadata,
            circuit_breaker_state=circuit_breaker_info
        )

        self.db.add(recovery_log)
        self.db.commit()

        logger.debug(
            f"Created RecoveryLog {recovery_log.id} for stream {stream_id}, "
            f"attempt {attempt_number}/{self.config.max_retries}"
        )

        return recovery_log

    def _get_circuit_breaker(self, stream_id: uuid.UUID) -> CircuitBreaker:
        """Получить или создать circuit breaker для stream.

        Args:
            stream_id: UUID stream

        Returns:
            CircuitBreaker instance
        """
        if stream_id not in self._circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
            self._circuit_breakers[stream_id] = CircuitBreaker(
                name=f"stream-{stream_id}",
                config=cb_config
            )

        return self._circuit_breakers[stream_id]

    def get_recovery_stats(self, stream_id: uuid.UUID) -> Dict[str, Any]:
        """Получить статистику восстановления для stream.

        Args:
            stream_id: UUID stream

        Returns:
            Словарь со статистикой:
            {
                "total_attempts": int,           # Общее количество попыток
                "successful_recoveries": int,    # Успешные восстановления
                "failed_recoveries": int,        # Неудачные восстановления
                "abandoned_recoveries": int,     # Прерванные восстановления
                "last_recovery": Optional[dict], # Последняя попытка
                "circuit_breaker": dict          # Состояние circuit breaker
            }
        """
        # Получить все записи recovery_logs для этого stream
        logs = self.db.query(RecoveryLog).filter(
            RecoveryLog.stream_id == stream_id
        ).order_by(RecoveryLog.started_at.desc()).all()

        total_attempts = len(logs)
        successful_recoveries = len([log for log in logs if log.status == RecoveryStatus.SUCCESS])
        failed_recoveries = len([log for log in logs if log.status == RecoveryStatus.FAILED])
        abandoned_recoveries = len([log for log in logs if log.status == RecoveryStatus.ABANDONED])

        # Последняя попытка
        last_recovery = None
        if logs:
            log = logs[0]
            last_recovery = {
                "id": str(log.id),
                "failure_type": log.failure_type.value,
                "strategy": log.recovery_strategy.value,
                "status": log.status.value,
                "attempt_number": log.attempt_number,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_ms": log.duration_ms
            }

        # Circuit breaker state
        circuit_breaker = self._get_circuit_breaker(stream_id)

        return {
            "stream_id": str(stream_id),
            "total_attempts": total_attempts,
            "successful_recoveries": successful_recoveries,
            "failed_recoveries": failed_recoveries,
            "abandoned_recoveries": abandoned_recoveries,
            "last_recovery": last_recovery,
            "circuit_breaker": circuit_breaker.get_state_info()
        }

    def reset_circuit_breaker(self, stream_id: uuid.UUID):
        """Сбросить circuit breaker для stream (manual intervention).

        Args:
            stream_id: UUID stream
        """
        circuit_breaker = self._get_circuit_breaker(stream_id)
        circuit_breaker.reset()
        logger.info(f"Circuit breaker manually reset for stream {stream_id}")

    def get_recent_recoveries(
        self,
        stream_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Получить недавние записи восстановления.

        Args:
            stream_id: Optional UUID stream для фильтрации
            limit: Максимальное количество записей

        Returns:
            Список recovery records
        """
        query = self.db.query(RecoveryLog)

        if stream_id:
            query = query.filter(RecoveryLog.stream_id == stream_id)

        logs = query.order_by(RecoveryLog.started_at.desc()).limit(limit).all()

        return [
            {
                "id": str(log.id),
                "stream_id": str(log.stream_id),
                "failure_type": log.failure_type.value,
                "failure_reason": log.failure_reason,
                "strategy": log.recovery_strategy.value,
                "status": log.status.value,
                "attempt_number": log.attempt_number,
                "max_attempts": log.max_attempts,
                "backoff_seconds": log.backoff_seconds,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "duration_ms": log.duration_ms,
                "error_code": log.error_code
            }
            for log in logs
        ]


# Singleton instance для использования в приложении
_recovery_service_instance: Optional[StreamRecoveryService] = None


def get_stream_recovery_service(db_session: Session) -> StreamRecoveryService:
    """Получить singleton instance StreamRecoveryService.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        StreamRecoveryService instance
    """
    global _recovery_service_instance
    if _recovery_service_instance is None:
        _recovery_service_instance = StreamRecoveryService(db_session)
    return _recovery_service_instance
