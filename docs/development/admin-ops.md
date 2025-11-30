# Admin Operations Guide

This guide describes the administrative operations available for the Telegram Video Streamer.

## Stream Control

The Admin Dashboard provides controls to manage the streamer service directly.

### Actions
- **Start**: Starts the streamer service if it is stopped.
- **Stop**: Stops the streamer service.
- **Restart**: Restarts the streamer service. This is useful for applying configuration changes or recovering from errors.

### API Endpoints
- `POST /admin/stream/control`: Accepts JSON `{ "action": "start" | "stop" | "restart" }`.

## Monitoring

### Logs
Real-time logs from the streamer service are available in the "Logs" tab of the dashboard.
- **API**: `GET /admin/stream/logs?lines=100`

### Metrics
System resource usage (CPU and RAM) for the streamer container is visualized in the "Metrics" tab.
- **API**: `GET /admin/stream/metrics`
- **Source**: Redis (collected via `psutil` inside the streamer container).

## Playlist Management

The playlist determines the sequence of videos played by the streamer.
- **Location**: `playlist.txt` in the shared data volume.
- **Management**: Use the "Playlist" tab in the dashboard to add, remove, or reorder videos.
- **Format**: Simple text file with one URL per line.
- **API**:
  - `GET /admin/playlist`: Returns the current list.
  - `POST /admin/playlist`: Updates the list with a new array of URLs.

## Auto-Session Recovery

The system includes a mechanism to attempt recovery if the Telegram session expires or becomes invalid.
- **Trigger**: Automatic upon `SessionExpired` or `AuthKeyInvalid` exceptions.
- **Action**:
  1. Logs a critical alert.
  2. Writes a status file (`session_status`).
  3. Restarts the streamer process to attempt a fresh connection.
- **Note**: If the session is permanently revoked (e.g., user logged out all sessions), manual intervention (re-login) is required.

## Extended Configuration

### FFmpeg Arguments
You can inject custom FFmpeg arguments via the `FFMPEG_ARGS` environment variable.
- **Usage**: Add `FFMPEG_ARGS="-preset veryfast -tune zerolatency"` to your `.env` file.
- **Application**: These arguments are appended to the video encoding parameters.

## Security

All admin endpoints are protected and require authentication. Ensure your admin user has the appropriate roles/permissions.
