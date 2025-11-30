# Quickstart: Complete Admin Ops

## Prerequisites

- Docker & Docker Compose installed.
- Python 3.11+ (for local dev).

## Configuration

1. **Environment Variables**:
   Add to `.env`:
   ```bash
   # Stream Controller Type: 'docker' or 'systemd'
   STREAM_CONTROLLER_TYPE=docker
   # Container name (if using docker controller)
   STREAM_CONTAINER_NAME=telegram-streamer-1
   # Service name (if using systemd controller)
   STREAM_SERVICE_NAME=tg_video_streamer
   # FFmpeg Arguments
   FFMPEG_ARGS="-re -preset ultrafast"
   ```

2. **Shared Volume**:
   Ensure `docker-compose.yml` mounts a shared volume for playlist:
   ```yaml
   volumes:
     - ./data:/app/data
   ```

## Running Locally

1. **Start Stack**:
   ```bash
   docker-compose up -d
   ```

2. **Access Admin Panel**:
   - Open `http://localhost:3000/admin/dashboard`.
   - Login as admin.

3. **Test Controls**:
   - Click "Restart Stream". Check logs: `docker logs -f telegram-streamer-1`.
   - Edit Playlist: Add a URL, save. Check file: `cat data/playlist.txt`.

## Troubleshooting

- **Permission Denied (Restart)**: Ensure the backend container has access to Docker socket (`/var/run/docker.sock`) if using `docker` controller.
  ```yaml
  backend:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
  ```
- **Metrics Missing**: Check Redis connection in Streamer logs.
