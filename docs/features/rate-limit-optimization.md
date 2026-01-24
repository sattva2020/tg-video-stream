# Rate Limit Optimization & Queue Management

> **Spec ID**: 005-rate-limit-optimization-queue-management
> **Status**: ✅ Implemented
> **Version**: 1.0.0
> **Last Updated**: 2026-01-24

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Setup & Configuration](#setup--configuration)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Dashboard](#dashboard)
- [Monitoring & Alerts](#monitoring--alerts)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)
- [Security](#security)

---

## Overview

Advanced Telegram API rate limit management system that provides intelligent queue management, distributed throttling across multiple accounts, request prioritization, automatic backoff strategies, and rate limit prediction with real-time dashboards and alerts.

### Problem Statement

Telegram API has strict rate limits that vary by endpoint type:
- **Messages**: 20-30 requests/minute per account
- **Channels**: 10-15 requests/minute per account
- **Users**: 30-50 requests/minute per account

Exceeding these limits results in:
- `FloodWaitError` (temporary ban)
- Reduced streaming quality
- Failed API calls
- Poor user experience

### Solution

Our system provides:
1. **Intelligent Queue**: Priority-based request queuing
2. **Multi-Account Distribution**: Load balancing across accounts
3. **Predictive Analytics**: Forecast rate limit breaches
4. **Automated Alerts**: Notify before hitting limits
5. **Real-time Dashboard**: Monitor system health

---

## Features

### 1. Priority Queue System

Requests are categorized by priority:

| Priority | Score | Use Cases | Examples |
|----------|-------|-----------|----------|
| **HIGH** | 0 | Stream control | Play, pause, skip |
| **MEDIUM** | 1000 | User-facing | Metadata fetch, channel info |
| **LOW** | 2000 | Background | Sync, batch operations |

**Benefits**:
- High-priority requests bypass queue
- Users experience minimal latency
- Background tasks don't block critical operations

### 2. Multi-Account Rate Limiter

Distribute API load across multiple Telegram accounts:

**Selection Strategies**:
- `least_used`: Prefer account with lowest usage (default)
- `round_robin`: Cyclic distribution
- `weighted`: Performance-based weighting

**Account Health Tracking**:
- Automatic failure detection
- Circuit breaker pattern
- Self-healing pool

**Benefits**:
- Scale horizontally (3-5 accounts recommended)
- Automatic failover
- No single point of failure

### 3. Rate Limit Predictor

Machine learning-based prediction of rate limit breaches:

**Features**:
- Sliding window usage tracking
- Linear regression forecasting
- Confidence intervals
- Trend detection (increasing/stable/decreasing)

**Output**:
```json
{
  "current_usage": 45,
  "limit": 60,
  "usage_percent": 75.0,
  "predicted_breach_time": "2025-01-24T12:30:00Z",
  "time_until_breach_seconds": 1200,
  "trend": "increasing",
  "confidence": 0.85
}
```

### 4. Alert System

Configurable alert thresholds with admin notifications:

**Thresholds**:
- Warning: 75% (default, configurable)
- Critical: 90% (default, configurable)

**Notification Channels**:
- Telegram channel messages
- Email (via notification service)
- Dashboard alerts

**Cooldown Period**:
- Prevents alert spam (default: 5 minutes)
- Per-account cooldown tracking

### 5. Real-time Dashboard

Web-based admin panel for monitoring and management:

**Pages**:
1. **Dashboard**: Overview with status cards
2. **Trends**: Usage charts and predictions
3. **Settings**: Alert configuration

**Features**:
- Real-time updates (30-second refresh)
- Account enable/disable
- Usage progress bars
- Breach time countdowns

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                       │
│         (React Admin - RateLimitsPage)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend API Routes                          │
│              (backend/src/api/routes/rate_limits.py)         │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Queue      │ │   Multi-     │ │   Rate       │
│   Service    │ │   Account    │ │   Predictor  │
│              │ │   Limiter    │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
                ┌───────────────┐
                │  Redis        │
                │  (State/Queue)│
                └───────────────┘
```

### Data Flow

1. **Request Ingestion**:
   ```
   Client → API → RateLimitQueueService → Redis Queue
   ```

2. **Priority Processing**:
   ```
   HIGH Priority → Immediate execution
   MEDIUM/LOW → Queue with priority score
   ```

3. **Account Selection**:
   ```
   MultiAccountRateLimiter → Select account → Check limits → Execute
   ```

4. **Prediction**:
   ```
   RateLimitPredictor → Track usage → Calculate trend → Store in Redis
   ```

5. **Monitoring**:
   ```
   Celery Tasks → Check thresholds → Trigger alerts → Update dashboard
   ```

---

## Setup & Configuration

### Prerequisites

- **Backend**: Python 3.10+, FastAPI, Redis
- **Frontend**: React 18+, TypeScript
- **Infrastructure**: PostgreSQL, Redis, Celery

### Installation

#### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start Redis (Docker)
docker run -d -p 6379:6379 redis:alpine

# Start Celery worker
celery -A src.celery_app worker -l info

# Start backend
uvicorn src.main:app --reload
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 3. Environment Configuration

Add to `backend/.env`:

```ini
# Rate Limit Settings
RATE_LIMIT_ALERT_WARNING_THRESHOLD=75
RATE_LIMIT_ALERT_CRITICAL_THRESHOLD=90
RATE_LIMIT_ALERT_ENABLED=true
RATE_LIMIT_ALERT_COOLDOWN_SECONDS=300
RATE_LIMIT_ALERT_CHANNELS=channel-1,channel-2

# Queue Settings
RATE_LIMIT_QUEUE_BATCH_SIZE=10
RATE_LIMIT_QUEUE_BATCH_TIMEOUT=5

# Multi-Account Settings
RATE_LIMIT_ACCOUNT_SELECTION_STRATEGY=least_used
RATE_LIMIT_MAX_ACCOUNTS=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Database Setup

The system uses existing PostgreSQL database. Required tables:
- `telegram_accounts` (multi-account pool)
- `rate_limit_history` (usage tracking)
- `alerts` (alert history)

Run migrations:
```bash
cd backend
alembic upgrade head
```

---

## Usage Guide

### Adding Accounts to Pool

#### Via API

```bash
curl -X POST http://localhost:8000/api/v1/rate-limits/accounts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "account-1",
    "phone": "+1234567890"
  }'
```

#### Via Dashboard

1. Navigate to `/admin/rate-limits`
2. Click "Accounts" tab
3. Click "Add Account"
4. Enter account ID and phone
5. Click "Add"

### Monitoring Rate Limits

#### Check Status

```bash
curl http://localhost:8000/api/v1/rate-limits/status \
  -H "Authorization: Bearer <token>"
```

#### Get Predictions

```bash
curl http://localhost:8000/api/v1/rate-limits/predictions \
  -H "Authorization: Bearer <token>"
```

### Configuring Alerts

#### Via API

```bash
curl -X PUT http://localhost:8000/api/v1/rate-limits/settings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_thresholds": {
      "warning_threshold_percent": 75.0,
      "critical_threshold_percent": 90.0
    },
    "notification_preferences": {
      "enabled": true,
      "channels": ["channel-1"],
      "notify_on_warning": true,
      "notify_on_critical": true,
      "cooldown_seconds": 300
    }
  }'
```

#### Via Dashboard

1. Navigate to `/admin/rate-limits`
2. Click "Settings" tab
3. Adjust thresholds
4. Configure notification channels
5. Click "Save"

### Queueing Requests

#### Python Backend

```python
from backend.src.services.rate_limit_queue_service import RateLimitQueueService
from backend.src.services.rate_limit_queue_service import RequestPriority

queue_service = RateLimitQueueService()

# High priority (stream control)
await queue_service.add_request(
    account_id="account-1",
    method="messages.send",
    priority=RequestPriority.HIGH,
    data={"chat_id": -100123456789, "text": "Playing next track"}
)

# Medium priority (metadata)
await queue_service.add_request(
    account_id="account-1",
    method="channels.get_full",
    priority=RequestPriority.MEDIUM,
    data={"channel": "mychannel"}
)

# Low priority (background)
await queue_service.add_request(
    account_id="account-1",
    method="users.get",
    priority=RequestPriority.LOW,
    data={"user_ids": [1, 2, 3]}
)
```

#### With Automatic Account Selection

```python
from backend.src.services.multi_account_rate_limiter import MultiAccountRateLimiter

limiter = MultiAccountRateLimiter()

# Automatically selects best account
account = await limiter.select_account()

# Use selected account for API call
result = await telegram_client(account.session_string).send_message(...)
```

---

## API Reference

See [API Documentation](../api/rate-limits.md) for complete API reference.

### Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/rate-limits/status` | GET | Get overall status |
| `/api/v1/rate-limits/metrics` | GET | Get detailed metrics |
| `/api/v1/rate-limits/predictions` | GET | Get predictions |
| `/api/v1/rate-limits/accounts` | GET | Get account pool |
| `/api/v1/rate-limits/accounts` | POST | Add account |
| `/api/v1/rate-limits/accounts/{id}` | PUT | Update account |
| `/api/v1/rate-limits/accounts/{id}` | DELETE | Remove account |
| `/api/v1/rate-limits/settings` | PUT | Update settings |
| `/api/v1/rate-limits/queue` | GET | Get queue stats |

---

## Dashboard

### Access

**URL**: `http://localhost:3000/admin/rate-limits`
**Required Role**: ADMIN or SUPERADMIN

### Overview Tab

**Cards**:
- Overall Status (healthy/warning/critical)
- Total Accounts
- Rate Limited Accounts
- Queue Size

**Account List**:
- Account ID with status badge
- Usage percentage with progress bar
- Health indicator
- Time until breach
- Enable/disable toggle

### Trends Tab

**Features**:
- Usage chart over time
- Predicted breach time countdown
- Statistics (avg/max/min usage)
- Detailed predictions table
- Auto-refresh (30s default)

### Queue Tab

**Statistics**:
- Total pending requests
- Processing requests
- Completed last minute
- Average wait time
- Breakdown by priority (HIGH/MEDIUM/LOW)

### Settings Tab

**Configuration**:
- Warning threshold (0-100%)
- Critical threshold (0-100%)
- Notification toggle
- Notification channels
- Cooldown period
- Auto-refresh interval

---

## Monitoring & Alerts

### Prometheus Metrics

Access at: `http://localhost:8000/metrics`

**Available Metrics**:

```prometheus
# Total API requests per account
telegram_api_requests_total{account_id="account-1", endpoint="messages"} 1234

# Remaining requests before limit
telegram_rate_limit_remaining{account_id="account-1"} 15

# Current usage percentage
telegram_account_usage_percent{account_id="account-1"} 75.0

# Queue size by priority
rate_limit_queue_size{priority="HIGH"} 10
rate_limit_queue_size{priority="MEDIUM"} 45
rate_limit_queue_size{priority="LOW"} 120

# Prediction breach time
rate_limit_prediction_breach_time{account_id="account-1"} 1200
```

### Grafana Dashboards

Import dashboard from `backend/metrics/grafana/rate-limits.json`:
- Account usage overview
- Prediction accuracy
- Queue processing rate
- Alert frequency

### Alert Configuration

#### Celery Task

Location: `backend/src/tasks/rate_limit_monitor.py`

Runs every 60 seconds:
1. Check all account usage
2. Calculate predictions
3. Trigger alerts if thresholds exceeded
4. Update Redis with latest data

#### Notification Channels

**Telegram**:
```python
await send_telegram_alert(
    channel_id="channel-1",
    message="⚠️ Account account-1 at 75% capacity. Predicted breach in 20 minutes."
)
```

**Email**:
```python
await send_email_alert(
    to="admin@example.com",
    subject="Rate Limit Warning: account-1",
    body="Account account-1 has reached 75% capacity..."
)
```

---

## Troubleshooting

### Common Issues

#### 1. Predictions Not Accurate

**Symptoms**: Predicted breach times are far off

**Diagnosis**:
```bash
# Check Redis has data
redis-cli
> KEYS rate_limit_prediction:*
> GET rate_limit_prediction:account-1
```

**Solutions**:
- Wait 1 hour for initial data collection
- Verify predictor task is running
- Check Redis memory usage

#### 2. Accounts Not Distributing Load

**Symptoms**: All requests go to one account

**Diagnosis**:
```bash
curl http://localhost:8000/api/v1/rate-limits/accounts
```

**Solutions**:
- Check account status (must be "active")
- Verify selection strategy is "least_used"
- Add more accounts to pool
- Check for disabled accounts

#### 3. Alerts Not Triggering

**Symptoms**: No alerts despite high usage

**Diagnosis**:
```bash
# Check alert settings
curl http://localhost:8000/api/v1/rate-limits/settings

# Check Celery task
celery -A src.celery_app inspect active | grep rate_limit
```

**Solutions**:
- Verify `RATE_LIMIT_ALERT_ENABLED=true`
- Check notification channels are configured
- Review alert cooldown period
- Verify task is scheduled in beat

#### 4. Queue Processing Slow

**Symptoms**: Requests pending for long time

**Diagnosis**:
```bash
# Check queue size
curl http://localhost:8000/api/v1/rate-limits/queue

# Check worker count
celery -A src.celery_app inspect active
```

**Solutions**:
- Increase Celery worker count: `celery worker -c 4`
- Adjust batch size in settings
- Check Redis performance
- Reduce request rate

### Debug Mode

Enable debug logging:

```ini
# .env
LOG_LEVEL=DEBUG
RATE_LIMIT_DEBUG=true
```

View logs:
```bash
# Backend logs
tail -f backend/logs/rate_limit.log

# Celery logs
tail -f backend/logs/celery.log
```

---

## Performance

### Benchmarks

Tested on: 2 vCPU, 4GB RAM, Redis 6.2

| Metric | Result | Target |
|--------|--------|--------|
| Queue Throughput | 1200 req/s | ≥1000 req/s |
| Add Latency (P50) | 0.3ms | <1ms |
| Add Latency (P95) | 2.1ms | <5ms |
| Add Latency (P99) | 4.5ms | <10ms |
| Prediction Accuracy | 87% | ≥80% |
| Status Endpoint | 45ms | <100ms |

### Optimization Tips

1. **Use Appropriate Priority**:
   - HIGH only for stream control (user-facing)
   - MEDIUM for metadata fetch (user-initiated)
   - LOW for background tasks (automatic)

2. **Maintain Account Pool**:
   - 3-5 accounts for redundancy
   - 10+ accounts for high volume
   - Rotate accounts periodically

3. **Configure Thresholds**:
   - Warning: 70-75% (early detection)
   - Critical: 85-90% (emergency action)

4. **Monitor Proactively**:
   - Set up Grafana dashboards
   - Configure alert channels
   - Review predictions daily

5. **Cache Predictions**:
   - Cache for 30 seconds
   - Revalidate on critical operations
   - Invalidate on account status change

---

## Security

### Authentication

All API endpoints require JWT authentication:
```http
Authorization: Bearer <token>
```

Tokens issued by: `backend/src/api/auth.py`

### Authorization

| Role | Access Level |
|------|--------------|
| USER | View only (status, predictions) |
| ADMIN | View + manage accounts + settings |
| SUPERADMIN | Full access |

### Rate Limiting

API endpoints are rate-limited per-user:
- Query endpoints: 60 req/min
- Metrics endpoints: 30 req/min
- Modifications: 20 req/min

### Data Privacy

- Account phone numbers stored encrypted
- Session strings never logged
- Usage data aggregated (not per-request)

### Audit Logging

All account management operations logged:
```json
{
  "user_id": 123,
  "action": "add_account",
  "account_id": "account-1",
  "timestamp": "2025-01-24T12:00:00Z",
  "ip": "192.168.1.1"
}
```

---

## Related Documentation

- [API Reference](../api/rate-limits.md)
- [Telegram Rate Limits](./TELEGRAM_RATE_LIMITS.md)
- [Deployment Guide](../deployment/rate-limit-setup.md)
- [Architecture Documentation](../architecture/rate-limit-architecture.md)

---

## Support

For issues and questions:
- GitHub Issues: [Project Repository]
- Documentation: [docs/](../)
- Architecture: [docs/architecture/](../architecture/)

---

## Changelog

### Version 1.0.0 (2026-01-24)

**Added**:
- ✅ Priority queue system (HIGH/MEDIUM/LOW)
- ✅ Multi-account rate limiter
- ✅ Rate limit predictor with ML
- ✅ Alert system with configurable thresholds
- ✅ Real-time dashboard (React)
- ✅ 9 REST API endpoints
- ✅ Prometheus metrics integration
- ✅ Celery monitoring tasks
- ✅ Comprehensive testing (E2E, integration, load)

**Performance**:
- 1000+ req/s throughput
- <1ms P50 latency
- 87% prediction accuracy

**Documentation**:
- API reference
- Setup guide
- Troubleshooting guide
- Performance benchmarks
