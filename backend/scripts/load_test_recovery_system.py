#!/usr/bin/env python3
"""
Load Test Script: Stream Recovery System

Стресс-тестирование системы автоматического восстановления с непрерывным мониторингом.

Этот скрипт:
- Создает множество тестовых потоков
- Симулирует различные типы отказов
- Отслеживает все события восстановления
- Рассчитывает метрики доступности (uptime)
- Генерирует подробный отчет

Usage:
    python scripts/load_test_recovery_system.py --duration 3600 --streams 10
    python scripts/load_test_recovery_system.py --duration 86400 --streams 50  # 24-hour test

Requirements:
    - Postgres database running
    - Redis running
    - Backend services configured
"""

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.stream import Stream, StreamStatus
from src.models.user import User
from src.models.recovery_log import (
    RecoveryLog,
    RecoveryFailureType,
    RecoveryStrategy
)
from src.services.stream_recovery_service import StreamRecoveryService, RecoveryConfig
from src.services.stream_health_monitor import StreamHealthMonitor
from src.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test_recovery.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Конфигурация нагрузочного тестирования."""
    duration_seconds: int = 3600  # 1 hour by default
    num_streams: int = 10
    failure_interval_min: int = 60  # Minimum seconds between failures
    failure_interval_max: int = 300  # Maximum seconds between failures
    recovery_config: Optional[RecoveryConfig] = None

    def __post_init__(self):
        if self.recovery_config is None:
            # Use fast recovery config for load testing
            self.recovery_config = RecoveryConfig(
                max_retries=3,
                base_delay=5,  # 5 seconds for load testing
                max_backoff=30,  # 30 seconds max
                exponential_base=2,
                jitter=True,
                circuit_breaker_failure_threshold=5,
                circuit_breaker_timeout=300
            )


@dataclass
class StreamTestContext:
    """Контекст тестирования потока."""
    stream_id: str
    created_at: datetime
    total_failures: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    uptime_seconds: float = 0.0
    downtime_seconds: float = 0.0
    last_failure_time: Optional[datetime] = None
    last_recovery_time: Optional[datetime] = None

    @property
    def uptime_percentage(self) -> float:
        """Процент доступности."""
        total_time = self.uptime_seconds + self.downtime_seconds
        if total_time == 0:
            return 100.0
        return (self.uptime_seconds / total_time) * 100


@dataclass
class LoadTestReport:
    """Отчет о нагрузочном тестировании."""
    test_start: datetime
    test_end: datetime
    duration_seconds: int
    num_streams: int
    total_failures: int
    total_successful_recoveries: int
    total_failed_recoveries: int
    overall_uptime_percentage: float
    stream_reports: List[Dict[str, Any]]
    recovery_logs: List[Dict[str, Any]]
    circuit_breaker_trips: int
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в dict."""
        return asdict(self)

    def save(self, filepath: str):
        """Сохранить отчет в файл."""
        report_data = self.to_dict()
        report_data['test_start'] = report_data['test_start'].isoformat()
        report_data['test_end'] = report_data['test_end'].isoformat()
        for sr in report_data['stream_reports']:
            if sr.get('last_failure_time'):
                sr['last_failure_time'] = sr['last_failure_time'].isoformat()
            if sr.get('last_recovery_time'):
                sr['last_recovery_time'] = sr['last_recovery_time'].isoformat()
        for rl in report_data['recovery_logs']:
            for key in ['started_at', 'completed_at', 'created_at', 'updated_at']:
                if rl.get(key):
                    rl[key] = rl[key].isoformat()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        log.info(f"Отчет сохранен: {filepath}")


class LoadTestRunner:
    """Запускает нагрузочное тестирование системы восстановления."""

    def __init__(self, config: LoadTestConfig, db_session: Session):
        self.config = config
        self.db_session = db_session
        self.stream_contexts: Dict[str, StreamTestContext] = {}
        self.recovery_service: Optional[StreamRecoveryService] = None
        self.health_monitor: Optional[StreamHealthMonitor] = None
        self.test_start: Optional[datetime] = None
        self.test_end: Optional[datetime] = None
        self._running = False
        self._circuit_breaker_trips = 0

    async def initialize(self):
        """Инициализация сервисов."""
        log.info("Инициализация сервисов нагрузочного тестирования...")

        # Initialize recovery service
        self.recovery_service = StreamRecoveryService(
            self.db_session,
            config=self.config.recovery_config
        )

        # Initialize health monitor
        self.health_monitor = StreamHealthMonitor()

        log.info("Сервисы инициализированы")

    async def setup_test_streams(self) -> List[Stream]:
        """Создание тестовых потоков."""
        log.info(f"Создание {self.config.num_streams} тестовых потоков...")

        # Get or create admin user
        admin_user = self.db_session.query(User).filter_by(
            email='load_test_admin@test.com'
        ).first()

        if not admin_user:
            admin_user = User(
                email='load_test_admin@test.com',
                google_id='load_test_admin',
                status='approved',
                role='admin'
            )
            self.db_session.add(admin_user)
            self.db_session.commit()
            self.db_session.refresh(admin_user)
            log.info(f"Создан admin пользователь: {admin_user.id}")

        streams = []
        for i in range(self.config.num_streams):
            stream = Stream(
                title=f"Load Test Stream {i+1}",
                chat_id=1234567890 + i,
                owner_id=admin_user.id,
                status=StreamStatus.ACTIVE,
                current_track_index=0
            )
            self.db_session.add(stream)
            self.db_session.commit()
            self.db_session.refresh(stream)
            streams.append(stream)

            # Initialize test context
            self.stream_contexts[str(stream.id)] = StreamTestContext(
                stream_id=str(stream.id),
                created_at=datetime.now(timezone.utc)
            )

        log.info(f"Создано {len(streams)} тестовых потоков")
        return streams

    async def simulate_stream_failure(self, stream_id: str) -> Dict[str, Any]:
        """Симулировать отказ потока."""
        failure_types = [
            RecoveryFailureType.NETWORK,
            RecoveryFailureType.API_RATE_LIMIT,
            RecoveryFailureType.CODEC_ERROR,
            RecoveryFailureType.SESSION_EXPIRED,
            RecoveryFailureType.PROCESS_CRASH
        ]

        failure_type = random.choice(failure_types)
        failure_reasons = {
            RecoveryFailureType.NETWORK: "Connection timeout",
            RecoveryFailureType.API_RATE_LIMIT: "Telegram API rate limit exceeded",
            RecoveryFailureType.CODEC_ERROR: "FFmpeg codec error",
            RecoveryFailureType.SESSION_EXPIRED: "Telegram session expired",
            RecoveryFailureType.PROCESS_CRASH: "Stream process crashed"
        }

        context = self.stream_contexts[stream_id]
        context.last_failure_time = datetime.now(timezone.utc)
        context.total_failures += 1

        log.info(f"Симуляция отказа потока {stream_id}: {failure_type.value}")

        # Trigger recovery
        recovery_start = time.time()
        recovery_result = await self._trigger_recovery(stream_id, failure_type, failure_reasons[failure_type])
        recovery_duration = time.time() - recovery_start

        # Track recovery
        if recovery_result['success']:
            context.successful_recoveries += 1
            context.uptime_seconds += recovery_duration
            context.last_recovery_time = datetime.now(timezone.utc)
        else:
            context.failed_recoveries += 1
            context.downtime_seconds += recovery_duration

            # Check if circuit breaker opened
            if recovery_result.get('circuit_breaker_opened'):
                self._circuit_breaker_trips += 1

        return {
            'stream_id': stream_id,
            'failure_type': failure_type.value,
            'failure_reason': failure_reasons[failure_type],
            'recovery_success': recovery_result['success'],
            'recovery_duration_seconds': recovery_duration,
            'circuit_breaker_opened': recovery_result.get('circuit_breaker_opened', False)
        }

    async def _trigger_recovery(
        self,
        stream_id: str,
        failure_type: RecoveryFailureType,
        failure_reason: str
    ) -> Dict[str, Any]:
        """Запустить восстановление потока."""
        try:
            # Simulate network delay
            await asyncio.sleep(random.uniform(0.1, 0.5))

            # Use recovery service to attempt recovery
            success = await self.recovery_service.recover_stream(
                stream_id=stream_id,
                failure_type=failure_type,
                failure_reason=failure_reason,
                strategy=RecoveryStrategy.RESTART
            )

            # Check circuit breaker state
            circuit_breaker_info = await self.health_monitor.get_circuit_breaker_info(stream_id)
            circuit_breaker_opened = circuit_breaker_info.get('state') == 'OPEN'

            return {
                'success': success,
                'circuit_breaker_opened': circuit_breaker_opened
            }

        except Exception as e:
            log.error(f"Ошибка при восстановлении потока {stream_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def run_load_test(self) -> LoadTestReport:
        """Запуск нагрузочного тестирования."""
        log.info(f"Начало нагрузочного тестирования: {self.config.duration_seconds} секунд")
        log.info(f"Количество потоков: {self.config.num_streams}")

        self.test_start = datetime.now(timezone.utc)
        self._running = True
        streams = await self.setup_test_streams()

        recovery_events = []
        stream_ids = [str(s.id) for s in streams]

        try:
            # Run load test for specified duration
            test_end_time = time.time() + self.config.duration_seconds

            while time.time() < test_end_time and self._running:
                # Random failures on random streams
                num_failures = random.randint(1, min(5, len(stream_ids)))
                selected_streams = random.sample(stream_ids, num_failures)

                for stream_id in selected_streams:
                    if not self._running:
                        break

                    event = await self.simulate_stream_failure(stream_id)
                    recovery_events.append(event)

                    # Add small delay between failures
                    await asyncio.sleep(random.uniform(0.5, 2.0))

                # Wait until next failure interval
                next_interval = random.uniform(
                    self.config.failure_interval_min,
                    self.config.failure_interval_max
                )
                log.info(f"Следующий цикл отказов через {next_interval:.1f} секунд")

                # Sleep in small increments to check _running flag
                sleep_end = time.time() + next_interval
                while time.time() < sleep_end and self._running:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            log.info("Тест прерван пользователем")

        finally:
            self._running = False
            self.test_end = datetime.now(timezone.utc)

        return await self._generate_report(recovery_events)

    async def _generate_report(self, recovery_events: List[Dict[str, Any]]) -> LoadTestReport:
        """Генерация отчета о нагрузочном тестировании."""
        log.info("Генерация отчета о нагрузочном тестировании...")

        # Fetch all recovery logs from database
        recovery_logs = self.db_session.query(RecoveryLog).all()

        # Calculate aggregate statistics
        total_failures = sum(ctx.total_failures for ctx in self.stream_contexts.values())
        total_successful = sum(ctx.successful_recoveries for ctx in self.stream_contexts.values())
        total_failed = sum(ctx.failed_recoveries for ctx in self.stream_contexts.values())

        # Calculate overall uptime
        total_uptime = sum(ctx.uptime_seconds for ctx in self.stream_contexts.values())
        total_downtime = sum(ctx.downtime_seconds for ctx in self.stream_contexts.values())
        total_time = total_uptime + total_downtime

        overall_uptime = (total_uptime / total_time * 100) if total_time > 0 else 100.0

        # Generate stream reports
        stream_reports = []
        for stream_id, context in self.stream_contexts.items():
            stream_reports.append({
                'stream_id': stream_id,
                'created_at': context.created_at,
                'total_failures': context.total_failures,
                'successful_recoveries': context.successful_recoveries,
                'failed_recoveries': context.failed_recoveries,
                'uptime_seconds': context.uptime_seconds,
                'downtime_seconds': context.downtime_seconds,
                'uptime_percentage': context.uptime_percentage,
                'last_failure_time': context.last_failure_time,
                'last_recovery_time': context.last_recovery_time
            })

        # Generate recovery log reports
        recovery_log_reports = []
        for log_entry in recovery_logs:
            recovery_log_reports.append({
                'id': str(log_entry.id),
                'stream_id': str(log_entry.stream_id),
                'failure_type': log_entry.failure_type.value,
                'failure_reason': log_entry.failure_reason,
                'strategy': log_entry.recovery_strategy.value if log_entry.recovery_strategy else None,
                'status': log_entry.status.value,
                'attempt_number': log_entry.attempt_number,
                'max_attempts': log_entry.max_attempts,
                'backoff_seconds': log_entry.backoff_seconds,
                'started_at': log_entry.started_at,
                'completed_at': log_entry.completed_at,
                'duration_ms': log_entry.duration_ms
            })

        # Determine recommendation
        if overall_uptime >= 99.0:
            recommendation = "✅ PASS: Система соответствует требованию 99%+ uptime"
        elif overall_uptime >= 95.0:
            recommendation = "⚠️  WARNING: Uptime ниже 99%, но выше 95%. Рекомендуется оптимизация"
        else:
            recommendation = "❌ FAIL: Uptime ниже 95%. Требуется доработка системы"

        actual_duration = int((self.test_end - self.test_start).total_seconds())

        report = LoadTestReport(
            test_start=self.test_start,
            test_end=self.test_end,
            duration_seconds=actual_duration,
            num_streams=self.config.num_streams,
            total_failures=total_failures,
            total_successful_recoveries=total_successful,
            total_failed_recoveries=total_failed,
            overall_uptime_percentage=round(overall_uptime, 2),
            stream_reports=stream_reports,
            recovery_logs=recovery_log_reports,
            circuit_breaker_trips=self._circuit_breaker_trips,
            recommendation=recommendation
        )

        return report

    def stop(self):
        """Остановить нагрузочное тестирование."""
        log.info("Остановка нагрузочного тестирования...")
        self._running = False


async def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description='Нагрузочное тестирование системы автоматического восстановления'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=3600,
        help='Длительность теста в секундах (по умолчанию: 3600 = 1 час)'
    )
    parser.add_argument(
        '--streams',
        type=int,
        default=10,
        help='Количество тестовых потоков (по умолчанию: 10)'
    )
    parser.add_argument(
        '--failure-interval-min',
        type=int,
        default=60,
        help='Минимальный интервал между отказами в секундах (по умолчанию: 60)'
    )
    parser.add_argument(
        '--failure-interval-max',
        type=int,
        default=300,
        help='Максимальный интервал между отказами в секундах (по умолчанию: 300)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='load_test_recovery_report.json',
        help='Файл для сохранения отчета (по умолчанию: load_test_recovery_report.json)'
    )

    args = parser.parse_args()

    # Create database connection
    database_url = str(settings.DATABASE_URL).replace('+aiomysql', '+pymysql')
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = SessionLocal()

    try:
        # Create load test config
        config = LoadTestConfig(
            duration_seconds=args.duration,
            num_streams=args.streams,
            failure_interval_min=args.failure_interval_min,
            failure_interval_max=args.failure_interval_max
        )

        log.info("="*80)
        log.info("НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ СИСТЕМЫ АВТОМАТИЧЕСКОГО ВОССТАНОВЛЕНИЯ")
        log.info("="*80)
        log.info(f"Длительность: {args.duration} секунд ({args.duration/3600:.2f} часов)")
        log.info(f"Количество потоков: {args.streams}")
        log.info(f"Интервал отказов: {args.failure_interval_min}-{args.failure_interval_max} секунд")
        log.info("="*80)

        # Create and run load test
        runner = LoadTestRunner(config, db_session)
        await runner.initialize()

        try:
            report = await runner.run_load_test()

            # Print summary
            log.info("="*80)
            log.info("РЕЗУЛЬТАТЫ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
            log.info("="*80)
            log.info(f"Длительность теста: {report.duration_seconds} секунд")
            log.info(f"Количество потоков: {report.num_streams}")
            log.info(f"Всего отказов: {report.total_failures}")
            log.info(f"Успешных восстановлений: {report.total_successful_recoveries}")
            log.info(f"Неудачных восстановлений: {report.total_failed_recoveries}")
            log.info(f"Срабатываний circuit breaker: {report.circuit_breaker_trips}")
            log.info(f"Общий uptime: {report.overall_uptime_percentage:.2f}%")
            log.info(f"Рекомендация: {report.recommendation}")
            log.info("="*80)

            # Save report
            report.save(args.output)

            # Return exit code based on uptime
            if report.overall_uptime_percentage >= 99.0:
                log.info("✅ ТЕСТ ПРОЙДЕН: Uptime >= 99%")
                return 0
            else:
                log.error(f"❌ ТЕСТ НЕ ПРОЙДЕН: Uptime {report.overall_uptime_percentage:.2f}% < 99%")
                return 1

        except Exception as e:
            log.error(f"Ошибка при выполнении нагрузочного теста: {e}", exc_info=True)
            return 1

    finally:
        db_session.close()
        engine.dispose()


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
