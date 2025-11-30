# Research: Complete Admin Ops

## 1. Stream Control & Logs (Docker vs Systemd)

**Problem**: The system must support restarting the streamer and reading logs in both Docker (Dev/Prod) and Systemd (Prod) environments.
**Constraint**: Backend might run in a container while Streamer runs on host (Systemd), or both in containers.

### Analysis
- **Docker**:
  - Restart: `docker restart <container_id>` (Requires Docker Socket access).
  - Logs: `docker logs --tail N <container_id>`.
- **Systemd**:
  - Restart: `sudo systemctl restart tg_video_streamer`.
  - Logs: `journalctl -u tg_video_streamer -n N --no-pager`.

### Decision
Implement a **Strategy Pattern** for `StreamController`:
- `DockerStreamController`: Uses `docker` python SDK or subprocess to control container.
- `SystemdStreamController`: Uses `subprocess` to call `systemctl`/`journalctl`.
- Configuration: `STREAM_CONTROLLER_TYPE=docker|systemd`.

## 2. Playlist Management (Shared State)

**Problem**: Backend needs to edit `playlist.txt` which is read by Streamer. In Docker, they have isolated filesystems.
**Solution**: Use a **Shared Volume**.
- Create a named volume `streamer_data` or host mount `./data`.
- Mount to `/app/data` in both Backend and Streamer.
- Move `playlist.txt` to `/app/data/playlist.txt`.

## 3. Metrics (Observability)

**Problem**: Backend cannot easily read CPU/RAM of a separate process/container.
**Solution**: **Push Model via Redis**.
- Streamer runs a background thread (`MetricsCollector`).
- Every 5 seconds, it collects `psutil` data and pushes to Redis key `streamer:metrics`.
- Backend reads from Redis.
- **Benefit**: Decoupled, works for both Docker and Systemd.

## 4. Auto-Session Recovery

**Problem**: `SessionExpired` requires re-authentication.
**Approach**:
- `auto_session_runner.py` will be a standalone script.
- Streamer catches `SessionExpired`, logs error, and executes this script.
- **Scope**: For this feature, the script will verify environment variables (`API_ID`, `API_HASH`, `PHONE`) and attempt to generate a new session file if possible (e.g., using a stored refresh token or just restarting if it was a glitch). *Note: Full automated login with 2FA is complex; MVP will focus on restart/alert.*

## 5. FFmpeg Arguments

**Problem**: Hardcoded arguments in `utils.py`.
**Solution**:
- Read `os.getenv("FFMPEG_ARGS")`.
- Parse string to list (e.g., using `shlex.split`).
- Inject into `ffmpeg` command construction.
