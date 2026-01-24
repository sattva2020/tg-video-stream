# Session Refresh with 2FA - E2E Tests

## Overview

Comprehensive end-to-end test suite for automatic session refresh with 2FA code flow. Tests verify the complete workflow from TOTP secret storage to session refresh execution.

## Test Files

### 1. `test_session_refresh_with_2fa_e2e.py` (725 lines)

Main test file with 7 test classes covering all aspects of session refresh with 2FA.

#### Test Classes:

**TestTOTPSecretStorage** (5 tests)
- TOTP secret encryption format validation
- Decryption correctness
- Invalid format handling
- Empty secret rejection
- Database encryption verification

**TestSessionRefreshDetection** (3 tests)
- Expiring session detection
- Healthy session exclusion
- Inactive account filtering

**TestTOTPCodeGeneration** (4 tests)
- Code generation from encrypted storage
- TOTP validation
- Error handling without 2FA secret
- Time-based code changes

**TestSessionRefreshWith2FA** (3 tests)
- Complete refresh flow with 2FA code
- Refresh without 2FA
- Healthy session skip logic

**TestRefreshCeleryTask** (3 tests)
- Task processes expiring sessions
- Handles no expiring sessions
- Multiple session processing

**TestRefreshErrorHandling** (3 tests)
- Invalid encrypted TOTP handling
- Missing account errors
- Database error handling

**TestEndToEndRefreshFlow** (1 test)
- Complete E2E flow matching all verification steps

### 2. `verify_session_refresh_with_2fa.py` (316 lines)

Standalone verification script that can run without pytest:
```bash
python tests/integration/verify_session_refresh_with_2fa.py
```

Performs all 7 verification steps:
1. ✅ Setup Telegram account with TOTP secret (encrypt and store)
2. ✅ Mark session as expiring soon (session_expires_at = now + 2 hours)
3. ✅ Trigger refresh task manually
4. ✅ Verify task retrieves TOTP code from encrypted storage
5. ✅ Verify Pyrogram client refreshes session successfully (mocked)
6. ✅ Verify TelegramAccount.last_refreshed_at updated
7. ✅ Verify session_expires_at extended

### 3. `validate_refresh_test_structure.py` (200 lines)

Test structure validation script:
```bash
python tests/integration/validate_refresh_test_structure.py
```

Validates:
- All required imports present
- All test classes exist
- All test methods implemented
- All fixtures available
- Verification steps coverage

## Fixtures

### `test_user`
Creates admin user for testing.

### `totp_secret`
Generates random base32 TOTP secret using pyotp.

### `expiring_session_with_2fa`
Creates Telegram account with:
- Session expiring in 2 hours
- Encrypted TOTP secret stored
- Auto-refresh enabled

### `expiring_session_without_2fa`
Creates account without 2FA for comparison testing.

### `healthy_session_with_2fa`
Creates healthy account (expires in 7 days) to verify no unnecessary refresh.

## Verification Steps

### Step 1: Setup TOTP Secret
```python
totp_secret = pyotp.random_base32()
encrypted_totp = encryption_service.encrypt_totp_secret(totp_secret)
```
✅ Secret is encrypted with Fernet + TOTP prefix
✅ Stored in `TelegramAccount.totp_secret` field

### Step 2: Mark Session Expiring
```python
session_expires_at = now + timedelta(hours=2)
session_health_status = SessionHealthStatus.EXPIRING
```
✅ Session marked as expiring soon
✅ Auto-refresh enabled

### Step 3: Trigger Refresh Task
```python
result = refresh_expiring_sessions_sync()
```
✅ Task detects expiring session
✅ Calls `TelegramSessionService.refresh_session()`

### Step 4: Retrieve TOTP Code
```python
code = service.generate_2fa_code(db, account_id)
# Decrypts totp_secret
# Generates current TOTP code
```
✅ Encrypted secret decrypted
✅ 6-digit TOTP code generated

### Step 5: Pyrogram Client Refresh
```python
# Mocked in tests (no real Telegram client)
# In production: Integration with Pyrogram API
```
✅ Pyrogram integration point identified in `refresh_session()`
✅ TOTP code would be provided to client

### Step 6: Update last_refreshed_at
```python
account.last_refreshed_at = datetime.utcnow()
```
✅ Timestamp updated after successful refresh

### Step 7: Extend session_expires_at
```python
account.session_expires_at = now + timedelta(days=30)
```
✅ Session expiration extended by 30 days
✅ Health status updated to HEALTHY

## Running Tests

### With pytest:
```bash
cd backend
pytest tests/integration/test_session_refresh_with_2fa_e2e.py -v
```

### Run specific test class:
```bash
pytest tests/integration/test_session_refresh_with_2fa_e2e.py::TestTOTPSecretStorage -v
```

### Run E2E test only:
```bash
pytest tests/integration/test_session_refresh_with_2fa_e2e.py::TestEndToEndRefreshFlow -v
```

### Standalone verification:
```bash
python tests/integration/verify_session_refresh_with_2fa.py
```

## Pattern Compliance

Follows patterns from:
- ✅ `test_stream_recovery_e2e.py` - Test structure, fixtures, assertions
- ✅ `test_session_health_monitoring_e2e.py` - Session health testing approach
- ✅ `conftest.py` - Fixture setup, database session handling
- ✅ `telegram_session_service.py` - Service integration patterns
- ✅ `encryption.py` - TOTP encryption patterns

## Mock Strategy

Since we don't have access to real Telegram client in tests:
- Pyrogram client interactions are mocked using `unittest.mock.Mock`
- TOTP generation uses real `pyotp` library
- Database operations use real PostgreSQL (via test fixtures)
- Redis operations use `fakeredis` for caching

## Test Coverage

- **Encryption**: TOTP secret encryption/decryption
- **Detection**: Expiring session identification
- **Code Generation**: 2FA code from encrypted storage
- **Refresh Flow**: Complete refresh with 2FA
- **Task Execution**: Celery task integration
- **Error Handling**: Invalid secrets, missing accounts, DB errors
- **E2E**: Complete workflow from setup to completion

## Quality Checklist

- ✅ Follows patterns from reference files
- ✅ No console.log/print debugging statements (uses logging)
- ✅ Error handling in place (try/except blocks, assertions)
- ✅ Comprehensive test coverage (7 classes, 22 tests)
- ✅ Fixtures for test data isolation
- ✅ Mock strategy for external dependencies
- ✅ Standalone verification script included
- ✅ Structure validation script included

## Notes

- Tests require pytest, fakeredis, and all project dependencies
- Verification script can run without pytest
- Database connection required for full test execution
- Pyrogram client is mocked (no real Telegram API calls)
- TOTP codes are real (using pyotp) but timestamp-dependent
- Test data is cleaned up after each test via fixtures
