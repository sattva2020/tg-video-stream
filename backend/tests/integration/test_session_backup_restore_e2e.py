"""
Integration Tests: Telegram Session Backup and Restore End-to-End
Тестируем полный цикл резервного копирования и восстановления Telegram сессий

Coverage Target: End-to-end backup and restore flow testing

Тесты проверяют:
1. Создание encrypted backup файлов через Celery tasks
2. Проверка шифрования backup файлов
3. Формат и структура backup данных
4. Восстановление сессии из backup (с имитацией недостающей функции)
5. Валидация целостности backup файлов
6. Обработка ошибок при backup/restore
7. Восстановление с TOTP секретами

Примечание: В текущей реализации backup_single_session_sync() создает .enc файлы
с encrypted JSON, но restore_session() в TelegramSessionService работает только
с .session файлами (plain text). Эти тесты демонстрируют необходимость создания
restore функции для .enc файлов.
"""
import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
import tempfile
import shutil

from src.models.user import User
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.tasks.telegram_session_health import (
    backup_single_session_sync,
    backup_all_sessions_sync,
    backup_all_sessions_task,
    backup_single_session_task,
)
from src.services.telegram_session_service import (
    get_telegram_session_service,
    TelegramSessionService
)
from src.services.encryption import encryption_service
from src.config import settings


@pytest.fixture
def test_user(db_session):
    """Create test user for Telegram accounts"""
    user = User(
        email='backup_restore_test@example.com',
        hashed_password='test_hash',
        role='admin',
        status='approved'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def backup_test_account(db_session, test_user):
    """Create Telegram account with session for backup testing"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+98765432101',
        username='backup_test_user',
        encrypted_session=encryption_service.encrypt('test_session_string_data'),
        tg_user_id=9001,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=15),
        session_expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24,
        totp_secret=encryption_service.encrypt_totp_secret('JBSWY3DPEHPK3PXP')  # Base32 test secret
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def backup_test_account_no_2fa(db_session, test_user):
    """Create Telegram account without 2FA for backup testing"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+98765432102',
        username='backup_test_user_no_2fa',
        encrypted_session=encryption_service.encrypt('test_session_string_data_no_2fa'),
        tg_user_id=9002,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(minutes=15),
        session_expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24,
        totp_secret=None
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def temp_backup_dir():
    """Create temporary directory for backup tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestBackupFileCreation:
    """Тесты создания backup файлов"""

    def test_backup_single_session_creates_file(self, backup_test_account, temp_backup_dir):
        """Проверяет, что backup_single_session_sync создает файл"""
        # Override settings to use temp directory
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))

            assert result['success'] is True
            assert 'backup_path' in result
            assert result['account_id'] == str(backup_test_account.id)

            # Verify file exists
            backup_path = Path(result['backup_path'])
            assert backup_path.exists()
            assert backup_path.is_file()

            # Verify file extension
            assert backup_path.suffix == '.enc'

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_backup_file_naming_convention(self, backup_test_account, temp_backup_dir):
        """Проверяет формат имени файла: telegram_session_{account_id}_{timestamp}.enc"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))

            backup_path = Path(result['backup_path'])
            filename = backup_path.name

            # Check format: telegram_session_{account_id}_{timestamp}.enc
            assert filename.startswith('telegram_session_')
            assert str(backup_test_account.id) in filename
            assert filename.endswith('.enc')

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_backup_includes_metadata(self, backup_test_account, temp_backup_dir):
        """Проверяет, что backup содержит метаданные"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))

            # Verify returned metadata
            assert 'phone' in result
            assert 'username' in result
            assert 'file_size_bytes' in result
            assert 'created_at' in result

            assert result['phone'] == backup_test_account.phone
            assert result['username'] == backup_test_account.username
            assert result['file_size_bytes'] > 0

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestBackupEncryption:
    """Тесты шифрования backup файлов"""

    def test_backup_file_is_encrypted(self, backup_test_account, temp_backup_dir):
        """Проверяет, что backup файл зашифрован (не читается как plain text)"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(result['backup_path'])

            # Read file content
            with open(backup_path, 'rb') as f:
                content = f.read()

            # Content should not be plain JSON (should be encrypted)
            # Encrypted content starts with "gAAAA" (Fernet prefix)
            encrypted_str = content.decode('utf-8')
            assert encrypted_str.startswith('gAAAA')

            # Try to parse as JSON - should fail
            try:
                json.loads(encrypted_str)
                assert False, "File content should be encrypted, not plain JSON"
            except json.JSONDecodeError:
                # Expected - content is encrypted
                pass

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_backup_can_be_decrypted(self, backup_test_account, temp_backup_dir):
        """Проверяет, что backup может быть расшифрован с помощью EncryptionService"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(result['backup_path'])

            # Read and decrypt
            with open(backup_path, 'rb') as f:
                encrypted_content = f.read().decode('utf-8')

            decrypted_json = encryption_service.decrypt(encrypted_content)
            backup_data = json.loads(decrypted_json)

            # Verify structure
            assert 'account_id' in backup_data
            assert 'phone' in backup_data
            assert 'encrypted_session' in backup_data
            assert 'totp_secret' in backup_data
            assert 'created_at' in backup_data

            # Verify data matches
            assert backup_data['account_id'] == str(backup_test_account.id)
            assert backup_data['phone'] == backup_test_account.phone

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestBackupDataFormat:
    """Тесты формата данных в backup"""

    def test_backup_contains_all_required_fields(self, backup_test_account, temp_backup_dir):
        """Проверяет наличие всех обязательных полей в backup"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(result['backup_path'])

            with open(backup_path, 'rb') as f:
                encrypted_content = f.read().decode('utf-8')

            decrypted_json = encryption_service.decrypt(encrypted_content)
            backup_data = json.loads(decrypted_json)

            # Required fields according to spec
            required_fields = [
                'account_id',
                'phone',
                'username',
                'encrypted_session',
                'totp_secret',
                'created_at',
                'session_expires_at',
                'health_status'
            ]

            for field in required_fields:
                assert field in backup_data, f"Missing required field: {field}"

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_backup_preserves_totp_secret(self, backup_test_account, temp_backup_dir):
        """Проверяет, что TOTP секрет сохраняется в backup"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(result['backup_path'])

            with open(backup_path, 'rb') as f:
                encrypted_content = f.read().decode('utf-8')

            decrypted_json = encryption_service.decrypt(encrypted_content)
            backup_data = json.loads(decrypted_json)

            # TOTP secret should be present and encrypted
            assert backup_data['totp_secret'] is not None
            assert backup_data['totp_secret'] != ''

            # Should be decryptable as TOTP secret
            decrypted_totp = encryption_service.decrypt_totp_secret(backup_data['totp_secret'])
            assert decrypted_totp == 'JBSWY3DPEHPK3PXP'

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestRestoreFromBackup:
    """
    Тесты восстановления из backup.

    ПРИМЕЧАНИЕ: restore_session() в TelegramSessionService работает только
    с .session файлами (plain text), а не с .enc файлами (encrypted JSON).
    Эти тесты используют вспомогательную функцию для демонстрации того,
    как должен работать restore из .enc файлов.
    """

    def _restore_from_encrypted_backup(self, backup_file_path: Path, account_id: str, db: Session) -> TelegramAccount:
        """
        Вспомогательная функция для восстановления из encrypted .enc backup.

        Эта функция демонстрирует, как должна работать restore для .enc файлов.
        В продакшене эта логика должна быть реализована в TelegramSessionService.restore_session().
        """
        # Read and decrypt backup
        with open(backup_file_path, 'rb') as f:
            encrypted_content = f.read().decode('utf-8')

        decrypted_json = encryption_service.decrypt(encrypted_content)
        backup_data = json.loads(decrypted_json)

        # Restore to account
        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Restore fields from backup
        account.encrypted_session = backup_data['encrypted_session']
        account.totp_secret = backup_data['totp_secret']
        account.session_expires_at = datetime.fromisoformat(backup_data['session_expires_at']) if backup_data['session_expires_at'] else None
        account.session_health_status = SessionHealthStatus.HEALTHY.value

        db.commit()
        db.refresh(account)

        return account

    def test_restore_session_from_backup(self, backup_test_account, temp_backup_dir, db_session):
        """Проверяет восстановление сессии из backup файла"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Create backup
            backup_result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(backup_result['backup_path'])

            # Simulate session loss: clear encrypted_session and totp_secret
            backup_test_account.encrypted_session = None
            backup_test_account.totp_secret = None
            db_session.commit()

            # Verify session is lost
            assert backup_test_account.encrypted_session is None
            assert backup_test_account.totp_secret is None

            # Restore from backup
            restored_account = self._restore_from_encrypted_backup(
                backup_path,
                str(backup_test_account.id),
                db_session
            )

            # Verify session restored
            assert restored_account.encrypted_session is not None
            assert restored_account.totp_secret is not None

            # Verify restored data matches backup
            backup_test_account_original_encrypted = 'test_session_string_data'  # Original value
            restored_session = encryption_service.decrypt(restored_account.encrypted_session)
            assert restored_session == backup_test_account_original_encrypted

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_restore_preserves_totp_secret(self, backup_test_account, temp_backup_dir, db_session):
        """Проверяет, что TOTP секрет восстанавливается корректно"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Create backup
            backup_result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(backup_result['backup_path'])

            # Simulate session loss
            backup_test_account.totp_secret = None
            db_session.commit()

            # Restore
            restored_account = self._restore_from_encrypted_backup(
                backup_path,
                str(backup_test_account.id),
                db_session
            )

            # Verify TOTP restored
            assert restored_account.totp_secret is not None

            # Verify TOTP is valid
            decrypted_totp = encryption_service.decrypt_totp_secret(restored_account.totp_secret)
            assert decrypted_totp == 'JBSWY3DPEHPK3PXP'

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path

    def test_restore_updates_health_status(self, backup_test_account, temp_backup_dir, db_session):
        """Проверяет, что после restore статус здоровья становится HEALTHY"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Create backup
            backup_result = backup_single_session_sync(str(backup_test_account.id))
            backup_path = Path(backup_result['backup_path'])

            # Set status to EXPIRED
            backup_test_account.session_health_status = SessionHealthStatus.EXPIRED.value
            db_session.commit()

            # Restore
            restored_account = self._restore_from_encrypted_backup(
                backup_path,
                str(backup_test_account.id),
                db_session
            )

            # Verify status updated to HEALTHY
            assert restored_account.session_health_status == SessionHealthStatus.HEALTHY.value

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestBackupAllSessions:
    """Тесты массового backup всех сессий"""

    def test_backup_all_sessions(self, backup_test_account, backup_test_account_no_2fa, temp_backup_dir):
        """Проверяет создание backup для всех активных сессий"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            result = backup_all_sessions_sync()

            assert result['success'] is True
            assert 'total_sessions' in result
            assert 'backed_up' in result
            assert result['total_sessions'] >= 2  # At least our test accounts

            # Verify backup files created
            backup_dir = Path(temp_backup_dir)
            backup_files = list(backup_dir.glob('*.enc'))
            assert len(backup_files) >= 2

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestBackupErrorHandling:
    """Тесты обработки ошибок при backup"""

    def test_backup_nonexistent_account(self, db_session):
        """Проверяет обработку несуществующего аккаунта"""
        fake_id = uuid.uuid4()

        result = backup_single_session_sync(str(fake_id))

        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    def test_backup_with_invalid_session_data(self, db_session, test_user, temp_backup_dir):
        """Проверяет обработку аккаунта с невалидными данными сессии"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Create account with invalid encrypted_session (can't be decrypted)
            account = TelegramAccount(
                user_id=test_user.id,
                phone='+98765432103',
                username='invalid_session_user',
                encrypted_session='invalid_encrypted_data_not_base64',
                tg_user_id=9003,
                is_active=True,
                session_health_status=SessionHealthStatus.ERROR.value
            )
            db_session.add(account)
            db_session.commit()

            # Backup should handle error gracefully
            result = backup_single_session_sync(str(account.id))

            # May succeed or fail depending on encryption validation
            # Important: shouldn't crash
            assert 'success' in result

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestRestoreErrorHandling:
    """Тесты обработки ошибок при restore"""

    def _restore_from_encrypted_backup(self, backup_file_path: Path, account_id: str, db: Session) -> TelegramAccount:
        """Helper function for restore tests"""
        with open(backup_file_path, 'rb') as f:
            encrypted_content = f.read().decode('utf-8')

        decrypted_json = encryption_service.decrypt(encrypted_content)
        backup_data = json.loads(decrypted_json)

        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        account.encrypted_session = backup_data['encrypted_session']
        account.totp_secret = backup_data['totp_secret']
        db.commit()
        db.refresh(account)

        return account

    def test_restore_from_nonexistent_file(self, backup_test_account, db_session):
        """Проверяет обработку несуществующего backup файла"""
        temp_dir = tempfile.mkdtemp()
        try:
            fake_backup_path = Path(temp_dir) / 'nonexistent_backup.enc'

            with pytest.raises(FileNotFoundError):
                self._restore_from_encrypted_backup(fake_backup_path, str(backup_test_account.id), db_session)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_restore_with_corrupted_backup(self, backup_test_account, temp_backup_dir, db_session):
        """Проверяет обработку поврежденного backup файла"""
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Create corrupted backup file
            corrupted_path = Path(temp_backup_dir) / 'corrupted.enc'
            with open(corrupted_path, 'wb') as f:
                f.write(b'corrupted_data_not_valid_fernet')

            # Should raise error when trying to decrypt
            with pytest.raises(Exception):
                self._restore_from_encrypted_backup(corrupted_path, str(backup_test_account.id), db_session)

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path


class TestEndToEndBackupRestoreFlow:
    """End-to-end тесты полного цикла backup/restore"""

    def _restore_from_encrypted_backup(self, backup_file_path: Path, account_id: str, db: Session) -> TelegramAccount:
        """Helper function for E2E tests"""
        with open(backup_file_path, 'rb') as f:
            encrypted_content = f.read().decode('utf-8')

        decrypted_json = encryption_service.decrypt(encrypted_content)
        backup_data = json.loads(decrypted_json)

        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        account.encrypted_session = backup_data['encrypted_session']
        account.totp_secret = backup_data['totp_secret']
        account.session_expires_at = datetime.fromisoformat(backup_data['session_expires_at']) if backup_data['session_expires_at'] else None
        account.session_health_status = SessionHealthStatus.HEALTHY.value
        account.last_refreshed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(account)

        return account

    def test_full_backup_restore_cycle(self, backup_test_account, temp_backup_dir, db_session):
        """
        Полный тест backup/restore цикла:

        Verification Steps:
        1. Trigger backup session task for test account
        2. Verify backup file created in SESSION_BACKUP_PATH
        3. Verify file is encrypted (cannot read as plain text)
        4. Delete session from database (simulate loss)
        5. Trigger restore task with backup file path
        6. Verify session restored to TelegramAccount
        7. Verify Pyrogram client can connect with restored session (simulated)
        """
        original_backup_path = settings.SESSION_BACKUP_PATH
        settings.SESSION_BACKUP_PATH = temp_backup_dir

        try:
            # Step 1: Trigger backup
            backup_result = backup_single_session_sync(str(backup_test_account.id))
            assert backup_result['success'] is True

            # Step 2: Verify backup file created
            backup_path = Path(backup_result['backup_path'])
            assert backup_path.exists()
            assert backup_path.parent == Path(temp_backup_dir)

            # Step 3: Verify file is encrypted
            with open(backup_path, 'rb') as f:
                content = f.read().decode('utf-8')
            assert content.startswith('gAAAA')  # Fernet prefix
            with pytest.raises(json.JSONDecodeError):
                json.loads(content)  # Should not be plain JSON

            # Step 4: Simulate session loss
            original_session = backup_test_account.encrypted_session
            original_totp = backup_test_account.totp_secret
            backup_test_account.encrypted_session = None
            backup_test_account.totp_secret = None
            db_session.commit()

            assert backup_test_account.encrypted_session is None

            # Step 5: Restore from backup
            restored_account = self._restore_from_encrypted_backup(
                backup_path,
                str(backup_test_account.id),
                db_session
            )

            # Step 6: Verify session restored
            assert restored_account.encrypted_session is not None
            assert restored_account.totp_secret is not None
            assert restored_account.encrypted_session == original_session
            assert restored_account.totp_secret == original_totp

            # Step 7: Verify Pyrogram can connect (simulated - check session data is valid)
            # In real scenario, would create Pyrogram client and attempt connection
            decrypted_session = encryption_service.decrypt(restored_account.encrypted_session)
            assert decrypted_session == 'test_session_string_data'  # Valid session string

            # Verify TOTP can generate codes
            decrypted_totp = encryption_service.decrypt_totp_secret(restored_account.totp_secret)
            assert decrypted_totp == 'JBSWY3DPEHPK3PXP'  # Valid base32

        finally:
            settings.SESSION_BACKUP_PATH = original_backup_path
