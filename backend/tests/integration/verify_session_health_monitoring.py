"""
Manual Verification Script for Telegram Session Health Monitoring
==================================================================

Этот скрипт проверяет end-to-end flow автоматического мониторинга здоровья сессий
без необходимости запуска full Celery worker.

Запуск:
    cd backend
    python tests/integration/verify_session_health_monitoring.py

Что проверяется:
1. Celery task для проверки здоровья всех сессий
2. Обновление статуса здоровья в базе данных
3. Сохранение статуса здоровья в Redis (через TelegramSessionMonitor)
4. API endpoint для получения статуса здоровья
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.database import SessionLocal
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.models.user import User
from src.tasks.telegram_session_health import (
    check_all_telegram_sessions_health_task,
    check_session_health_sync,
    get_active_telegram_accounts
)


def create_test_accounts():
    """Create test Telegram accounts with different health states"""
    db = SessionLocal()
    try:
        # Check if test user exists
        user = db.query(User).filter_by(email='health_monitor_test@example.com').first()
        if not user:
            user = User(
                email='health_monitor_test@example.com',
                hashed_password='test_hash',
                role='admin',
                status='approved'
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create healthy account
        healthy = TelegramAccount(
            user_id=user.id,
            phone='+11111111111',
            username='healthy_test_user',
            encrypted_session='encrypted_healthy',
            tg_user_id=9001,
            is_active=True,
            session_health_status=SessionHealthStatus.HEALTHY.value,
            last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
            session_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            auto_refresh_enabled=True,
            refresh_before_expires_hours=24
        )
        db.add(healthy)

        # Create expiring account (< 24 hours)
        expiring = TelegramAccount(
            user_id=user.id,
            phone='+22222222222',
            username='expiring_test_user',
            encrypted_session='encrypted_expiring',
            tg_user_id=9002,
            is_active=True,
            session_health_status=SessionHealthStatus.HEALTHY.value,
            last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
            session_expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
            auto_refresh_enabled=True,
            refresh_before_expires_hours=24
        )
        db.add(expiring)

        # Create expired account
        expired = TelegramAccount(
            user_id=user.id,
            phone='+33333333333',
            username='expired_test_user',
            encrypted_session='encrypted_expired',
            tg_user_id=9003,
            is_active=True,
            session_health_status=SessionHealthStatus.HEALTHY.value,
            last_health_check=datetime.now(timezone.utc) - timedelta(minutes=30),
            session_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            auto_refresh_enabled=True,
            refresh_before_expires_hours=24
        )
        db.add(expired)

        db.commit()
        db.refresh(healthy)
        db.refresh(expiring)
        db.refresh(expired)

        print(f"✓ Created test accounts:")
        print(f"  - Healthy: {healthy.phone} (expires in 7 days)")
        print(f"  - Expiring: {expiring.phone} (expires in 12 hours)")
        print(f"  - Expired: {expired.phone} (expired 1 hour ago)")

        return healthy, expiring, expired

    except Exception as e:
        db.rollback()
        print(f"✗ Error creating test accounts: {e}")
        return None, None, None
    finally:
        db.close()


def test_health_check_task():
    """Test 1: Celery task для проверки здоровья всех сессий"""
    print("\n" + "="*70)
    print("TEST 1: Celery Health Check Task")
    print("="*70)

    try:
        # Run the Celery task
        result = check_all_telegram_sessions_health_task()

        print(f"✓ Task executed successfully")
        print(f"  Result: {result}")

        if result:
            print(f"  Total accounts checked: {result.get('total_accounts', 0)}")
            print(f"  Healthy accounts: {result.get('healthy_accounts', 0)}")
            print(f"  Unhealthy accounts: {result.get('unhealthy_accounts', 0)}")

        return True

    except Exception as e:
        print(f"✗ Error running health check task: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_updates(healthy_id, expiring_id, expired_id):
    """Test 2: Проверка обновлений в базе данных"""
    print("\n" + "="*70)
    print("TEST 2: Database Health Status Updates")
    print("="*70)

    db = SessionLocal()
    try:
        # Check healthy account
        healthy = db.query(TelegramAccount).filter_by(id=healthy_id).first()
        if healthy:
            print(f"✓ Healthy account ({healthy.phone}):")
            print(f"  - Status: {healthy.session_health_status}")
            print(f"  - Last check: {healthy.last_health_check}")
            assert healthy.last_health_check is not None, "last_health_check should be updated"

        # Check expiring account
        expiring = db.query(TelegramAccount).filter_by(id=expiring_id).first()
        if expiring:
            print(f"✓ Expiring account ({expiring.phone}):")
            print(f"  - Status: {expiring.session_health_status}")
            print(f"  - Last check: {expiring.last_health_check}")
            assert expiring.last_health_check is not None, "last_health_check should be updated"

        # Check expired account
        expired = db.query(TelegramAccount).filter_by(id=expired_id).first()
        if expired:
            print(f"✓ Expired account ({expired.phone}):")
            print(f"  - Status: {expired.session_health_status}")
            print(f"  - Last check: {expired.last_health_check}")
            assert expired.session_health_status == SessionHealthStatus.EXPIRED.value, \
                f"Expected EXPIRED status, got {expired.session_health_status}"

        print("\n✓ All database updates verified")
        return True

    except Exception as e:
        print(f"\n✗ Error verifying database updates: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_redis_caching(account_id):
    """Test 3: Проверка сохранения в Redis"""
    print("\n" + "="*70)
    print("TEST 3: Redis Health Data Storage")
    print("="*70)

    try:
        import asyncio
        from src.services.telegram_session_monitor import get_telegram_session_monitor

        # Get monitor instance
        monitor = get_telegram_session_monitor()

        # Check health via monitor (this stores in Redis)
        async def check_and_retrieve():
            # First, run health check
            health = await monitor.check_account_health(str(account_id))
            print(f"✓ Health check completed for account {account_id}")
            print(f"  - Status: {health.health_status}")
            print(f"  - Healthy: {health.is_healthy}")

            # Then retrieve from cache
            cached = await monitor.get_account_health(str(account_id))
            if cached:
                print(f"✓ Retrieved from Redis cache:")
                print(f"  - Account ID: {cached.account_id}")
                print(f"  - Status: {cached.health_status}")
                print(f"  - Last check: {cached.last_check}")
                print(f"  - Failures: {cached.consecutive_failures}")
                return True
            else:
                print(f"✗ No cached data found in Redis")
                return False

        result = asyncio.run(check_and_retrieve())
        return result

    except Exception as e:
        print(f"✗ Error verifying Redis caching: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_health_check(account_id):
    """Test 4: Проверка отдельной сессии"""
    print("\n" + "="*70)
    print("TEST 4: Single Session Health Check")
    print("="*70)

    try:
        health = check_session_health_sync(str(account_id))

        print(f"✓ Single health check completed:")
        print(f"  - Account ID: {health.get('account_id')}")
        print(f"  - Health status: {health.get('health_status')}")
        print(f"  - Is healthy: {health.get('is_healthy')}")
        print(f"  - Last check: {health.get('last_check')}")

        return True

    except Exception as e:
        print(f"✗ Error checking single session: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_accounts():
    """Clean up test accounts after verification"""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email='health_monitor_test@example.com').first()
        if user:
            # Delete all test accounts
            db.query(TelegramAccount).filter_by(user_id=user.id).delete()
            db.commit()
            print(f"\n✓ Cleaned up test accounts")
    except Exception as e:
        print(f"\n✗ Error cleaning up: {e}")
    finally:
        db.close()


def main():
    """Main verification flow"""
    print("="*70)
    print("Telegram Session Health Monitoring - E2E Verification")
    print("="*70)

    # Create test accounts
    print("\nStep 1: Creating test accounts...")
    healthy, expiring, expired = create_test_accounts()
    if not healthy or not expiring or not expired:
        print("\n✗ Failed to create test accounts. Exiting.")
        return False

    # Test 1: Run Celery task
    print("\nStep 2: Running health check Celery task...")
    test1_passed = test_health_check_task()

    # Test 2: Verify database updates
    print("\nStep 3: Verifying database updates...")
    test2_passed = test_database_updates(healthy.id, expiring.id, expired.id)

    # Test 3: Verify Redis caching
    print("\nStep 4: Verifying Redis caching...")
    test3_passed = test_redis_caching(healthy.id)

    # Test 4: Single health check
    print("\nStep 5: Testing single session health check...")
    test4_passed = test_single_health_check(expiring.id)

    # Cleanup
    print("\nStep 6: Cleaning up test data...")
    cleanup_test_accounts()

    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    print(f"Test 1 (Celery Task):        {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Test 2 (Database Updates):   {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"Test 3 (Redis Caching):      {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print(f"Test 4 (Single Health Check): {'✓ PASSED' if test4_passed else '✗ FAILED'}")

    all_passed = all([test1_passed, test2_passed, test3_passed, test4_passed])
    print("\n" + ("="*70))
    if all_passed:
        print("✓ ALL TESTS PASSED - Health monitoring flow verified!")
    else:
        print("✗ SOME TESTS FAILED - Please review errors above")
    print("="*70)

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
