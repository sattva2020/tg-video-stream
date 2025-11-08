# Implementation Plan: Production Broadcast Improvements

This plan implements the production hardening items described in `spec.md`:

- Session recovery with explicit auto-regeneration flow (interactive, --write-env flag)
- systemd unit hardening and automatic restarts (Restart=always, RestartSec=10)
- weekly yt-dlp updates via systemd-timer (Sunday 02:00 UTC, /var/log/yt-dlp-update.log)
- FFMPEG_ARGS support from `.env` (space-separated, double-quote escaping; fallback on invalid)
- `.env` ownership/permissions enforcement (600, tgstream:tgstream, atomic write)
- Prometheus basic metrics export (Counter, streams_played_total, port fallback on occupied)
- CI restart step with 60s timeout and Active state validation
- Degraded mode (SessionExpired → degraded → periodic regen attempts)

Tech stack and locations
- Python 3.12, per-release venv under `/opt/tg_video_streamer/releases/<ver>/venv`
- Runtime entrypoint: `main.py` in release root
- Deploy layout: `/opt/tg_video_streamer/releases/<ver>` symlinked to `/opt/tg_video_streamer/current`
- Prometheus exporter: port 9090 (default, configurable via PROMETHEUS_PORT in .env; fallback to next free port if occupied)

High-level steps (MVP first)
1. Add environment template and quickstart/docs for session regen.
2. Ensure deploy script enforces `.env` ownership/permissions (atomic write, 600, tgstream).
3. Provide systemd unit template with sandboxing and Restart policy.
4. Add systemd-timer + updater script for `yt-dlp` (weekly, Sunday 02:00 UTC, logging to /var/log/yt-dlp-update.log).
5. Add optional Prometheus exporter to `main.py` (type=Counter, streams_played_total, port fallback).
6. Add CI/Workflow snippet to restart service after deploy (60s timeout, validate Active, fail if not active).
7. Add degraded mode logic to `main.py` (SessionExpired → degraded, periodic regen attempts, operator notification).

Operational notes
- Deploy should be run as root (or a user with permissions to write `/opt/...` and restart systemd).
- CI user must be allowed to `sudo systemctl restart tg_video_streamer` without interactive password.
- `.env` is considered sensitive; deploy will set `chmod 600` and `chown tgstream:tgstream` atomically when the `tgstream` user exists on the host.
- Concurrent deploy + auto_session_runner.py execution must be avoided (add lock or CI sequencing).
- yt-dlp updates use current release symlink: `/opt/tg_video_streamer/current/venv/bin/pip install -U yt-dlp`.

Paths created/used by tasks
- `specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service`
- `specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.service`
- `specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.timer`
- `scripts/yt-dlp-update.sh` (activates venv, runs pip, logs to /var/log/yt-dlp-update.log)
- `.env.template` (with PROMETHEUS_PORT, FFMPEG_ARGS placeholders)
- `specs/002-prod-broadcast-improvements/quickstart.md`
- `main.py` (degraded mode, SessionExpired handling, Prometheus exporter)
- `utils.py` (FFMPEG_ARGS parsing)
- `test/auto_session_runner.py` (--write-env flag, atomic .env write)

MVP success criteria
- `scripts/remote_deploy.sh` sets `.env` to owner `tgstream` (if present) and `chmod 600` atomically.
- Systemd unit template includes `Restart=always`, `RestartSec=10`, sandboxing options, and can be enabled by copying to `/etc/systemd/system`.
- `main.py` handles SessionExpired, logs degraded mode, periodically attempts regen.
- Prometheus exporter runs on 9090 (or next free port + log WARNING), exports `streams_played_total` Counter.
- yt-dlp timer runs weekly (Sunday 02:00 UTC), logs to `/var/log/yt-dlp-update.log`, failures logged but non-fatal.
