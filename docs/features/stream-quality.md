# Stream Quality Monitoring (Spec 022)

## Overview
The Stream Quality Monitoring feature provides real-time and historical analysis of audio/video stream performance. It allows administrators to monitor bitrate, FPS, and overall quality scores to ensure high availability and listener satisfaction.

## Features

### 1. Real-time Monitoring
- **Status**: Online/Offline indicator.
- **Bitrate**: Current bitrate in kbps (Audio + Video).
- **FPS**: Frames per second (for video streams).
- **Quality Score**: Automated quality assessment (Low, Medium, High, Lossless, Ultra).

### 2. Historical Analysis
- **Charts**: Interactive line charts showing bitrate and FPS trends over time.
- **Periods**: Selectable time ranges (1h, 6h, 12h, 24h, 7d).
- **Data Retention**: Detailed metrics stored for 30 days.

### 3. Alerting
- **Thresholds**: Configurable minimum quality levels.
- **Notifications**: Alerts triggered on quality degradation or stream failure.
- **Recovery**: Automatic notification when stream recovers.

## Technical Implementation

### Backend
- **Service**: `StreamQualityService` uses FFprobe to analyze stream metrics.
- **Storage**: `StreamQualityHistory` table stores time-series data.
- **API**:
  - `GET /api/admin/stream-quality/current`: Real-time status.
  - `GET /api/admin/stream-quality/history`: Historical data.
  - `GET/PUT /api/admin/stream-quality/alerts`: Alert configuration.

### Frontend
- **Widget**: `StreamHealthWidget` displays current metrics.
- **Chart**: `StreamQualityHistoryChart` visualizes trends using Recharts.
- **Page**: `/admin/stream-quality` aggregates all monitoring tools.

## Configuration
Alerts can be configured via the API (UI coming soon in Phase 4.1):
```json
{
  "stream_url": "http://example.com/stream",
  "min_overall_quality": "medium",
  "consecutive_failures": 3,
  "enabled": true
}
```

## Troubleshooting
- **No Data**: Ensure the stream URL is correct and accessible from the server.
- **"Stream Unavailable"**: Check if the stream source is online.
- **High Latency**: Check server network connection and FFprobe timeout settings.
