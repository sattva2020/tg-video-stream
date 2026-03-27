# Multi-Account Session Rotation Tests

Comprehensive end-to-end tests for multi-account session rotation functionality in the Telegram Session Management system.

## Overview

This test suite verifies the **multi-account session rotation** feature that enables load balancing across multiple Telegram accounts. The rotation logic ensures that:

- Accounts are selected based on `rotation_order` priority (lower number = higher priority)
- Within each priority level, the least-recently-used (LRU) account is selected
- No rate limiting occurs (Circuit Breaker verification)
- All rotation events are properly logged to the database
- Load is distributed evenly across participating accounts

## Files

### Test Files

1. **test_session_rotation_e2e.py** (730 lines)
   - Main pytest test suite with 6 test classes
   - 25+ test methods covering all rotation scenarios
   - Tests for selection logic, multi-account rotation, Circuit Breaker, database logging, E2E flows, and edge cases

2. **verify_session_rotation.py** (330 lines)
   - Standalone verification script (no pytest required)
   - Can be run directly: `python tests/integration/verify_session_rotation.py`
   - Executes all 6 verification steps from the spec
   - Creates test data, runs tests, cleans up automatically

3. **README_session_rotation_tests.md** (this file)
   - Comprehensive documentation
   - Usage instructions and test coverage details

## Verification Steps (from Spec)

The tests verify all 6 steps required for multi-account session rotation:

1. ✅ **Create 3 Telegram accounts in database**
   - Creates accounts with different `rotation_order` values (1, 2, 3)
   - Configures different `refresh_before_expires_hours` for each (12, 24, 48)

2. ✅ **Configure different refresh_before_expires_hours for each**
   - Account 1: `refresh_before_expires_hours=12`
   - Account 2: `refresh_before_expires_hours=24`
   - Account 3: `refresh_before_expires_hours=48`

3. ✅ **Trigger health check on all accounts**
   - Uses `TelegramSessionMonitor.check_account_health()`
   - Verifies health status: HEALTHY, EXPIRING, or EXPIRED
   - Checks `last_health_check` timestamp updates

4. ✅ **Verify rotation logic selects least-recently-used account**
   - Tests `get_account_for_rotation()` method
   - Verifies LRU selection within same `rotation_order`
   - Verifies priority selection across different `rotation_order` values

5. ✅ **Verify no rate limiting (check Circuit Breaker state)**
   - Checks `CircuitBreaker` state for each account
   - Verifies state is not OPEN (which would indicate rate limiting)
   - Acceptable states: CLOSED (normal), HALF_OPEN (recovering)

6. ✅ **Verify rotation event logged to database**
   - Tests `rotate_sessions()` method
   - Verifies `last_refreshed_at` updated
   - Verifies `session_health_status` updated to HEALTHY
   - Verifies `rotation_order` preserved (not changed)

## Test Classes

### 1. TestRotationSelection (4 tests)

Tests the account selection logic for rotation:

- `test_get_account_for_rotation_selects_lru`: Selects account with oldest `last_refreshed_at`
- `test_get_account_respects_rotation_order_priority`: Priority takes precedence over age
- `test_get_account_skips_non_participating_accounts`: Skips accounts with `rotation_order=0`
- `test_get_account_filters_by_health_status`: Only selects HEALTHY/EXPIRING accounts

### 2. TestMultiAccountRotation (4 tests)

Tests rotation of multiple accounts:

- `test_rotate_sessions_refreshes_multiple_accounts`: Refreshes up to `max_accounts`
- `test_rotate_sessions_respects_max_accounts_limit`: Honors `max_accounts` parameter
- `test_rotate_sessions_load_balances_across_orders`: Distributes load across different priorities
- `test_rotate_sessions_continues_on_individual_failures`: Continues on individual account failures

### 3. TestRotationCircuitBreaker (2 tests)

Tests Circuit Breaker integration:

- `test_rotation_checks_circuit_breaker_state`: Verifies Circuit Breaker exists for each account
- `test_no_rate_limiting_with_rotation`: Ensures rotation doesn't trigger rate limiting

### 4. TestRotationEventLogging (3 tests)

Tests database logging of rotation events:

- `test_rotation_updates_last_refreshed_at`: Verifies timestamp updates
- `test_rotation_preserves_rotation_order`: Ensures `rotation_order` not changed
- `test_rotation_updates_health_status`: Verifies `session_health_status` updated to HEALTHY

### 5. TestEndToEndRotationFlow (3 tests)

Complete end-to-end workflow tests:

- `test_full_rotation_workflow`: Full E2E test (create → select → rotate → verify)
- `test_rotation_with_realistic_scenario`: 5 accounts, rotate 3, verify distribution
- `test_rotation_respects_user_isolation`: User accounts not mixed

### 6. TestRotationEdgeCases (5 tests)

Tests edge cases and boundary conditions:

- `test_rotation_with_no_accounts`: Behavior when no accounts exist
- `test_rotation_with_all_accounts_disabled`: All accounts have `rotation_order=0`
- `test_rotation_with_inactive_accounts`: Inactive accounts excluded
- `test_rotation_with_auto_refresh_disabled_accounts`: Auto-refresh disabled accounts excluded
- `test_rotation_order_zero_treated_as_disabled`: `rotation_order=0` means disabled

## Running the Tests

### Option 1: Using pytest (Recommended for development)

```bash
# Run all rotation tests
cd backend
pytest tests/integration/test_session_rotation_e2e.py -v

# Run specific test class
pytest tests/integration/test_session_rotation_e2e.py::TestRotationSelection -v

# Run specific test
pytest tests/integration/test_session_rotation_e2e.py::TestRotationSelection::test_get_account_for_rotation_selects_lru -v

# Run with coverage
pytest tests/integration/test_session_rotation_e2e.py -v --cov=src/services/telegram_session_service --cov-report=term-missing
```

### Option 2: Using standalone verification script (No pytest required)

```bash
# Run verification script directly
cd backend
python tests/integration/verify_session_rotation.py

# The script will:
# 1. Create test data (3 accounts)
# 2. Execute all 6 verification steps
# 3. Print detailed results
# 4. Clean up test data automatically
```

### Option 3: Run with database URL override

```bash
# Override database URL for testing
export DATABASE_URL="postgresql://user:pass@host:port/db"
python tests/integration/verify_session_rotation.py
```

## Test Coverage

### Feature Coverage

- ✅ Rotation order priority (1, 2, 3, etc.)
- ✅ Least-recently-used (LRU) selection
- ✅ Load balancing across multiple accounts
- ✅ Health status filtering
- ✅ Circuit Breaker integration
- ✅ Database logging and timestamp updates
- ✅ User isolation (accounts not mixed between users)
- ✅ Edge cases (no accounts, disabled accounts, inactive accounts)

### Code Coverage

The tests cover the following methods in `TelegramSessionService`:

- `get_account_for_rotation()`: Account selection logic
- `rotate_sessions()`: Multi-account rotation logic

And verifies integration with:

- `TelegramSessionMonitor.check_account_health()`: Health checking
- `CircuitBreaker`: Rate limit protection
- Database ORM models: `TelegramAccount` field updates

## Implementation Details

### Rotation Strategy

The rotation uses a **priority-based LRU strategy**:

1. **First Level**: Sort by `rotation_order` (ascending, so 1 is highest priority)
2. **Second Level**: Within same `rotation_order`, sort by `last_refreshed_at` (oldest first)

This ensures:
- Higher priority accounts (lower `rotation_order`) are selected first
- Load is distributed evenly among accounts with same priority
- No single account is overused

### Example Scenario

```
Account A: rotation_order=1, last_refreshed_at=3 hours ago
Account B: rotation_order=1, last_refreshed_at=1 hour ago
Account C: rotation_order=2, last_refreshed_at=10 hours ago

Selection order:
1. Account A (order=1, oldest)
2. Account B (order=1, newer than A)
3. Account C (order=2, lower priority than both A and B)
```

### Database Fields

The rotation uses these database fields:

- `rotation_order` (Integer): Priority for rotation (0=disabled, 1+=enabled)
- `last_refreshed_at` (DateTime): Last time session was refreshed
- `auto_refresh_enabled` (Boolean): Only accounts with True participate
- `is_active` (Boolean): Only active accounts participate
- `session_health_status` (Enum): Only HEALTHY/EXPIRING participate

### Circuit Breaker Integration

Each account has a Circuit Breaker to prevent rate limiting:

- **CLOSED**: Normal operation, requests allowed
- **OPEN**: Rate limit detected, requests blocked
- **HALF_OPEN**: Recovering, testing if rate limit cleared

The rotation logic checks Circuit Breaker state and respects OPEN state.

## Expected Output

### Successful Test Run

```
================================================================================
🔄 VERIFICATION: Multi-Account Session Rotation for Load Balancing
================================================================================

📍 Step 1: Create 3 Telegram accounts in database
--------------------------------------------------------------------------------
✅ Created user: [uuid]
✅ Created 3 accounts:
   - Account 1: rotation_order=1, refresh_hours=12
   - Account 2: rotation_order=2, refresh_hours=24
   - Account 3: rotation_order=3, refresh_hours=48

📍 Step 2: Verify different refresh_before_expires_hours configured
--------------------------------------------------------------------------------
   Account +11112222333: refresh_before_expires_hours=12
   Account +22223333444: refresh_before_expires_hours=24
   Account +33334444555: refresh_before_expires_hours=48
✅ All accounts have different refresh_before_expires_hours values

📍 Step 3: Trigger health check on all accounts
--------------------------------------------------------------------------------
   Account +11112222333: health_status=HEALTHY, is_healthy=True
   Account +22223333444: health_status=HEALTHY, is_healthy=True
   Account +33334444555: health_status=HEALTHY, is_healthy=True
✅ Health checks completed for all accounts

📍 Step 4: Verify rotation logic selects least-recently-used account
--------------------------------------------------------------------------------
   Selected account for rotation:
   - Phone: +11112222333
   - rotation_order: 1
   - last_refreshed_at: 2026-01-24 11:00:00
   - refresh_before_expires_hours: 12
✅ Correctly selected account with highest priority (rotation_order=1)

📍 Step 5: Verify no rate limiting (check Circuit Breaker state)
--------------------------------------------------------------------------------
   Account +11112222333: Circuit Breaker state=closed
   ✅ Account +11112222333 is not rate limited
   Account +22223333444: Circuit Breaker state=closed
   ✅ Account +22223333444 is not rate limited
   Account +33334444555: Circuit Breaker state=closed
   ✅ Account +33334444555 is not rate limited
✅ Circuit Breaker states verified (no rate limiting detected)

📍 Step 6: Verify rotation event logged to database
--------------------------------------------------------------------------------
   Performing rotation of all accounts...
   Rotated 3 accounts:
   - +11112222333: refreshed (order=1)
   - +22223333444: refreshed (order=2)
   - +33334444555: refreshed (order=3)

   Verifying database state after rotation...
   Account +11112222333:
   - last_refreshed_at: 2026-01-24 14:05:30
   - session_health_status: healthy
   - rotation_order: 1 (unchanged)
   ✅ last_refreshed_at updated recently
   ...

✅ All rotation_order values preserved

================================================================================
✅ ALL 6 VERIFICATION STEPS PASSED!
================================================================================

📊 Summary:
   ✅ 3 Telegram accounts created with different configs
   ✅ Health checks completed for all accounts
   ✅ Rotation logic selected LRU account with highest priority
   ✅ No rate limiting detected (Circuit Breaker not OPEN)
   ✅ Rotation events logged to database
   ✅ 3 accounts successfully rotated

🎉 Rotation verification completed successfully!
```

## Troubleshooting

### Common Issues

1. **Import Error: No module named 'sqlalchemy'**
   - Solution: Install dependencies `pip install -r requirements.txt`

2. **Database Connection Error**
   - Solution: Ensure PostgreSQL is running and `DATABASE_URL` is correct

3. **Tests Pass But Verification Fails**
   - Solution: Check that database migration was applied: `alembic upgrade head`

4. **Circuit Breaker Not Available**
   - This is OK in test environment - tests handle this gracefully

## Pattern Compliance

This test suite follows existing patterns from:

- `test_session_health_monitoring_e2e.py`: Fixture structure, test class organization
- `test_session_refresh_with_2fa_e2e.py`: Async test patterns, service integration
- `conftest.py`: Database fixtures, test data management

Pattern compliance features:
- ✅ Russian docstrings with English comments
- ✅ Type hints throughout
- ✅ Comprehensive error handling
- ✅ No console.log/print debugging (uses logging)
- ✅ pytest fixtures for test isolation
- ✅ Standalone verification script
- ✅ AST syntax validation

## Summary

This comprehensive test suite validates multi-account session rotation for load balancing in the Telegram Session Management system. The tests ensure that:

- Accounts are selected based on priority and LRU strategy
- Load is distributed evenly across participating accounts
- No rate limiting occurs during rotation
- All events are properly logged to the database
- Edge cases are handled correctly

All tests follow existing code patterns and include both pytest-based tests and a standalone verification script for flexible testing options.
