# Performance Tests

This directory contains performance tests for live streaming capabilities.

## Stream Switching Latency Tests

`test_stream_switching_latency.py` measures the performance of stream switching operations.

### Test Coverage

1. **Stream Creation API Latency**
   - Measures API response time for creating live streams
   - Target: < 500ms

2. **Stream Start API Latency**
   - Measures API response time for starting streams
   - Target: < 500ms

3. **Stream Stop API Latency**
   - Measures API response time for stopping streams
   - Target: < 500ms

4. **Complete Switch to Live Latency**
   - Measures API call time + status propagation time
   - Target: < 2 seconds total

5. **Complete Stream Stop Latency**
   - Measures API call time + status propagation time
   - Target: < 2 seconds total

6. **Multiple Stream Switching Latency**
   - Measures latency when switching between multiple streams
   - Simulates rapid switching scenarios (e.g., camera angles)
   - Target: < 2 seconds per switch

7. **Manual End-to-End Latency** (requires human verification)
   - Measures actual audio change in Telegram client
   - Requires manual testing with streamer and Telegram

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API Response Time | < 500ms | Backend API should respond quickly |
| Status Propagation | < 1.5s | Status change should propagate to database |
| Total Switch Latency | < 2s | Complete switch from command to status update |
| Audio Change (manual) | < 2s | From command to audio change in Telegram |

### Running Tests

```bash
# Run all performance tests
pytest tests/performance/test_stream_switching_latency.py -v -m performance

# Run specific test
pytest tests/performance/test_stream_switching_latency.py::test_stream_start_api_latency -v

# Run with coverage
pytest tests/performance/ --cov=src.services --cov-report=html
```

### Environment Variables

- `BACKEND_URL`: Backend API URL (default: http://localhost:8000)
- `TEST_USER_TOKEN`: Auth token for test user (required)
- `TEST_TELEGRAM_CHAT_ID`: Telegram chat ID for testing (default: -1001234567890)

### Test Methodology

1. **Warmup Iterations**: 2 warmup runs to stabilize system
2. **Measurement Iterations**: 5 measurement runs for statistics
3. **Statistics Calculated**:
   - Min, Max, Average
   - Median
   - P95, P99 percentiles

### Interpreting Results

Tests will fail if:
- Average latency exceeds target
- P95 latency exceeds 1.5x target
- Max latency exceeds 1.5x target (for multi-stream tests)

Example output:
```
test_stream_start_api_latency: Average 234ms, P95 312ms ✓
test_switch_to_live_complete_latency: Total 1.2s ✓
```

### Manual Testing

For complete end-to-end latency measurement (command → audio change in Telegram):

1. Start scheduled stream with music
2. Send switch-to-live command (record timestamp)
3. Monitor Telegram audio output
4. Record timestamp when audio changes
5. Calculate latency difference

This cannot be fully automated due to the need for human listening and Telegram client interaction.

### Continuous Integration

These tests can be integrated into CI/CD pipelines:
- Run on every PR to detect performance regressions
- Set performance budgets in test thresholds
- Track metrics over time with performance monitoring tools

### Troubleshooting

**Tests fail with timeout errors**:
- Check backend API is running
- Verify database connection is healthy
- Check system resources (CPU, memory)

**High latency variability**:
- Run tests multiple times to establish baseline
- Check for background processes consuming resources
- Verify network latency between test and backend

**Tests skip with "TEST_USER_TOKEN not configured"**:
- Set TEST_USER_TOKEN environment variable
- Token must be valid JWT for test user
