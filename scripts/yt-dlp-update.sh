#!/usr/bin/env bash
set -euo pipefail

LOG=/var/log/yt-dlp-update.log
RELEASE_CURRENT=/opt/tg_video_streamer/current
VENV_ACTIVATE="$RELEASE_CURRENT/venv/bin/activate"

echo "[yt-dlp-update] Starting at $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOG"
if [ -f "$VENV_ACTIVATE" ]; then
  # shellcheck source=/dev/null
  source "$VENV_ACTIVATE"
  echo "[yt-dlp-update] Running pip install -U yt-dlp" >> "$LOG"
  python -m pip install -U yt-dlp >> "$LOG" 2>&1 || echo "[yt-dlp-update] pip install returned non-zero" >> "$LOG"
else
  echo "[yt-dlp-update] venv not found at $VENV_ACTIVATE" >> "$LOG"
  exit 2
fi
echo "[yt-dlp-update] Finished at $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$LOG"
