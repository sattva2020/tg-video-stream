# Specification: Stream Quality Monitoring (Spec 022)

## 1. Introduction
**Goal**: Provide real-time monitoring and historical analysis of audio stream quality to ensure high availability and listener satisfaction.
**Scope**: Backend monitoring service, database storage for metrics, and frontend visualization for Admins.

## 2. User Stories
- **US1**: As an Admin, I want to see the current status of the stream (Online/Offline, Bitrate, Listeners) on the dashboard.
- **US2**: As an Admin, I want to receive notifications (Telegram/Email) if the stream goes offline or bitrate drops below a threshold.
- **US3**: As an Admin, I want to view historical charts of stream stability (uptime, dropouts) to identify patterns.

## 3. Technical Requirements
### Backend
- **Metrics Collection**:
  - Periodically check stream URL (Icecast/HLS).
  - Record: Status (200 OK), Response Time, Bitrate (if possible), Buffer health.
- **Storage**:
  - Store metrics in TimescaleDB (or existing Postgres with time-series approach).
  - Retention policy: 30 days for detailed data, 1 year for aggregated.
- **Alerting**:
  - Background worker (Celery/APScheduler) to check thresholds.
  - Integration with Notification Service (Spec 001/021).

### Frontend
- **Real-time Widget**:
  - "Live" indicator.
  - Current Bitrate / Format.
- **Quality Chart**:
  - Line chart showing uptime/response time over last 24h.
- **Logs**:
  - Table of recent "Incidents" (Stream restarts, buffer underruns).

## 4. API Design
- `GET /api/monitoring/stream/status` - Current snapshot.
- `GET /api/monitoring/stream/history?from=...&to=...` - Historical data for charts.
- `GET /api/monitoring/incidents` - List of detected issues.

## 5. Data Model
### `StreamMetric`
- `id`: UUID
- `timestamp`: DateTime
- `stream_id`: UUID (FK)
- `is_online`: Boolean
- `response_time_ms`: Integer
- `bitrate_kbps`: Integer (optional)
- `listeners_count`: Integer

### `StreamIncident`
- `id`: UUID
- `start_time`: DateTime
- `end_time`: DateTime (nullable)
- `type`: Enum (OFFLINE, LOW_BITRATE, HIGH_LATENCY)
- `description`: String

## 6. Security
- Only `ADMIN` and `SUPERADMIN` can access monitoring data.
- Internal monitoring worker needs `INTERNAL_API_TOKEN` if accessing protected internal streams.
