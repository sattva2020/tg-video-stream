# E2E Tests for SDK Functionality

This directory contains end-to-end tests for the SDK functionality with real API endpoints.

## Test Overview

The tests verify that the Python SDK works correctly with the actual backend API endpoints. These are integration-level tests that use:

- Real API endpoints (via TestClient or HTTP requests)
- Real database operations
- Actual SDK client instances
- Real API key authentication

## Test Structure

### Fixtures

- `db_session`: Creates a test user and API key in the database
- `api_key`: Extracts the raw API key for use in SDK client
- `sdk_client`: Creates an instance of SattvaClient with the test API key

### Test Categories

1. **Client Initialization Tests**
   - test_sdk_client_initialization
   - test_sdk_client_context_manager

2. **Authentication Tests**
   - test_sdk_auth_with_valid_key
   - test_sdk_auth_with_invalid_key
   - test_sdk_auth_without_key

3. **Resource Tests**
   - Streams: list, get
   - Channels: list, get
   - Playlists: list
   - API Keys: list
   - Webhooks: list, create, update, delete

4. **Error Handling Tests**
   - test_sdk_not_found_error
   - test_sdk_validation_error

5. **Rate Limiting Tests**
   - test_sdk_rate_limiting

6. **Webhook Signature Verification**
   - test_sdk_webhook_signature_verification

7. **HTTP Client Tests**
   - test_sdk_http_get_method
   - test_sdk_http_post_method

8. **Timeout Tests**
   - test_sdk_timeout_handling

9. **Integration Tests**
   - test_sdk_full_workflow

10. **SDK Version Test**
    - test_sdk_version

## Running the Tests

### Prerequisites

Ensure the backend dependencies are installed:

```bash
cd backend
pip install -e .
```

### Run All E2E Tests

From the project root:

```bash
pytest tests/e2e/test_sdks.py -v
```

### Run Specific Test

```bash
pytest tests/e2e/test_sdks.py::test_sdk_version -v
```

### Run with Coverage

```bash
pytest tests/e2e/test_sdks.py -v --cov=sdks/python/sattva_api --cov-report=term-missing
```

## Environment Variables

The tests use the following environment variables (automatically set in conftest.py):

- `SESSION_ENCRYPTION_KEY`: Test encryption key
- `JWT_SECRET`: Test JWT secret
- `TESTING`: Set to "true"
- `BACKEND_URL`: Backend API URL (default: http://localhost:8000)
- `REDIS_URL`: Disabled in tests (uses fakeredis)

## Test Data

The tests create the following test data:

- **User**: sdk_e2e_test@example.com
- **API Key**: SDK E2E Test Key with scopes for reading streams, playlists, channels, webhooks and writing webhooks
- **Rate Limit**: 100 requests per 60 seconds

All test data is automatically cleaned up after each test.

## Expected Results

All tests should pass with the following expectations:

- SDK client can be initialized with API key
- SDK can authenticate with valid API key and fail with invalid key
- All SDK resource methods (streams, channels, playlists, webhooks, api_keys) work correctly
- Error handling properly raises SDK exceptions
- Webhook signature verification works
- SDK context manager works correctly
- Full workflow integration test passes

## Troubleshooting

### Import Errors

If you see import errors for SDK modules:

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/project/sdks/python"
```

### Database Connection Errors

Ensure the test database configuration is correct in `backend/src/database.py`.

### Backend Not Running

These tests use TestClient and don't require a running backend server. The FastAPI app is started in test mode.

## Future Enhancements

Potential additions to the E2E test suite:

- JavaScript SDK tests (using Node.js test runner)
- Go SDK tests (using Go test framework)
- Concurrent request tests
- Webhook delivery end-to-end tests
- Rate limiting stress tests
