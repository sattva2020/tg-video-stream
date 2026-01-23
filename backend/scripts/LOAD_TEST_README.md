# Load Testing: Stream Recovery System

## Overview

This load test validates the intelligent auto-recovery system's ability to maintain 99%+ uptime under continuous failure conditions. The test simulates realistic failure scenarios across multiple concurrent streams and tracks recovery metrics.

## Test Parameters

### Configuration Options

- **`--duration`**: Test duration in seconds (default: 3600 = 1 hour)
- **`--streams`**: Number of concurrent test streams (default: 10)
- **`--failure-interval-min`**: Minimum seconds between failures (default: 60)
- **`--failure-interval-max`**: Maximum seconds between failures (default: 300)
- **`--output`**: Report output file (default: `load_test_recovery_report.json`)

### Failure Types Simulated

The test randomly induces these failure types:
- **Network**: Connection timeouts
- **API Rate Limit**: Telegram API rate limit exceeded
- **Codec Error**: FFmpeg codec errors
- **Session Expired**: Telegram session expiration
- **Process Crash**: Stream process crashes

## Quick Start

### 1-Hour Test (Development)

```bash
cd backend
python scripts/load_test_recovery_system.py --duration 3600 --streams 10
```

### 24-Hour Test (Production Validation)

```bash
cd backend
python scripts/load_test_recovery_system.py --duration 86400 --streams 50
```

### Intensive Test (100 Streams, 4 Hours)

```bash
cd backend
python scripts/load_test_recovery_system.py --duration 14400 --streams 100 --failure-interval-min 30 --failure-interval-max 120
```

## Prerequisites

### Services Required

1. **PostgreSQL Database**: Running and accessible
2. **Redis**: Running for health state storage
3. **Backend Configuration**: Valid settings in `.env`

### Database Setup

The test will:
- Create a test admin user (`load_test_admin@test.com`)
- Generate test streams with `ACTIVE` status
- Create recovery logs for all recovery attempts
- Clean up is **NOT** automatic (manual cleanup required)

## Test Execution

### Running the Test

```bash
# Basic test
python scripts/load_test_recovery_system.py

# Custom configuration
python scripts/load_test_recovery_system.py \
    --duration 7200 \
    --streams 25 \
    --failure-interval-min 45 \
    --failure-interval-max 180 \
    --output my_test_report.json
```

### Monitoring Progress

The test provides real-time logging to both:
- **Console**: Live progress updates
- **File**: `load_test_recovery.log` (detailed logs)

Example log output:
```
2026-01-23 10:00:00 - __main__ - INFO - Создание 10 тестовых потоков...
2026-01-23 10:00:05 - __main__ - INFO - Создано 10 тестовых потоков
2026-01-23 10:00:10 - __main__ - INFO - Симуляция отказа потoku abc123: network
2026-01-23 10:00:15 - __main__ - INFO - Следующий цикл отказов через 127.3 секунд
```

### Stopping the Test

Press `Ctrl+C` to gracefully stop the test. A report will still be generated with partial results.

## Test Report

### Report Structure

The test generates a JSON report with the following structure:

```json
{
  "test_start": "2026-01-23T10:00:00.000000+00:00",
  "test_end": "2026-01-23T11:00:00.000000+00:00",
  "duration_seconds": 3600,
  "num_streams": 10,
  "total_failures": 45,
  "total_successful_recoveries": 43,
  "total_failed_recoveries": 2,
  "overall_uptime_percentage": 99.12,
  "stream_reports": [...],
  "recovery_logs": [...],
  "circuit_breaker_trips": 3,
  "recommendation": "✅ PASS: Система соответствует требованию 99%+ uptime"
}
```

### Report Sections

1. **Overall Metrics**:
   - Total failures
   - Successful/failed recoveries
   - Overall uptime percentage
   - Circuit breaker trip count

2. **Stream Reports** (Per Stream):
   - Total failures
   - Recovery success/failure counts
   - Uptime/downtime seconds
   - Uptime percentage
   - Last failure/recovery times

3. **Recovery Logs** (All Attempts):
   - Failure type and reason
   - Recovery strategy used
   - Attempt number and backoff time
   - Duration and status

## Acceptance Criteria

The test **PASSES** if:
- ✅ Overall uptime >= 99.0%
- ✅ All recovery events are logged
- ✅ Circuit breaker prevents cascading failures
- ✅ No unexpected crashes or errors

The test **FAILS** if:
- ❌ Overall uptime < 99.0%
- ❌ Recovery events missing from logs
- ❌ System becomes unresponsive
- ❌ Unexpected exceptions occur

## Verification

### Automated Verification

The test script automatically:
1. Calculates uptime percentage
2. Verifies all events are logged
3. Checks circuit breaker functionality
4. Returns exit code 0 on pass, 1 on fail

### Manual Verification

Review the JSON report:
```bash
# View summary
cat load_test_recovery_report.json | jq '.overall_uptime_percentage, .recommendation'

# Check per-stream uptime
cat load_test_recovery_report.json | jq '.stream_reports[] | .stream_id, .uptime_percentage'

# Verify all failures logged
cat load_test_recovery_report.json | jq '.total_failures, (.recovery_logs | length)'
```

### Database Verification

```sql
-- Count recovery logs created during test
SELECT COUNT(*) FROM recovery_logs WHERE created_at >= '2026-01-23 10:00:00';

-- Check failure type distribution
SELECT failure_type, COUNT(*) FROM recovery_logs GROUP BY failure_type;

-- Verify recovery success rate
SELECT status, COUNT(*) FROM recovery_logs GROUP BY status;
```

## Cleanup

### After Testing

Remove test data:
```sql
-- Delete test streams and their recovery logs
DELETE FROM recovery_logs WHERE stream_id IN (
    SELECT id FROM streams WHERE owner_id IN (
        SELECT id FROM users WHERE email = 'load_test_admin@test.com'
    )
);

-- Delete test user
DELETE FROM users WHERE email = 'load_test_admin@test.com';
```

Or use the cleanup script:
```bash
python scripts/cleanup_load_test_data.py
```

## Troubleshooting

### Common Issues

**Issue**: Database connection failed
- **Solution**: Ensure PostgreSQL is running and `DATABASE_URL` is correct

**Issue**: Redis connection error
- **Solution**: Start Redis service: `redis-server`

**Issue**: Import errors
- **Solution**: Ensure virtual environment is activated: `source .venv/bin/activate`

**Issue**: Test hangs
- **Solution**: Check health monitor task logs, ensure Celery worker is running

### Debug Mode

Enable detailed logging:
```python
# Edit the script and change:
logging.basicConfig(level=logging.DEBUG)
```

## Performance Expectations

### Baseline Metrics

Based on configuration (10 streams, 1 hour):
- **Expected Failures**: ~30-60
- **Expected Recovery Time**: 5-30 seconds per failure
- **Expected Uptime**: 99.0% - 99.9%
- **Circuit Breaker Trips**: 0-5

### Scaling

| Streams | Duration | Expected Failures | Expected Test Duration |
|---------|----------|-------------------|----------------------|
| 10      | 1 hour   | 30-60             | ~60 minutes          |
| 50      | 1 hour   | 150-300           | ~60 minutes          |
| 50      | 24 hours | 3600-7200         | ~24 hours            |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Test Recovery System

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run load test (1 hour)
        run: |
          cd backend
          python scripts/load_test_recovery_system.py \
            --duration 3600 \
            --streams 10 \
            --output test_report.json

      - name: Verify uptime threshold
        run: |
          UPTIME=$(cat test_report.json | jq '.overall_uptime_percentage')
          if (( $(echo "$UPTIME < 99" | bc -l) )); then
            echo "❌ Uptime $UPTIME% below 99% threshold"
            exit 1
          fi
          echo "✅ Uptime $UPTIME% meets threshold"
```

## Support

For issues or questions:
1. Check `load_test_recovery.log` for detailed error messages
2. Review the JSON report for specific failure patterns
3. Consult system logs: `backend/logs/` and Celery worker logs
4. Open an issue with the report attached
