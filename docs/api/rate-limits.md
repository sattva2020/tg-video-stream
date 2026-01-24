# Rate Limit Management API

> **Spec**: 005-rate-limit-optimization-queue-management
> **Version**: 1.0
> **Date**: 2026-01-24

## Overview

Advanced Telegram API rate limit management system with intelligent queue management, distributed throttling across multiple accounts, request prioritization, automatic backoff strategies, and rate limit prediction.

## Features

- **Priority Queue**: HIGH (stream control), MEDIUM (metadata fetch), LOW (background tasks)
- **Multi-Account Distribution**: Automatic load balancing across multiple Telegram accounts
- **Rate Limit Prediction**: Forecast when rate limits will be hit
- **Alert System**: Configurable warning thresholds with admin notifications
- **Real-time Dashboard**: Monitor usage, predictions, and account health

## Base URL

All endpoints use the base path:
```
/api/v1/rate-limits
```

## Authentication

All endpoints require authenticated user (admin access recommended). Include JWT token in Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Get Rate Limit Status

Get current rate limit status across all accounts with predictions.

```http
GET /api/v1/rate-limits/status
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 60 requests/minute per user

**Query Parameters**: None

**Response**:
```json
{
  "overall_status": "healthy",
  "total_accounts": 5,
  "active_accounts": 4,
  "rate_limited_accounts": 1,
  "accounts": [
    {
      "account_id": "account-1",
      "endpoint_type": "messages",
      "current_usage": 45,
      "limit": 60,
      "usage_percent": 75.0,
      "status": "warning",
      "predicted_breach_time": "2025-01-24T12:30:00Z",
      "time_until_breach_seconds": 1200
    }
  ],
  "timestamp": "2025-01-24T12:00:00Z"
}
```

**Status Values**:
- `healthy`: Usage < 75%
- `warning`: Usage 75-89%
- `critical`: Usage ≥ 90%

---

### 2. Get Rate Limit Metrics

Get detailed metrics including usage trends, predictions, and confidence scores.

```http
GET /api/v1/rate-limits/metrics
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 30 requests/minute per user

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_id` | string | No | Filter metrics for specific account |

**Response**:
```json
{
  "usage_metrics": [
    {
      "account_id": "account-1",
      "requests_per_minute": 15.5,
      "trend": "increasing",
      "confidence": 0.85,
      "window_start": "2025-01-24T11:00:00Z",
      "window_end": "2025-01-24T12:00:00Z"
    }
  ],
  "predictions": [
    {
      "endpoint_type": "messages",
      "current_usage": 45,
      "limit": 60,
      "usage_percent": 75.0,
      "predicted_breach_time": "2025-01-24T12:30:00Z",
      "time_until_breach_seconds": 1200,
      "trend": "increasing",
      "confidence": 0.85,
      "alert_triggered": false,
      "is_critical": false
    }
  ],
  "summary": {
    "total_accounts": 5,
    "avg_usage_percent": 65.5,
    "critical_predictions": 0
  },
  "timestamp": "2025-01-24T12:00:00Z"
}
```

**Trend Values**:
- `increasing`: Usage rate is growing
- `stable`: Usage rate is consistent
- `decreasing`: Usage rate is declining

---

### 3. Get Rate Limit Predictions

Get predicted breach times for all accounts and endpoint types.

```http
GET /api/v1/rate-limits/predictions
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 30 requests/minute per user

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_id` | string | No | Filter predictions for specific account |

**Response**:
```json
{
  "predictions": [
    {
      "account_id": "account-1",
      "endpoint_type": "messages",
      "current_usage": 45,
      "limit": 60,
      "usage_percent": 75.0,
      "predicted_breach_time": "2025-01-24T12:30:00Z",
      "time_until_breach_seconds": 1200,
      "trend": "increasing",
      "confidence": 0.85,
      "status": "warning"
    }
  ],
  "summary": {
    "total_predictions": 5,
    "approaching_limit": 2,
    "critical_predictions": 0,
    "overall_status": "warning"
  },
  "timestamp": "2025-01-24T12:00:00Z"
}
```

---

### 4. Get Account Distribution

Get account pool status and distribution information.

```http
GET /api/v1/rate-limits/accounts
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 60 requests/minute per user

**Response**:
```json
{
  "total_accounts": 5,
  "active_accounts": 4,
  "rate_limited_accounts": 1,
  "disabled_accounts": 0,
  "failed_accounts": 0,
  "accounts": [
    {
      "account_id": "account-1",
      "status": "active",
      "health": "healthy",
      "usage_percent": 75.0,
      "success_count": 450,
      "failure_count": 5,
      "last_used": "2025-01-24T12:00:00Z"
    }
  ],
  "selection_strategy": "least_used",
  "timestamp": "2025-01-24T12:00:00Z"
}
```

**Account Status Values**:
- `active`: Available for requests
- `rate_limited`: Temporarily limited by Telegram
- `disabled`: Manually disabled
- `failed`: Automatic exclusion due to errors
- `banned`: Permanently banned by Telegram

**Health Values**:
- `healthy`: All systems operational
- `degraded`: Some issues detected
- `failed`: Non-operational
- `disabled`: Intentionally disabled

**Selection Strategies**:
- `least_used`: Select account with lowest usage
- `round_robin`: Cyclic account selection
- `weighted`: Weighted based on performance

---

### 5. Get Queue Statistics

Get queue statistics and pending request information.

```http
GET /api/v1/rate-limits/queue
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 60 requests/minute per user

**Response**:
```json
{
  "total_pending": 150,
  "total_processing": 5,
  "stats_by_priority": [
    {
      "priority_level": "HIGH",
      "pending_requests": 10,
      "processing_requests": 2,
      "completed_last_minute": 45,
      "average_wait_time_seconds": 0.5
    },
    {
      "priority_level": "MEDIUM",
      "pending_requests": 40,
      "processing_requests": 2,
      "completed_last_minute": 30,
      "average_wait_time_seconds": 2.0
    },
    {
      "priority_level": "LOW",
      "pending_requests": 100,
      "processing_requests": 1,
      "completed_last_minute": 25,
      "average_wait_time_seconds": 5.0
    }
  ],
  "batch_size": 10,
  "batch_timeout_seconds": 5,
  "timestamp": "2025-01-24T12:00:00Z"
}
```

**Priority Levels**:
- `HIGH` (0): Stream control - play/pause/skip
- `MEDIUM` (1000): Metadata fetch, channel info
- `LOW` (2000): Background sync, batch operations

---

### 6. Add Account to Pool

Add a new Telegram account to the multi-account pool.

```http
POST /api/v1/rate-limits/accounts
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 20 requests/minute per user

**Request Body**:
```json
{
  "account_id": "account-123",
  "phone": "+1234567890"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "message": "Account added to pool successfully",
  "account_id": "account-123"
}
```

**Error Responses**:
- `409 Conflict`: Account already exists in pool
- `500 Internal Server Error`: Failed to add account

---

### 7. Update Account Status

Enable or disable an account in the pool.

```http
PUT /api/v1/rate-limits/accounts/{account_id}
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 30 requests/minute per user

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_id` | string | Yes | Account identifier |

**Request Body**:
```json
{
  "status": "active"
}
```

**Valid Status Values**:
- `active`: Enable account
- `disabled`: Manually disable account
- `failed`: Mark as failed (automatic exclusion)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Account status updated to active",
  "account_id": "account-123"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid status value
- `404 Not Found`: Account not found in pool
- `500 Internal Server Error`: Failed to update status

---

### 8. Remove Account from Pool

Remove an account from the multi-account pool.

```http
DELETE /api/v1/rate-limits/accounts/{account_id}
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 20 requests/minute per user

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_id` | string | Yes | Account identifier |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Account removed from pool successfully",
  "account_id": "account-123"
}
```

**Error Responses**:
- `404 Not Found`: Account not found in pool
- `500 Internal Server Error`: Failed to remove account

---

### 9. Update Rate Limit Settings

Configure alert thresholds and notification preferences.

```http
PUT /api/v1/rate-limits/settings
```

**Permission**: Authenticated user (admin access recommended)
**Rate Limit**: 30 requests/minute per user

**Request Body** (all fields optional):
```json
{
  "alert_thresholds": {
    "warning_threshold_percent": 75.0,
    "critical_threshold_percent": 90.0
  },
  "notification_preferences": {
    "enabled": true,
    "channels": ["channel-1", "channel-2"],
    "notify_on_warning": true,
    "notify_on_critical": true,
    "cooldown_seconds": 300
  }
}
```

**Field Descriptions**:
- `warning_threshold_percent` (0-100): Warning alert threshold
- `critical_threshold_percent` (0-100): Critical alert threshold (must be > warning)
- `enabled`: Whether notifications are enabled
- `channels`: List of notification channel IDs
- `notify_on_warning`: Send notifications at warning threshold
- `notify_on_critical`: Send notifications at critical threshold
- `cooldown_seconds`: Minimum seconds between notifications for same account

**Response** (200 OK):
```json
{
  "alert_thresholds": {
    "warning_threshold_percent": 75.0,
    "critical_threshold_percent": 90.0
  },
  "notification_preferences": {
    "enabled": true,
    "channels": ["channel-1", "channel-2"],
    "notify_on_warning": true,
    "notify_on_critical": true,
    "cooldown_seconds": 300
  },
  "timestamp": "2025-01-24T12:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: warning_threshold_percent must be < critical_threshold_percent
- `500 Internal Server Error`: Failed to update settings

---

## Configuration

### Environment Variables

Configure rate limiting behavior via environment variables in `.env`:

```ini
# Alert Thresholds
RATE_LIMIT_ALERT_WARNING_THRESHOLD=75
RATE_LIMIT_ALERT_CRITICAL_THRESHOLD=90

# Alert Settings
RATE_LIMIT_ALERT_ENABLED=true
RATE_LIMIT_ALERT_COOLDOWN_SECONDS=300
RATE_LIMIT_ALERT_CHANNELS=channel-1,channel-2

# Queue Settings
RATE_LIMIT_QUEUE_BATCH_SIZE=10
RATE_LIMIT_QUEUE_BATCH_TIMEOUT=5

# Multi-Account Settings
RATE_LIMIT_ACCOUNT_SELECTION_STRATEGY=least_used
RATE_LIMIT_MAX_ACCOUNTS=10
```

---

## Error Handling

### Standard Error Response

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Status | Description |
|--------|-------------|
| `200 OK` | Request successful |
| `201 Created` | Resource created successfully |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Missing or invalid authentication |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Resource already exists |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |

---

## Rate Limiting

API endpoints have different rate limits to prevent abuse:

| Endpoint Type | Rate Limit |
|---------------|------------|
| Status/Query endpoints | 60 req/min |
| Metrics/Predictions | 30 req/min |
| Account modifications | 20 req/min |
| Settings updates | 30 req/min |

Rate limits are per-user and enforced via JWT token.

---

## Monitoring

### Prometheus Metrics

The system exports Prometheus metrics for monitoring:

- `telegram_api_requests_total`: Total API requests per account
- `telegram_rate_limit_remaining`: Remaining requests before limit
- `telegram_account_usage_percent`: Current usage percentage
- `rate_limit_queue_size`: Current queue size by priority
- `rate_limit_prediction_breach_time`: Seconds until predicted breach

Access metrics at: `http://localhost:8000/metrics`

---

## Frontend Integration

### React Admin Dashboard

Access the rate limit dashboard at:
```
http://localhost:3000/admin/rate-limits
```

**Features**:
- Real-time status overview
- Account distribution panel
- Usage trends chart
- Queue statistics
- Alert configuration
- Account management (enable/disable/remove)

**Required Role**: ADMIN or SUPERADMIN

### API Client

Use the TypeScript API client for frontend integration:

```typescript
import { rateLimitsApi } from '@/api/rateLimits';

// Get status
const status = await rateLimitsApi.getStatus();

// Get predictions
const predictions = await rateLimitsApi.getPredictions('account-1');

// Update settings
await rateLimitsApi.updateSettings({
  alert_thresholds: {
    warning_threshold_percent: 75,
    critical_threshold_percent: 90
  }
});
```

---

## Troubleshooting

### Issue: Predictions not accurate

**Cause**: Insufficient historical data

**Solution**:
- Wait at least 1 hour for initial data collection
- Check Redis is running: `redis-cli ping`
- Verify predictor task is running: `celery -A celery_app inspect active`

### Issue: Accounts not distributing load

**Cause**: All accounts rate-limited or disabled

**Solution**:
- Check account status via `/accounts` endpoint
- Verify account health in database
- Add more accounts to pool if needed

### Issue: Alerts not triggering

**Cause**: Notification channels not configured

**Solution**:
- Verify `RATE_LIMIT_ALERT_ENABLED=true`
- Check notification channels are set in settings
- Review alert cooldown period

### Issue: Queue processing slow

**Cause**: Insufficient worker capacity

**Solution**:
- Increase Celery worker count: `celery worker -c 4`
- Adjust batch size in settings
- Check Redis memory usage

---

## Performance

### Benchmarks

- **Queue Throughput**: 1000+ requests/second
- **Prediction Latency**: P50 < 1ms, P95 < 5ms, P99 < 10ms
- **Status Endpoint**: < 100ms response time
- **Concurrent Accounts**: Supports 10+ accounts

### Optimization Tips

1. **Batch Requests**: Use queue for bulk operations
2. **Appropriate Priority**: Use HIGH priority sparingly
3. **Account Pool**: Maintain 3-5 accounts for redundancy
4. **Monitoring**: Set up alerts for 75% threshold
5. **Cache Results**: Cache predictions for 30 seconds

---

## Security Considerations

1. **Authentication**: All endpoints require valid JWT
2. **Authorization**: Admin-only access for account management
3. **Rate Limiting**: API endpoints have rate limits
4. **Input Validation**: All inputs validated via Pydantic
5. **Audit Logging**: All operations logged with user ID

---

## Related Documentation

- [Feature Documentation](../features/rate-limit-optimization.md)
- [Setup Guide](../deployment/rate-limit-setup.md)
- [Architecture](../architecture/rate-limit-architecture.md)
- [Telegram Rate Limits](../features/TELEGRAM_RATE_LIMITS.md)
