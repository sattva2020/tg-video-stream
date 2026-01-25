# PyTgCalls Fallback Tests

## Overview

This document describes the test coverage for verifying that the system correctly falls back to PyTgCalls when AyuGram is unavailable or not enabled.

## Purpose

These tests ensure backward compatibility by verifying that:
1. When USE_AYUGRAM is not set or set to "0"/"pytg", the system uses PyTgCalls
2. No AyuGram import errors occur in fallback scenarios
3. The ayugram_adapter module can be imported regardless of USE_AYUGRAM setting
4. Backend detection logic works correctly

## Test Files

- `streamer/tests/test_ayugram_integration.py` - Contains `TestPyTgCallsFallback` class with 9 test methods
- `streamer/tests/verify_fallback_tests.py` - Standalone verification script (pytest-free)

## Test Coverage

### TestPyTgCallsFallback Class

1. **test_fallback_when_use_ayugram_unset**
   - Verifies that when USE_AYUGRAM is not set, `is_available()` returns False
   - Ensures PyTgCalls path is taken by default

2. **test_fallback_when_use_ayugram_zero**
   - Verifies that when USE_AYUGRAM="0", `is_available()` returns False
   - Ensures explicit PyTgCalls selection works

3. **test_fallback_when_use_ayugram_pytg**
   - Verifies that when USE_AYUGRAM="pytg", `is_available()` returns False
   - Ensures explicit PyTgCalls selection works with "pytg" value

4. **test_no_ayugram_import_errors**
   - Verifies that ayugram_adapter module can be imported without errors when USE_AYUGRAM is not set
   - Ensures AYUGRAM_AVAILABLE flag is set correctly based on environment
   - Ensures AyuGramAdapter can be instantiated (but not used via is_available())

5. **test_ayugram_available_flag_reflects_env**
   - Verifies that AYUGRAM_AVAILABLE flag reflects the USE_AYUGRAM environment variable
   - Tests with USE_AYUGRAM unset (expects False)
   - Tests with USE_AYUGRAM="0" (expects False)

6. **test_adapter_works_without_env_var**
   - Verifies that AyuGramAdapter can be created and used even without USE_AYUGRAM set
   - Tests adapter.start() and adapter.stop() methods work
   - Note: The adapter can be created but should not be used when is_available() returns False

7. **test_backend_detection_main_py**
   - Tests backend detection logic for all USE_AYUGRAM values:
     * Not set → False (PyTgCalls)
     * "0" → False (PyTgCalls)
     * "pytg" → False (PyTgCalls)
     * "1" → True (AyuGram)
     * "ayugram" → True (AyuGram)

8. **test_fallback_integration_with_streaming**
   - Integration test verifying fallback works with streaming scenario
   - Ensures that when USE_AYUGRAM="0", is_available() returns False
   - Verifies adapter can be created but system should use PyTgCalls

## Verification Steps

### End-to-End Verification

1. **Set USE_AYUGRAM=0 or leave unset**
   ```bash
   unset USE_AYUGRAM  # or export USE_AYUGRAM=0
   ```

2. **Start streamer**
   ```bash
   cd streamer
   python main.py
   ```

3. **Verify PyTgCalls initialization succeeds**
   - Check logs for "pytgcalls" initialization messages
   - No AyuGram-related errors should appear

4. **Send start command** (via Redis)
   ```bash
   redis-cli PUBLISH stream:control '{"command":"start",...}'
   ```

5. **Verify stream works with PyTgCalls as before**
   - Stream should start and play normally
   - All event handlers should work

6. **Verify no AyuGram import errors**
   - Check logs for no import errors
   - System should degrade gracefully to PyTgCalls

## Running Tests

### With pytest
```bash
cd streamer
python -m pytest tests/test_ayugram_integration.py::TestPyTgCallsFallback -v
```

### Without pytest (verification script)
```bash
cd streamer
python tests/verify_fallback_tests.py
```

## Expected Results

All 8 verification tests should pass:
- ✅ test_fallback_when_use_ayugram_unset
- ✅ test_fallback_when_use_ayugram_zero
- ✅ test_fallback_when_use_ayugram_pytg
- ✅ test_no_ayugram_import_errors
- ✅ test_ayugram_available_flag_reflects_env
- ✅ test_adapter_works_without_env_var
- ✅ test_backend_detection
- ✅ test_fallback_integration

## Important Notes

1. **AYUGRAM_AVAILABLE Flag**: This flag is set at module import time based on the USE_AYUGRAM environment variable. It does not indicate whether the module can be imported, but rather whether AyuGram should be used.

2. **is_available() Function**: Returns True only when USE_AYUGRAM is set to "1", "true", "yes", or "ayugram" (case-insensitive). For all other values (including "0", "pytg", or unset), it returns False.

3. **Module Reload**: Tests that check different USE_AYUGRAM values must reload the ayugram_adapter module (delete from sys.modules) to ensure AYUGRAM_AVAILABLE is recalculated.

4. **Graceful Degradation**: The system is designed to work with PyTgCalls when AyuGram is not available. The ayugram_adapter module can always be imported, but is_available() determines whether it should be used.

## Implementation Details

### Backend Detection in main.py

```python
# Lines 197-229 in main.py
if USE_AYUGRAM == "1" or USE_AYUGRAM == "ayugram":
    # Use AyuGram adapter
    if AYUGRAM_AVAILABLE and app:
        try:
            ayugram = AyuGramAdapter(app)
            log.info("AyuGram adapter initialized")
        except Exception as e:
            log.warning("AyuGram adapter initialization failed: %s", e)
            ayugram = None
    # Fallback to PyTgCalls if AYUGRAM_AVAILABLE is False
else:
    # Use PyTgCalls (default)
    if PYG_AVAILABLE and app:
        try:
            pytg = PyTgCalls(app)
        except Exception as e:
            log.warning("pytgcalls initialization failed: %s", e)
            pytg = None
```

### is_available() in ayugram_adapter.py

```python
# Lines 508-530 in ayugram_adapter.py
def is_available() -> bool:
    """
    Check if AyuGram adapter is available.

    Returns True if tg-engine service path is configured or if
    the adapter should be used based on environment.
    """
    use_ayugram = os.getenv("USE_AYUGRAM", "0").strip().lower() in {"1", "true", "yes", "ayugram"}

    tg_engine_path = os.getenv("AYUGRAM_TG_ENGINE_PATH")

    if use_ayugram and not tg_engine_path:
        log.warning("USE_AYUGRAM=1 but AYUGRAM_TG_ENGINE_PATH not set")

    return use_ayugram
```

## Related Files

- `streamer/main.py` - Backend initialization logic
- `streamer/ayugram_adapter.py` - is_available() function and AYUGRAM_AVAILABLE flag
- `streamer/tests/test_ayugram_integration.py` - Full integration test suite
- `streamer/tests/verify_fallback_tests.py` - Standalone verification script

## Dependencies

None - tests use only unittest.mock and standard library modules.
