# Feature 022 Phase 3: Advanced Stream Quality Monitoring

**Last Updated**: December 16, 2025  
**Status**: ✅ IMPLEMENTATION COMPLETE  
**Phase**: 3/3  
**Related**: [Feature 022 Phase 2 Documentation](./feature-022-phase2-real-time-monitoring.md)

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [React Components](#react-components)
6. [Configuration Guide](#configuration-guide)
7. [Usage Examples](#usage-examples)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)
10. [Deployment Checklist](#deployment-checklist)

## Overview

Feature 022 Phase 3 introduces **Advanced Stream Quality Monitoring** with historical trend analysis and intelligent alert configuration. Building on Phase 2's real-time quality metrics, Phase 3 enables:

- ✅ **24-hour Quality Trends** — Visualize quality patterns over time with statistics
- ✅ **Alert Configuration** — Set per-stream quality thresholds with flexible options
- ✅ **Historical Data** — Track quality metrics with hourly aggregates for fast queries
- ✅ **Intelligent Alerts** — Avoid false alarms with consecutive failure counters
- ✅ **Recovery Notifications** — Alert operators when quality improves

## Architecture

### Components Overview

```
Frontend                           Backend                         Database
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AdminDashboard/Metrics                             │
│                          (Phase 2 + Phase 3 Tabs)                           │
├──────────────────────────────┬──────────────────────────────────────────────┤
│                              │                                              │
│  ┌────────────────────────┐  │  ┌─────────────────────────────────────────┐ │
│  │ StreamQualityChart     │  │  │ QualityTrendsService (Singleton)        │ │
│  │ (Phase 3 - Trends Tab) │◄─┤◄─┤ • record_quality_analysis()            │ │
│  │ • Statistics Grid      │  │  │ • get_quality_trend(hours)             │ │
│  │ • Loading/Error States │  │  │ • set_alert_config()                   │ │
│  │ • Chart Placeholder    │  │  │ • _check_and_trigger_alerts()          │ │
│  └────────────────────────┘  │  └─────────────────────────────────────────┘ │
│                              │                                              │
│  ┌────────────────────────┐  │  ┌─────────────────────────────────────────┐ │
│  │StreamQualityAlert      │  │  │ FastAPI Admin Router                    │ │
│  │Settings                │  │  │ GET /api/admin/stream/quality/trend/*   │ │
│  │(Phase 3 - Alerts Tab)  │◄─┤◄─┤ POST /api/admin/stream/quality/cfg      │ │
│  │ • Quality Thresholds   │  │  │ GET /api/admin/stream/quality/cfg/*     │ │
│  │ • Advanced Bitrate     │  │  └─────────────────────────────────────────┘ │
│  │ • Alert Channels       │  │                                              │
│  │ • Save Configuration   │  │  ┌─────────────────────────────────────────┐ │
│  └────────────────────────┘  │  │ SQLAlchemy Models                       │ │
│                              │  │ • StreamQualityHistory (time-series)    │ │
│  ┌────────────────────────┐  │  │ • QualityAlertConfig (per-stream cfg)   │ │
│  │ StreamQualityBadge     │  │  │ • QualityTrendSnapshot (hourly agg)     │ │
│  │ (Phase 2 - Quality Tab)│  │  └─────────────────────────────────────────┘ │
│  │ • Current Metrics      │  │                                              │
│  └────────────────────────┘  │                                              │
│                              │                                              │
└─────────────────────────────────────────────────────────────────────────────┘
         Metrics Tab Interface (Quality | Trends | Alerts)
```

### Data Flow

```
Quality Analysis (FFprobe)
        ↓
QualityTrendsService.record_quality_analysis()
        ↓
StreamQualityHistory (saves raw data)
        ↓
Consecutive Failure Counter
        ↓
Alert Threshold Check
        ├─→ Alert Triggered → QualityAlertEvent
        └─→ No Alert (within threshold)
        ↓
Next Hour: QualityTrendSnapshot (hourly aggregation)
        ↓
Frontend: StreamQualityChart (fetches trends + stats)
          StreamQualityAlertSettings (loads/updates config)
```

## Database Schema

### Table: `stream_quality_history`

Time-series table storing detailed quality metrics for every analysis run (typically every 5 minutes).

```sql
CREATE TABLE stream_quality_history (
  -- Identifiers
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stream_url VARCHAR(255) INDEXED,
  stream_name VARCHAR(255),
  
  -- Audio Metrics
  audio_quality VARCHAR(20),          -- 'excellent', 'high', 'medium', 'low', 'poor'
  audio_bitrate_kbps INT,
  
  -- Video Metrics
  video_quality VARCHAR(20),          -- same quality levels
  video_bitrate_kbps INT,
  video_resolution VARCHAR(50),       -- e.g., '1920x1080'
  video_fps INT,
  
  -- Overall Assessment
  overall_quality VARCHAR(20) INDEXED,
  success BOOLEAN,                    -- Whether analysis succeeded
  error_message VARCHAR(500),
  
  -- Time & Data
  analyzed_at DATETIME INDEXED,       -- When analysis was run
  raw_data JSON,                      -- Full FFprobe output (optional)
  
  UNIQUE KEY unique_analysis (stream_url, analyzed_at)
);
```

**Indexes**: `stream_url`, `analyzed_at`, `overall_quality`

**Purpose**: Store individual quality measurements for trend analysis and historical reporting.

**Retention**: Keep for 30 days; archive older data.

### Table: `quality_alert_configs`

Per-stream configuration for alert thresholds and behavior.

```sql
CREATE TABLE quality_alert_configs (
  -- Identifiers
  id INT PRIMARY KEY AUTO_INCREMENT,
  stream_url VARCHAR(255) UNIQUE,
  stream_name VARCHAR(255),
  
  -- Quality Thresholds
  min_overall_quality VARCHAR(20),    -- e.g., 'high', 'medium'
  min_audio_quality VARCHAR(20),
  min_video_quality VARCHAR(20),
  
  -- Bitrate Thresholds (advanced)
  min_audio_bitrate_kbps INT,         -- NULL = no check
  min_video_bitrate_kbps INT,
  min_video_fps INT,
  min_video_resolution VARCHAR(50),
  
  -- Alert Behavior
  enabled BOOLEAN DEFAULT TRUE,
  notify_on_degradation BOOLEAN,
  notify_on_recovery BOOLEAN,
  consecutive_failures_threshold INT, -- How many failures before alert
  
  -- Alert Channels
  alert_channels JSON,                -- e.g., {"telegram": ["@admin"], "email": ["ops@site.com"]}
  
  -- Metadata
  last_alert_at DATETIME,
  last_alert_type VARCHAR(50),        -- 'degradation' or 'recovery'
  consecutive_failures_count INT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP
);
```

**Indexes**: `stream_url`

**Purpose**: Store per-stream alert configuration. Each stream can have unique thresholds.

### Table: `quality_trend_snapshots`

Hourly aggregates of quality data for fast graph queries (avoids scanning 288 history records).

```sql
CREATE TABLE quality_trend_snapshots (
  -- Identifiers
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stream_url VARCHAR(255) INDEXED,
  
  -- Time Bucket
  hour DATETIME INDEXED,              -- e.g., 2025-12-16 14:00:00
  
  -- Aggregates
  overall_quality_avg VARCHAR(20),
  overall_quality_min VARCHAR(20),
  audio_quality_avg VARCHAR(20),
  audio_quality_min VARCHAR(20),
  audio_bitrate_avg_kbps INT,
  video_quality_avg VARCHAR(20),
  video_quality_min VARCHAR(20),
  video_bitrate_avg_kbps INT,
  video_fps_avg INT,
  
  -- Success Metrics
  success_count INT,
  total_analyses INT,
  success_rate DECIMAL(5,2),          -- Percentage 0-100
  
  UNIQUE KEY unique_snapshot (stream_url, hour)
);
```

**Indexes**: `stream_url`, `hour`

**Purpose**: Provide fast queries for 24-hour trend visualization without scanning history table.

**Generation**: Automatically created hourly by QualityTrendsService after recording analyses.

## API Endpoints

### 1. Get Quality Trend (24-hour)

**Endpoint**: `GET /api/admin/stream/quality/trend/{stream_url}`

**Authentication**: Required (admin role)

**Query Parameters**:
- `hours` (optional, default=24): Number of hours to retrieve (1-168)

**Response**: `QualityTrendData`

```json
{
  "stream_url": "http://stream.local/video",
  "stream_name": "Main Studio Stream",
  "history": [
    {
      "timestamp": "2025-12-16T01:00:00Z",
      "overall_quality": "high",
      "audio_quality": "high",
      "audio_bitrate_kbps": 128,
      "video_quality": "high",
      "video_bitrate_kbps": 2500,
      "video_resolution": "1920x1080",
      "video_fps": 30,
      "success": true
    },
    // ... more data points (24 points for 24 hours if hourly aggregation)
  ],
  "average_quality": "high",
  "min_quality": "medium",
  "max_quality": "high",
  "audio_avg_bitrate_kbps": 127,
  "video_avg_bitrate_kbps": 2498,
  "success_rate": 0.954,
  "period_start": "2025-12-15T01:00:00Z",
  "period_end": "2025-12-16T01:00:00Z",
  "samples_count": 288
}
```

**Example curl**:
```bash
curl -X GET "http://localhost:8000/api/admin/stream/quality/trend/http%3A%2F%2Fstream.local%2Fvideo?hours=24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Use Case**: Display 24-hour trend graph with statistics.

### 2. Set Alert Configuration

**Endpoint**: `POST /api/admin/stream/quality/alert/config`

**Authentication**: Required (admin role)

**Request Body**: `QualityAlertConfigUpdate`

```json
{
  "stream_url": "http://stream.local/video",
  "stream_name": "Main Studio Stream",
  "min_overall_quality": "high",
  "min_audio_quality": "high",
  "min_video_quality": "high",
  "min_audio_bitrate_kbps": 100,
  "min_video_bitrate_kbps": 2000,
  "min_video_fps": 25,
  "min_video_resolution": "1280x720",
  "enabled": true,
  "notify_on_degradation": true,
  "notify_on_recovery": true,
  "consecutive_failures_threshold": 3,
  "alert_channels": {
    "telegram": ["@admin_channel"],
    "email": ["ops@example.com"]
  }
}
```

**Response**: `QualityAlertConfigResponse`

```json
{
  "id": 42,
  "stream_url": "http://stream.local/video",
  "stream_name": "Main Studio Stream",
  "min_overall_quality": "high",
  // ... all request fields
  "last_alert_at": "2025-12-16T00:15:00Z",
  "last_alert_type": "degradation",
  "consecutive_failures_count": 2,
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-16T01:30:00Z"
}
```

**Example curl**:
```bash
curl -X POST "http://localhost:8000/api/admin/stream/quality/alert/config" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_url": "http://stream.local/video",
    "min_overall_quality": "high",
    "enabled": true,
    "consecutive_failures_threshold": 3
  }'
```

**Use Case**: Create or update alert configuration for a stream.

### 3. Get Alert Configuration

**Endpoint**: `GET /api/admin/stream/quality/alert/config/{stream_url}`

**Authentication**: Required (admin role)

**Response**: `QualityAlertConfigResponse` or `null`

**Example curl**:
```bash
curl -X GET "http://localhost:8000/api/admin/stream/quality/alert/config/http%3A%2F%2Fstream.local%2Fvideo" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200)**: Full config object
**Response (404 equivalent)**: `null`

**Use Case**: Load current configuration for editing.

## React Components

### StreamQualityChart

Displays 24-hour quality trends with statistics.

**Location**: `frontend/src/components/dashboard/StreamQualityChart.tsx`

**Props**:
```typescript
interface StreamQualityChartProps {
  streamUrl: string;
  streamName?: string;
  hours?: number;              // default: 24
  loading?: boolean;
  error?: string;
  onDataLoaded?: (data: QualityTrendData) => void;
}
```

**Features**:
- Loading spinner with "Loading trend data..." text
- Error alert with error message
- Statistics grid (Avg/Max/Min Quality, Success Rate)
- Data summary table
- Chart placeholder (ready for Recharts library integration)

**Example Usage**:
```tsx
import StreamQualityChart from './components/dashboard/StreamQualityChart';

export function TrendsTab() {
  return (
    <StreamQualityChart
      streamUrl="http://stream.local/video"
      streamName="Main Stream"
      hours={24}
      onDataLoaded={(data) => console.log('Data:', data)}
    />
  );
}
```

**Styling**: Full Tailwind CSS responsive design with grid layout.

### StreamQualityAlertSettings

Configure quality alert thresholds for a stream.

**Location**: `frontend/src/components/dashboard/StreamQualityAlertSettings.tsx`

**Props**:
```typescript
interface StreamQualityAlertSettingsProps {
  streamUrl: string;
  streamName?: string;
  onSave?: (config: QualityAlertConfigUpdate) => Promise<void>;
  loading?: boolean;
  error?: string;
}
```

**Features**:
- Enable/disable toggle
- Quality threshold selectors (Overall, Audio, Video)
- Advanced section:
  - Bitrate thresholds (Audio, Video)
  - Video resolution dropdown
  - Video FPS input
- Alert behavior toggles (degradation, recovery)
- Consecutive failures counter
- Save button with loading state
- Success/error messages with auto-dismiss (5s)
- Info box with alert mechanism explanation

**Example Usage**:
```tsx
import StreamQualityAlertSettings from './components/dashboard/StreamQualityAlertSettings';

export function AlertsTab() {
  const handleSave = async (config) => {
    await adminApi.setQualityAlertConfig(config);
  };

  return (
    <StreamQualityAlertSettings
      streamUrl="http://stream.local/video"
      streamName="Main Stream"
      onSave={handleSave}
    />
  );
}
```

**Styling**: Full Tailwind CSS form styling with expandable advanced section.

### Metrics Tab Integration

The main `Metrics.tsx` component now includes Phase 3 tabs.

**Tabs**:
1. **Current Quality (Phase 2)** → StreamQualityBadge
2. **Trend Analysis (Phase 3)** → StreamQualityChart
3. **Alert Settings (Phase 3)** → StreamQualityAlertSettings

**Tab Styling**:
- Active: Blue border-bottom, blue text
- Inactive: Transparent border, gray text
- Hover: Smooth transition

## Configuration Guide

### Quality Levels

Quality is assessed on a 5-level scale:

```
'excellent'  (>=4.8/5 score)
'high'       (4.0-4.7/5 score)
'medium'     (2.5-3.9/5 score)
'low'        (1.0-2.4/5 score)
'poor'       (<1.0/5 score)
```

**Score Calculation** (from Phase 2):
```
base_score = 5.0
if audio_bitrate < min: base_score -= 0.5
if video_bitrate < min: base_score -= 0.5
if video_fps < 24: base_score -= 1.0
if video_resolution < target: base_score -= 0.5
...
```

### Setting Thresholds

**Conservative (High Quality)**:
```json
{
  "min_overall_quality": "high",
  "min_audio_quality": "high",
  "min_video_quality": "high",
  "min_audio_bitrate_kbps": 128,
  "min_video_bitrate_kbps": 2500,
  "consecutive_failures_threshold": 2
}
```

**Moderate (Standard)**:
```json
{
  "min_overall_quality": "medium",
  "min_audio_quality": "high",
  "min_video_quality": "medium",
  "min_audio_bitrate_kbps": 64,
  "min_video_bitrate_kbps": 1500,
  "consecutive_failures_threshold": 3
}
```

**Permissive (Best-effort)**:
```json
{
  "min_overall_quality": "medium",
  "min_audio_quality": "medium",
  "min_video_quality": "low",
  "min_audio_bitrate_kbps": null,
  "min_video_bitrate_kbps": null,
  "consecutive_failures_threshold": 5
}
```

### Consecutive Failures Threshold

**Why?** Avoid alerts on temporary network hiccups.

**Recommendation**:
- Conservative streams: 2-3 failures
- Standard streams: 3-4 failures  
- Tolerant streams: 5+ failures

**Example**: With threshold=3, alert only triggers after 3 consecutive quality failures within 15 minutes.

## Usage Examples

### Example 1: View 24-hour Trend

```typescript
// In StreamQualityChart component
const [trend, setTrend] = useState<QualityTrendData | null>(null);

useEffect(() => {
  adminApi.getQualityTrend('http://stream.local/video', 24)
    .then(setTrend)
    .catch(console.error);
}, []);

// Render chart with trend data
```

### Example 2: Configure Alerts for High-Quality Stream

```typescript
const config: QualityAlertConfigUpdate = {
  stream_url: 'http://stream.local/video',
  min_overall_quality: 'high',
  min_audio_quality: 'high',
  min_video_quality: 'high',
  enabled: true,
  notify_on_degradation: true,
  notify_on_recovery: true,
  consecutive_failures_threshold: 2,
  alert_channels: {
    telegram: ['@broadcast_alerts'],
    email: ['ops@broadcast.tv']
  }
};

await adminApi.setQualityAlertConfig(config);
```

### Example 3: Load Existing Config for Editing

```typescript
const config = await adminApi.getQualityAlertConfig('http://stream.local/video');
if (config) {
  setFormValues(config);
} else {
  // Config doesn't exist yet, use defaults
  setFormValues({
    stream_url: 'http://stream.local/video',
    min_overall_quality: 'medium',
    consecutive_failures_threshold: 3,
    enabled: true,
    notify_on_degradation: true,
    notify_on_recovery: false
  });
}
```

## Performance Optimization

### Query Optimization

**Problem**: Querying 288 hourly history records for 24-hour graph is slow.

**Solution**: Use `QualityTrendSnapshot` (hourly aggregates).

```python
# Fast query (1 table scan)
snapshots = db.query(QualityTrendSnapshot) \
  .filter(QualityTrendSnapshot.stream_url == url) \
  .filter(QualityTrendSnapshot.hour >= cutoff) \
  .order_by(QualityTrendSnapshot.hour) \
  .all()  # 24 rows max

# Slow query (288 rows)
history = db.query(StreamQualityHistory) \
  .filter(StreamQualityHistory.stream_url == url) \
  .filter(StreamQualityHistory.analyzed_at >= cutoff) \
  .all()  # 288 rows with aggregation
```

### Indexing Strategy

All tables have proper indexes on frequently queried columns:

```sql
-- StreamQualityHistory
CREATE INDEX idx_stream_url ON stream_quality_history(stream_url);
CREATE INDEX idx_analyzed_at ON stream_quality_history(analyzed_at);
CREATE INDEX idx_overall_quality ON stream_quality_history(overall_quality);

-- QualityAlertConfigs
CREATE UNIQUE INDEX idx_stream_url ON quality_alert_configs(stream_url);

-- QualityTrendSnapshots
CREATE INDEX idx_stream_url ON quality_trend_snapshots(stream_url);
CREATE INDEX idx_hour ON quality_trend_snapshots(hour);
```

### Data Retention

**Recommendation**:
- Keep history for 30 days (for trend analysis & reports)
- Keep snapshots for 90 days
- Archive older data for compliance

```sql
-- Delete old history (30+ days)
DELETE FROM stream_quality_history
WHERE analyzed_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Delete old snapshots (90+ days)
DELETE FROM quality_trend_snapshots
WHERE hour < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

## Troubleshooting

### Issue: Alerts firing too frequently

**Causes**:
- Threshold too low
- Consecutive failures counter too low

**Solution**:
```json
{
  "consecutive_failures_threshold": 5,  // Increase from 3
  "min_overall_quality": "medium"       // Lower from high
}
```

### Issue: Missing trend data

**Causes**:
- Analyses not being recorded
- QualityTrendsService not called

**Debugging**:
```python
# Check if history exists
history_count = db.query(StreamQualityHistory) \
  .filter(StreamQualityHistory.stream_url == url) \
  .filter(StreamQualityHistory.analyzed_at >= cutoff) \
  .count()

if history_count == 0:
  logger.warning(f"No quality history for {url}")
```

### Issue: Alert configuration not saving

**Causes**:
- Database connection error
- Validation failure
- Permission issue

**Debugging**:
```python
try:
  config = await trends_service.set_alert_config(db, config_update)
except SQLAlchemyError as e:
  logger.error(f"Database error: {e}")
except ValidationError as e:
  logger.error(f"Validation error: {e.errors()}")
```

## Deployment Checklist

### Pre-Deployment

- [ ] Alembic migration tested locally (`alembic upgrade head`)
- [ ] All backend tests passing (`pytest backend/tests/api/test_quality_trends.py`)
- [ ] All frontend tests passing (`npm test`)
- [ ] Code review completed
- [ ] Database backup created

### Deployment Steps

1. **Database Migration**
   ```bash
   # On production server
   cd /app && alembic upgrade head
   # Verifies: Tables created, indexes created
   ```

2. **Backend Deployment**
   ```bash
   # Restart backend service
   docker compose up -d backend
   
   # Verify service health
   curl http://localhost:8000/api/admin/health
   ```

3. **Frontend Deployment**
   ```bash
   # Build and deploy frontend
   cd frontend && npm run build
   docker compose up -d frontend
   
   # Verify tabs visible in metrics page
   ```

4. **Verification**
   - [ ] Navigate to Admin > Metrics
   - [ ] Verify 3 tabs visible (Quality, Trends, Alerts)
   - [ ] Click "Trend Analysis" tab
   - [ ] Verify chart loads (even with placeholder)
   - [ ] Click "Alert Settings" tab
   - [ ] Verify form loads
   - [ ] Try updating alert config
   - [ ] Check backend logs for errors

### Post-Deployment

- [ ] Monitor error logs for next 24 hours
- [ ] Verify daily alert-triggering scenarios
- [ ] Test trend data accumulation

## Next Steps

### Phase 4 Recommendations

1. **Chart Library Integration**
   - Replace chart placeholder with Recharts
   - Add interactive hover tooltips
   - Implement zoom/pan controls

2. **ML Quality Prediction**
   - Analyze historical trends
   - Predict quality degradation 1-2 hours in advance
   - Alert operators before actual degradation

3. **Advanced Alert Channels**
   - Add Slack integration
   - Add PagerDuty integration
   - Add Webhook support for custom integrations

4. **Reporting & Analytics**
   - Generate daily/weekly quality reports
   - SLA tracking and reporting
   - Quality metrics exports (CSV, JSON)

5. **User Experience Improvements**
   - One-click alert presets ("High Quality", "Standard", "Tolerant")
   - Alert history log
   - Alert acknowledgment & escalation

## Appendix: Data Model References

### QualityHistoryPoint

```typescript
interface QualityHistoryPoint {
  timestamp: string;              // ISO 8601 format
  overall_quality: 'excellent' | 'high' | 'medium' | 'low' | 'poor';
  audio_quality?: string;
  audio_bitrate_kbps?: number;
  video_quality?: string;
  video_bitrate_kbps?: number;
  video_resolution?: string;      // e.g., '1920x1080'
  video_fps?: number;
  success: boolean;
  error_message?: string;
}
```

### QualityAlertConfigUpdate

```typescript
interface QualityAlertConfigUpdate {
  stream_url: string;
  stream_name?: string;
  min_overall_quality?: string;
  min_audio_quality?: string;
  min_video_quality?: string;
  min_audio_bitrate_kbps?: number;
  min_video_bitrate_kbps?: number;
  min_video_fps?: number;
  min_video_resolution?: string;
  enabled?: boolean;
  notify_on_degradation?: boolean;
  notify_on_recovery?: boolean;
  consecutive_failures_threshold?: number;
  alert_channels?: Record<string, string[]>;
}
```

---

**Document Version**: 1.0  
**Last Updated**: December 16, 2025  
**Author**: System Architecture Team  
**Status**: ✅ Complete & Production-Ready
