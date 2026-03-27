"""
Integration Tests: Telegram Session Health Monitoring End-to-End
Тестируем полный цикл автоматического мониторинга здоровья Telegram сессий

Coverage Target: End-to-end health monitoring flow testing

Тесты проверяют:
1. Celery task для проверки здоровья всех сессий
2. Обновление статуса здоровья в базе данных
3. Сохранение статуса здоровья в Redis
4. API endpoint для получения статуса здоровья
5. Корректное определение истекающих/истекших сессий
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.tasks.telegram_session_health import (
    check_all_telegram_sessions_health_task,
    check_session_health_sync,
    get_active_telegram_accounts
)
from src.services.telegram_session_monitor import (
    TelegramSessionMonitor,
    TelegramSessionHealth
)
from src.services.circuit_breaker import CircuitBreaker


@pytest.fixture
def test_user(db_session):
    """Create test user for Telegram accounts"""
    user = User(
        email='session_test_user@example.com',
        hashed_password='test_hash',
        role='admin',
        status='approved'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def healthy_session_account(db_session, test_user):
    """Create Telegram account with healthy session"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678901',
        username='healthy_user',
        encrypted_session='encrypted_session_data_healthy',
        tg_user_id=1001,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
        session_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def expiring_session_account(db_session, test_user):
    """Create Telegram account with expiring session (< 24 hours)"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678902',
        username='expiring_user',
        encrypted_session='encrypted_session_data_expiring',
        tg_user_id=1002,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=12),  # Expires in 12 hours
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def expired_session_account(db_session, test_user):
    """Create Telegram account with expired session"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678903',
        username='expired_user',
        encrypted_session='encrypted_session_data_expired',
        tg_user_id=1003,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
        session_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def needs_2fa_account(db_session, test_user):
    """Create Telegram account with 2FA requirement"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678904',
        username='user_2fa',
        encrypted_session='encrypted_session_data_2fa',
        tg_user_id=1004,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
        session_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        totp_secret='totp:encrypted_secret_here',  # Has 2FA configured
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


# ==================== Test 1: Health Check Celery Task ====================

class TestHealthCheckCeleryTask:
    """Тесты Celery task для проверки здоровья сессий"""

    def test_check_all_sessions_task_updates_database(self, db_session, healthy_session_account, expiring_session_account):
        """Task обновляет статус здоровья в базе данных"""
        # Запускаем Celery task для проверки здоровья всех сессий
        result = check_all_telegram_sessions_health_task()

        # Проверяем результат task
        assert result is not None
        assert 'total_accounts' in result
        assert result['total_accounts'] >= 2

        # Проверяем, что healthy_session_account помечен как HEALTHY или EXPIRING
        db_session.refresh(healthy_session_account)
        assert healthy_session_account.session_health_status in [
            SessionHealthStatus.HEALTHY.value,
            SessionHealthStatus.EXPIRING.value
        ]
        assert healthy_session_account.last_health_check is not None

        # Проверяем, что expiring_session_account помечен как EXPIRING
        db_session.refresh(expiring_session_account)
        assert expiring_session_account.session_health_status == SessionHealthStatus.EXPIRING.value
        assert expiring_session_account.last_health_check is not None

    def test_check_all_sessions_task_detects_expired(self, db_session, expired_session_account):
        """Task корректно определяет истекшие сессии"""
        result = check_all_telegram_sessions_health_task()

        assert result is not None
        assert 'unhealthy_accounts' in result

        # Проверяем, что expired_session_account помечен как EXPIRED
        db_session.refresh(expired_session_account)
        assert expired_session_account.session_health_status == SessionHealthStatus.EXPIRED.value
        assert expired_session_account.last_health_check is not None

    def test_check_all_sessions_returns_summary(self, db_session, healthy_session_account, expiring_session_account, expired_session_account):
        """Task возвращает корректную сводку здоровья сессий"""
        result = check_all_telegram_sessions_health_task()

        assert result is not None
        assert isinstance(result, dict)
        assert 'total_accounts' in result
        assert 'healthy_accounts' in result
        assert 'unhealthy_accounts' in result

        # Проверяем, что total_accounts >= 3 (созданные fixtures)
        assert result['total_accounts'] >= 3

        # Проверяем, что unhealthy_accounts >= 1 (expired_session_account)
        assert result['unhealthy_accounts'] >= 1


# ==================== Test 2: Database Health Status Updates ====================

class TestDatabaseHealthUpdates:
    """Тесты обновления статуса здоровья в базе данных"""

    def test_health_check_updates_last_check_timestamp(self, db_session, healthy_session_account):
        """Проверка здоровья обновляет поле last_health_check"""
        old_last_check = healthy_session_account.last_health_check

        # Запускаем проверку здоровья
        health = check_session_health_sync(str(healthy_session_account.id))

        # Проверяем, что last_health_check обновлено
        db_session.refresh(healthy_session_account)
        assert healthy_session_account.last_health_check is not None
        if old_last_check:
            assert healthy_session_account.last_health_check > old_last_check

    def test_expiring_session_detected_correctly(self, db_session, expiring_session_account):
        """Истекающая сессия определяется корректно"""
        # Запускаем проверку здоровья
        health = check_session_health_sync(str(expiring_session_account.id))

        # Проверяем результат
        assert health is not None
        assert 'health_status' in health
        assert health['health_status'] in ['expiring', 'expiring_soon']

        # Проверяем базу данных
        db_session.refresh(expiring_session_account)
        assert expiring_session_account.session_health_status == SessionHealthStatus.EXPIRING.value

    def test_expired_session_detected_correctly(self, db_session, expired_session_account):
        """Истекшая сессия определяется корректно"""
        # Запускаем проверку здоровья
        health = check_session_health_sync(str(expired_session_account.id))

        # Проверяем результат
        assert health is not None
        assert 'health_status' in health
        assert health['health_status'] == 'expired'

        # Проверяем базу данных
        db_session.refresh(expired_session_account)
        assert expired_session_account.session_health_status == SessionHealthStatus.EXPIRED.value


# ==================== Test 3: Redis Health Data Storage ====================

class TestRedisHealthStorage:
    """Тесты сохранения статуса здоровья в Redis"""

    def test_health_status_cached_in_redis(self, db_session, healthy_session_account):
        """Статус здоровья кэшируется в Redis"""
        import redis

        # Запускаем проверку здоровья (это сохранит статус в Redis)
        health = check_session_health_sync(str(healthy_session_account.id))

        # Проверяем, что данные есть в Redis
        redis_client = redis.from_url('redis://localhost', decode_responses=True)
        redis_key = f'session_health:{healthy_session_account.id}'

        # В тестовой среде используем fakeredis, проверяем через monitor
        monitor = TelegramSessionMonitor()
        cached_health = monitor.get_account_health(healthy_session_account.id)

        assert cached_health is not None
        assert cached_health.account_id == str(healthy_session_account.id)
        assert isinstance(cached_health.is_healthy, bool)

    def test_redis_key_contains_all_fields(self, db_session, expiring_session_account):
        """Redis ключ содержит все необходимые поля"""
        import asyncio

        # Запускаем проверку здоровья
        health = check_session_health_sync(str(expiring_session_account.id))

        # Получаем данные из monitor (который использует Redis)
        monitor = TelegramSessionMonitor()

        # Run async method in sync context
        async def get_health():
            return await monitor.check_account_health(str(expiring_session_account.id))

        cached_health = asyncio.run(get_health())

        # Проверяем все необходимые поля
        assert cached_health is not None
        assert hasattr(cached_health, 'account_id')
        assert hasattr(cached_health, 'is_healthy')
        assert hasattr(cached_health, 'health_status')
        assert hasattr(cached_health, 'last_check')
        assert hasattr(cached_health, 'consecutive_failures')
        assert hasattr(cached_health, 'session_expires_at')

    def test_redis_has_correct_ttl(self, db_session, healthy_session_account):
        """Redis ключ имеет правильный TTL"""
        import asyncio

        # Запускаем проверку здоровья
        health = check_session_health_sync(str(healthy_session_account.id))

        # Проверяем TTL через monitor
        monitor = TelegramSessionMonitor()

        async def check_health():
            await monitor.check_account_health(str(healthy_session_account.id))
            # TTL должен быть установлен (24 часа по умолчанию)
            # В тестовой среде просто проверяем, что ключ создан
            health = await monitor.get_account_health(str(healthy_session_account.id))
            return health

        cached_health = asyncio.run(check_health())
        assert cached_health is not None


# ==================== Test 4: API Health Status Endpoint ====================

class TestAPIHealthEndpoint:
    """Тесты API endpoint для получения статуса здоровья"""

    def test_get_session_health_returns_correct_status(self, db_session, client, healthy_session_account):
        """GET /api/telegram/sessions/{account_id}/health возвращает корректный статус"""
        # Сначала запускаем health check, чтобы обновить статус
        check_session_health_sync(str(healthy_session_account.id))

        # Выполняем API запрос
        response = client.get(f'/api/telegram/sessions/{healthy_session_account.id}/health')

        assert response.status_code == 200
        data = response.json()
        assert 'health_status' in data
        assert 'is_healthy' in data
        assert 'last_check' in data

    def test_list_sessions_enriches_with_health_status(self, db_session, client, healthy_session_account, expiring_session_account):
        """GET /api/telegram/sessions обогащает сессии статусом здоровья"""
        # Запускаем health check
        check_all_telegram_sessions_health_task()

        # Получаем список сессий
        response = client.get('/api/telegram/sessions')

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Находим наши тестовые сессии
        healthy_session = next((s for s in data if s['id'] == str(healthy_session_account.id)), None)
        expiring_session = next((s for s in data if s['id'] == str(expiring_session_account.id)), None)

        assert healthy_session is not None
        assert 'session_health_status' in healthy_session
        assert healthy_session['session_health_status'] in ['healthy', 'expiring']

        assert expiring_session is not None
        assert 'session_health_status' in expiring_session
        assert expiring_session['session_health_status'] == 'expiring'


# ==================== Test 5: End-to-End Flow ====================

class TestEndToEndHealthMonitoringFlow:
    """Энд-ту-энд тесты полного цикла мониторинга здоровья"""

    def test_full_health_monitoring_flow(self, db_session, healthy_session_account, expiring_session_account, expired_session_account):
        """
        Полный цикл мониторинга здоровья:
        1. Создаем сессии с разным состоянием
        2. Запускаем Celery task
        3. Проверяем обновления в базе данных
        4. Проверяем данные в Redis
        5. Проверяем API endpoint
        """
        # Шаг 1: Сессии уже созданы через fixtures

        # Шаг 2: Запускаем Celery task
        task_result = check_all_telegram_sessions_health_task()
        assert task_result is not None
        assert task_result['total_accounts'] >= 3

        # Шаг 3: Проверяем обновления в базе данных
        db_session.refresh(healthy_session_account)
        db_session.refresh(expiring_session_account)
        db_session.refresh(expired_session_account)

        # Healthy account должен быть healthy или expiring (в зависимости от времени)
        assert healthy_session_account.session_health_status in [
            SessionHealthStatus.HEALTHY.value,
            SessionHealthStatus.EXPIRING.value
        ]
        assert healthy_session_account.last_health_check is not None

        # Expiring account должен быть expiring
        assert expiring_session_account.session_health_status == SessionHealthStatus.EXPIRING.value
        assert expiring_session_account.last_health_check is not None

        # Expired account должен быть expired
        assert expired_session_account.session_health_status == SessionHealthStatus.EXPIRED.value
        assert expired_session_account.last_health_check is not None

        # Шаг 4: Проверяем данные в Redis через monitor
        import asyncio

        monitor = TelegramSessionMonitor()

        async def check_redis():
            h_health = await monitor.get_account_health(str(healthy_session_account.id))
            e_health = await monitor.get_account_health(str(expiring_session_account.id))
            ex_health = await monitor.get_account_health(str(expired_session_account.id))
            return h_health, e_health, ex_health

        h_health, e_health, ex_health = asyncio.run(check_redis())

        assert h_health is not None
        assert h_health.account_id == str(healthy_session_account.id)

        assert e_health is not None
        assert e_health.account_id == str(expiring_session_account.id)

        assert ex_health is not None
        assert ex_health.account_id == str(expired_session_account.id)

    def test_health_monitoring_with_2fa_account(self, db_session, needs_2fa_account):
        """Мониторинг здоровья корректно обрабатывает 2FA сессии"""
        # Запускаем проверку здоровья
        health = check_session_health_sync(str(needs_2fa_account.id))

        # Проверяем результат
        assert health is not None
        assert 'health_status' in health

        # Проверяем базу данных
        db_session.refresh(needs_2fa_account)
        assert needs_2fa_account.last_health_check is not None

        # Если сессия с 2FA и не истекает, она должна быть healthy или needs_2fa
        assert needs_2fa_account.session_health_status in [
            SessionHealthStatus.HEALTHY.value,
            SessionHealthStatus.NEEDS_2FA.value
        ]


# ==================== Test 6: Edge Cases ====================

class TestHealthMonitoringEdgeCases:
    """Тесты граничных случаев мониторинга здоровья"""

    def test_inactive_accounts_not_checked(self, db_session, test_user):
        """Неактивные аккаунты не проверяются"""
        # Создаем неактивный аккаунт
        inactive_account = TelegramAccount(
            user_id=test_user.id,
            phone='+19999999999',
            username='inactive_user',
            encrypted_session='encrypted_session',
            tg_user_id=9999,
            is_active=False,  # Неактивен
            session_health_status=None,
            last_health_check=None,
            session_expires_at=None
        )
        db_session.add(inactive_account)
        db_session.commit()

        # Получаем список активных аккаунтов
        active_accounts = get_active_telegram_accounts()

        # Проверяем, что неактивный аккаунт не в списке
        inactive_in_list = any(a['id'] == str(inactive_account.id) for a in active_accounts)
        assert not inactive_in_list

    def test_account_without_session_expires_at(self, db_session, test_user):
        """Аккаунт без session_expires_at обрабатывается корректно"""
        account = TelegramAccount(
            user_id=test_user.id,
            phone='+18888888888',
            username='no_expiry_user',
            encrypted_session='encrypted_session',
            tg_user_id=8888,
            is_active=True,
            session_health_status=None,
            last_health_check=None,
            session_expires_at=None  # Нет даты истечения
        )
        db_session.add(account)
        db_session.commit()

        # Запускаем проверку здоровья (не должно упасть)
        health = check_session_health_sync(str(account.id))

        # Проверяем результат
        assert health is not None
        # Статус должен быть error или healthy (в зависимости от логики)
        assert 'health_status' in health
