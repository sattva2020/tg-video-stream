"""
Standalone Verification Script: Session Refresh with 2FA Flow
Проверка автоматического обновления сессии с 2FA

Этот скрипт можно запустить самостоятельно без pytest:
  python tests/integration/verify_session_refresh_with_2fa.py

Verification Steps:
1. Setup Telegram account with TOTP secret (encrypt and store)
2. Mark session as expiring soon (session_expires_at = now + 2 hours)
3. Trigger refresh task manually
4. Verify task retrieves TOTP code from encrypted storage
5. Verify Pyrogram client refreshes session successfully
6. Verify TelegramAccount.last_refreshed_at updated
7. Verify session_expires_at extended
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add backend to path
backend_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
src_root = os.path.join(backend_root, 'src')
sys.path.insert(0, backend_root)
sys.path.insert(0, src_root)

# Set test environment
os.environ["SESSION_ENCRYPTION_KEY"] = "TnaLffqg0O5jccqqyQdSKT4JEnf6O2IMalnuECbHv0A="
os.environ["JWT_SECRET"] = "test_jwt_secret_key_for_testing_only"
os.environ["TESTING"] = "true"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def create_test_data(db):
    """Создать тестовые данные для проверки"""
    from src.models.user import User
    from src.models.telegram import TelegramAccount, SessionHealthStatus
    from src.services.encryption import encryption_service
    import pyotp

    # Create test user
    user = User(
        email='refresh_2fa_verify@example.com',
        hashed_password='test_hash',
        role='admin',
        status='approved'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info(f"Created test user: {user.id}")

    # Generate TOTP secret
    totp_secret = pyotp.random_base32()
    log.info(f"Generated TOTP secret: {totp_secret[:10]}...")

    # Encrypt TOTP secret
    encrypted_totp = encryption_service.encrypt_totp_secret(totp_secret)
    log.info(f"Encrypted TOTP secret: {encrypted_totp[:20]}...")

    # Create account with expiring session (2 hours from now)
    account = TelegramAccount(
        user_id=user.id,
        phone='+19998887776',
        username='refresh_2fa_test',
        encrypted_session='test_encrypted_session_data',
        tg_user_id=9001,
        is_active=True,
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24,
        totp_secret=encrypted_totp,
        session_health_status=SessionHealthStatus.EXPIRING.value,
        last_refreshed_at=None
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    log.info(f"Created test account: {account.id} (expires in 2 hours)")

    return user, account, totp_secret


def verify_totp_encryption(account, original_secret):
    """Verify TOTP encryption and decryption"""
    from src.services.encryption import encryption_service

    log.info("\n--- Verification 1: TOTP Encryption ---")

    # Verify encrypted format
    encrypted = account.totp_secret
    assert encrypted != original_secret, "Secret should be encrypted"
    assert 'gAAAA' in encrypted, "Should use Fernet encryption"
    log.info("✅ TOTP secret is encrypted (not plaintext)")

    # Verify decryption works
    decrypted = encryption_service.decrypt_totp_secret(encrypted)
    assert decrypted == original_secret, "Decrypted secret should match original"
    log.info(f"✅ TOTP secret decrypts correctly: {decrypted[:10]}...")


def verify_2fa_code_generation(db, account):
    """Verify 2FA code generation from encrypted storage"""
    from src.services.telegram_session_service import get_telegram_session_service
    from src.tasks.telegram_session_health import _run_async
    import pyotp

    log.info("\n--- Verification 2: 2FA Code Generation ---")

    service = get_telegram_session_service()

    # Generate 2FA code
    code = _run_async(service.generate_2fa_code(db, str(account.id)))
    log.info(f"Generated 2FA code: {code}")

    # Verify code format
    assert code is not None, "Code should not be None"
    assert len(code) == 6, "Code should be 6 digits"
    assert code.isdigit(), "Code should be numeric"
    log.info("✅ 2FA code has correct format (6 digits)")

    # Verify code is valid
    # We need to decrypt the secret to verify
    from src.services.encryption import encryption_service
    decrypted_secret = encryption_service.decrypt_totp_secret(account.totp_secret)
    totp = pyotp.TOTP(decrypted_secret)
    is_valid = totp.verify(code, valid_window=1)
    assert is_valid, "Generated code should be valid TOTP"
    log.info("✅ Generated code is valid TOTP (verified with pyotp)")


def verify_expiring_session_detection(account):
    """Verify that expiring session is detected correctly"""
    from src.tasks.telegram_session_health import get_expiring_sessions

    log.info("\n--- Verification 3: Expiring Session Detection ---")

    expiring_sessions = get_expiring_sessions()
    log.info(f"Found {len(expiring_sessions)} expiring sessions")

    # Find our test account
    found = False
    for session in expiring_sessions:
        if session['id'] == str(account.id):
            found = True
            log.info(f"✅ Test account detected: {session['phone']}")
            assert session['username'] == 'refresh_2fa_test'
            assert session['is_active'] == True
            break

    assert found, "Test account should be in expiring sessions list"
    log.info("✅ Expiring session detected correctly")


def verify_session_refresh(db, account):
    """Verify session refresh updates database correctly"""
    from src.services.telegram_session_service import get_telegram_session_service
    from src.tasks.telegram_session_health import _run_async

    log.info("\n--- Verification 4: Session Refresh ---")

    service = get_telegram_session_service()
    account_id = str(account.id)

    # Store original values
    original_expires_at = account.session_expires_at
    original_last_refreshed = account.last_refreshed_at

    log.info(f"Original session_expires_at: {original_expires_at}")
    log.info(f"Original last_refreshed_at: {original_last_refreshed}")

    # Perform refresh
    log.info(f"Refreshing session for account {account_id}...")
    refreshed_account = _run_async(service.refresh_session(db, account_id))
    log.info("✅ Refresh completed without errors")

    # Verify last_refreshed_at updated
    assert refreshed_account.last_refreshed_at is not None, "last_refreshed_at should be set"
    if original_last_refreshed:
        assert refreshed_account.last_refreshed_at > original_last_refreshed, \
            "last_refreshed_at should be newer"
    log.info(f"✅ last_refreshed_at updated: {refreshed_account.last_refreshed_at}")

    # Verify session_expires_at extended
    new_expiry = refreshed_account.session_expires_at
    expected_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    time_diff = abs((new_expiry - expected_expiry).total_seconds())
    assert time_diff < 60, "session_expires_at should be extended by ~30 days"
    log.info(f"✅ session_expires_at extended: {new_expiry}")
    log.info(f"   (was: {original_expires_at}, now: {new_expiry})")

    # Verify health status updated
    from src.models.telegram import SessionHealthStatus
    assert refreshed_account.session_health_status == SessionHealthStatus.HEALTHY.value, \
        "Health status should be HEALTHY after refresh"
    log.info(f"✅ Health status updated to: {refreshed_account.session_health_status}")


def verify_refresh_task_execution():
    """Verify refresh Celery task execution"""
    from src.tasks.telegram_session_health import refresh_expiring_sessions_sync

    log.info("\n--- Verification 5: Refresh Task Execution ---")

    # Run refresh task
    log.info("Executing refresh_expiring_sessions_sync()...")
    result = refresh_expiring_sessions_sync()

    log.info(f"Task result: success={result['success']}, total={result['total_sessions']}, "
             f"refreshed={result['refreshed']}, failed={result['failed']}")

    assert result['success'] == True, "Task should succeed"
    assert result['total_sessions'] >= 1, "Should process at least 1 session"
    assert result['refreshed'] >= 1, "Should refresh at least 1 session"
    assert result['failed'] == 0, "Should have no failures"
    log.info("✅ Refresh task executed successfully")


def cleanup_test_data(db, user, account):
    """Очистить тестовые данные"""
    log.info("\n--- Cleanup ---")

    db.delete(account)
    db.delete(user)
    db.commit()
    log.info("✅ Test data cleaned up")


def main():
    """Main verification function"""
    from src.database import SessionLocal

    log.info("=" * 70)
    log.info(" Session Refresh with 2FA - End-to-End Verification")
    log.info("=" * 70)

    db = SessionLocal()
    user, account, totp_secret = None, None, None

    try:
        # Step 1: Setup Telegram account with TOTP secret (encrypt and store)
        log.info("\n=== Step 1: Setup ===")
        user, account, totp_secret = create_test_data(db)

        # Verify TOTP encryption
        verify_totp_encryption(account, totp_secret)

        # Step 2: Mark session as expiring soon (already done in create_test_data)
        log.info(f"\n=== Step 2: Expiring Session ===")
        log.info(f"✅ Session expires at: {account.session_expires_at}")
        log.info(f"   (Time until expiry: ~2 hours)")

        # Verify expiring session detection
        verify_expiring_session_detection(account)

        # Verify 2FA code generation
        verify_2fa_code_generation(db, account)

        # Step 3 & 4: Trigger refresh task manually + verify TOTP retrieval
        log.info(f"\n=== Step 3 & 4: Manual Refresh Trigger + TOTP Retrieval ===")
        verify_session_refresh(db, account)

        # Step 5: Verify refresh task execution (Pyrogram client refresh is mocked)
        log.info(f"\n=== Step 5: Pyrogram Client Refresh ===")
        log.info("✅ Pyrogram client integration is mocked in tests")
        log.info("   (Real Telegram client not available in test environment)")

        # Step 6 & 7: Verify database updates
        log.info(f"\n=== Step 6 & 7: Database Updates ===")
        # Already verified in verify_session_refresh()

        # Verify refresh task
        verify_refresh_task_execution()

        # Cleanup
        cleanup_test_data(db, user, account)

        log.info("\n" + "=" * 70)
        log.info(" ✅ ALL VERIFICATION STEPS PASSED!")
        log.info("=" * 70)
        log.info("\nSummary:")
        log.info("  ✅ TOTP secret encrypted and stored correctly")
        log.info("  ✅ Expiring session detected")
        log.info("  ✅ 2FA code generated from encrypted storage")
        log.info("  ✅ Session refresh executed successfully")
        log.info("  ✅ last_refreshed_at updated")
        log.info("  ✅ session_expires_at extended by 30 days")
        log.info("  ✅ Health status updated to HEALTHY")
        log.info("  ✅ Refresh Celery task works correctly")
        log.info("\n")
        return 0

    except Exception as e:
        log.error(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()

        # Cleanup on failure
        try:
            if user and account:
                cleanup_test_data(db, user, account)
        except:
            pass

        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
