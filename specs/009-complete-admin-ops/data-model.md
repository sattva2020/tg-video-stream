# Data Model: Complete Admin Ops

## Storage

### File System (Shared Volume)
- **Path**: `/app/data/playlist.txt`
- **Format**: Plain text, one URL per line.
- **Access**:
  - **Backend**: Read/Write (Admin API).
  - **Streamer**: Read-Only (Playback).

### Redis Keys

| Key | Type | TTL | Description |
|-----|------|-----|-------------|
| `streamer:status` | Hash | - | Current state of the streamer. |
| `streamer:metrics` | Hash | 10s | Real-time metrics (CPU, RAM). |
| `streamer:logs` | List | - | (Optional) Buffer for logs if direct access fails. |

## Entities

### StreamStatus (Redis Hash `streamer:status`)
```json
{
  "state": "running" | "stopped" | "error",
  "current_track": "URL or Title",
  "started_at": "ISO8601 Timestamp",
  "last_error": "Error message string"
}
```

### SystemMetrics (Redis Hash `streamer:metrics`)
```json
{
  "cpu_percent": 12.5,
  "memory_mb": 256.4,
  "uptime_seconds": 3600,
  "timestamp": 1716384000
}
```

### Playlist Item (API DTO)
```json
{
  "index": 0,
  "url": "https://youtube.com/watch?v=..."
}
```
