#!/usr/bin/env bash
set -euo pipefail

# rollback_release.sh
# Switch /opt/tg_video_streamer/current to the previous release in releases/

APP_DIR=/opt/tg_video_streamer
RELEASES_DIR="$APP_DIR/releases"
CURRENT_LINK="$APP_DIR/current"

if [ ! -d "$RELEASES_DIR" ]; then
  echo "No releases directory found at $RELEASES_DIR"
  exit 1
fi

# list releases sorted by name (timestamp) and pick last two
releases=( $(ls -1d "$RELEASES_DIR"/* 2>/dev/null | sort) )
if [ ${#releases[@]} -lt 2 ]; then
  echo "Less than 2 releases found, nothing to roll back to"
  exit 1
fi

current_target="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
prev_index=$((${#releases[@]}-2))
prev_release="${releases[$prev_index]}"

if [ -z "$prev_release" ]; then
  echo "Could not determine previous release"
  exit 1
fi

ln -sfn "$prev_release" "$APP_DIR/.current_tmp_rollback"
mv -Tf "$APP_DIR/.current_tmp_rollback" "$CURRENT_LINK"

echo "Rolled back current -> $prev_release"

echo "Restarting service"
systemctl restart tg_video_streamer || true

echo "rollback_release.sh finished"
