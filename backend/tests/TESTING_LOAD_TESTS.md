# Load Testing: Recommendation API

## Overview

This document describes the load testing approach for the recommendation API endpoints.

## Test File

**Location:** `backend/tests/test_recommendations_load.py`

**Lines of Code:** 567

**Test Methods:** 6

## Endpoints Tested

### 1. GET /api/recommendations
**Purpose:** Fetch personalized recommendations for users

**Test:** `test_get_recommendations_concurrent_requests`
- **Concurrent requests:** 50
- **Max workers:** 10
- **Performance requirements:**
  - Average response time < 2 seconds
  - P95 response time < 5 seconds
  - Error rate < 5%

### 2. POST /api/recommendations/feedback
**Purpose:** Submit user feedback (like/dislike) on recommendations

**Test:** `test_post_feedback_concurrent_requests`
- **Concurrent requests:** 50
- **Max workers:** 10
- **Performance requirements:**
  - Average response time < 1 second
  - P95 response time < 2 seconds
  - Error rate < 5%

### 3. GET /api/recommendations/stats
**Purpose:** Fetch quality metrics (CTR, watch time, feedback rate)

**Test:** `test_get_stats_concurrent_requests`
- **Concurrent requests:** 30
- **Max workers:** 10
- **Performance requirements:**
  - Average response time < 1 second (benefits from Redis caching)
  - P95 response time < 2 seconds
  - Error rate < 5%

### 4. GET /api/recommendations/for-playlist
**Purpose:** Fetch recommendations for a specific playlist

**Test:** `test_get_for_playlist_concurrent_requests`
- **Concurrent requests:** 30
- **Max workers:** 10
- **Performance requirements:**
  - Average response time < 2 seconds
  - P95 response time < 5 seconds
  - Error rate < 5%

### 5. Mixed Endpoints Load Test
**Purpose:** Simulate real-world usage patterns

**Test:** `test_mixed_endpoints_concurrent_requests`
- **Total concurrent requests:** 100
- **Max workers:** 15
- **Request distribution:**
  - 40% GET /api/recommendations (40 requests)
  - 30% POST /api/recommendations/feedback (30 requests)
  - 20% GET /api/recommendations/stats (20 requests)
  - 10% GET /api/recommendations/for-playlist (10 requests)
- **Performance requirements:**
  - Average response time < 2 seconds
  - P95 response time < 5 seconds
  - Error rate < 5%

### 6. Sustained Load Test
**Purpose:** Test system stability under continuous load

**Test:** `test_sustained_load_recommendations`
- **Total requests:** 200
- **Max workers:** 20
- **Endpoint:** GET /api/recommendations
- **Performance requirements:**
  - Throughput > 10 requests/second
  - Average response time < 2 seconds
  - Error rate < 5%
  - No response time degradation over time

## Metrics Collected

The `LoadTestMetrics` class collects the following metrics:

1. **Response Times**
   - Average (mean)
   - Minimum
   - Maximum
   - P50 (median)
   - P95 (95th percentile)
   - P99 (99th percentile)

2. **Throughput**
   - Requests per second

3. **Error Rate**
   - Percentage of failed requests
   - Success count
   - Error count
   - Error details (status code, exception, response)

## Implementation Details

### Thread Safety
- All metrics operations use `threading.Lock` for thread-safe updates
- `LoadTestMetrics.add_response()` ensures atomic updates

### Concurrency Model
- `ThreadPoolExecutor` for managing concurrent requests
- Configurable `max_workers` (10-20 depending on test)
- `as_completed()` for processing results as they finish

### Test Fixtures
1. **client:** FastAPI TestClient for API requests
2. **load_test_user:** Test user (telegram_id=999999)
3. **load_test_items:** 20 test playlist items
4. **recommendation_service_no_redis:** Service without Redis cache
5. **trained_models:** Pre-trained collaborative and content-based models

### Validation Script
**Location:** `backend/tests/validate_load_test.py`

Validates test structure without pytest:
- Checks required imports
- Verifies fixtures present
- Confirms test class exists
- Validates test methods
- Checks helper functions
- Verifies endpoint coverage (4/4)

## Running the Tests

```bash
# Run all load tests
cd backend
pytest tests/test_recommendations_load.py -v --tb=short

# Run specific test
pytest tests/test_recommendations_load.py::TestRecommendationsLoad::test_get_recommendations_concurrent_requests -v

# Run with detailed output
pytest tests/test_recommendations_load.py -v -s

# Validate test structure
python backend/tests/validate_load_test.py
```

## Example Output

```
=== GET /api/recommendations Load Test ===
Total requests: 50
Success: 50, Errors: 0
Error rate: 0.00%
Avg response time: 0.523s
P50: 0.487s, P95: 0.891s, P99: 0.956s

=== POST /api/recommendations/feedback Load Test ===
Total requests: 50
Success: 50, Errors: 0
Error rate: 0.00%
Avg response time: 0.234s
P50: 0.210s, P95: 0.456s

=== Mixed Endpoints Load Test ===
Total requests: 100
Success: 98, Errors: 2
Error rate: 2.00%
Avg response time: 0.678s
P50: 0.543s, P95: 1.234s, P99: 1.567s
```

## Performance Optimization Insights

### Redis Caching
- `/api/recommendations/stats` benefits from 10-minute TTL cache
- Subsequent requests are significantly faster
- Cache invalidation on feedback submission

### Database Queries
- Recommendations are saved to database for CTR tracking
- Indexes on `user_id`, `playlist_item_id`, `created_at` improve query performance
- Connection pooling handles concurrent connections

### ML Model Inference
- Models loaded once per test (via fixtures)
- Predictions are CPU-bound but fast (< 100ms per request)
- Scikit-learn's TruncatedSVD is efficient for matrix factorization

## Troubleshooting

### High Error Rate
- Check database connection pool size
- Verify Redis connection
- Review ML model files exist

### Slow Response Times
- Check database query performance (EXPLAIN ANALYZE)
- Verify Redis caching is working
- Review ML model size and loading time

### Race Conditions
- All metrics use threading.Lock
- Database transactions handle concurrent writes
- Redis operations are atomic

## Success Criteria

✓ All tests pass with < 5% error rate
✓ Response times meet performance thresholds
✓ System remains stable under sustained load
✓ No memory leaks or connection pool exhaustion
✓ Thread-safe metrics collection

## Related Documentation

- [Collaborative Filtering Tests](./integration/TESTING_COLLABORATIVE_FILTERING.md)
- [Content-Based Filtering Tests](./integration/TESTING_CONTENT_BASED_FILTERING.md)
- [Hybrid Recommendations Tests](./integration/TESTING_HYBRID_RECOMMENDATIONS.md)
- [Quality Metrics Tests](./integration/TESTING_QUALITY_METRICS.md)
- [API Documentation](../../src/api/recommendations.py)
