#!/usr/bin/env bash
set -euo pipefail

# remote_deploy.sh
# Deploys artifact found in /tmp/telegram-deploy-*.tar.gz into a releases/ directory and
# updates /opt/tg_video_streamer/current -> releases/<ver> symlink atomically.
# Designed to be idempotent and safe for rolling back.

TARFILE="$(ls -1t /tmp/telegram-deploy-*.tar.gz 2>/dev/null | head -n1 || true)"
if [ -z "$TARFILE" ]; then
  echo "No artifact found in /tmp (expected /tmp/telegram-deploy-*.tar.gz)"
  exit 1
fi

APP_DIR=/opt/tg_video_streamer
RELEASES_DIR="$APP_DIR/releases"
CURRENT_LINK="$APP_DIR/current"

echo "Using TAR=$TARFILE"

mkdir -p "$RELEASES_DIR"

# Determine release version: allow override via RELEASE_VER env, else timestamp
if [ -n "${RELEASE_VER:-}" ]; then
  VER="$RELEASE_VER"
else
  VER="$(date -u +%Y%m%d%H%M%S)"
fi

DEST="$RELEASES_DIR/$VER"
if [ -d "$DEST" ]; then
  echo "Release $VER already exists, reusing"
else
  mkdir -p "$DEST"
  echo "Extracting $TARFILE -> $DEST"
  # avoid restoring foreign owners
  tar --no-same-owner -xzf "$TARFILE" -C "$DEST"
fi

# Create venv under the release if missing (this avoids sharing venv across releases)
if [ ! -d "$DEST/venv" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found - please install python3, python3-venv and build deps"
    exit 1
  fi
  python3 -m venv "$DEST/venv"
fi

# Activate and install Python deps
. "$DEST/venv/bin/activate"
python -m pip install -U pip setuptools wheel
if [ -f "$DEST/requirements.txt" ]; then
  python -m pip install -r "$DEST/requirements.txt" || true
else
  echo "No requirements.txt in release; skipping pip install"
fi

# Create dedicated deploy user if it exists in /etc/passwd, else we'll keep current ownership (script usually run as root)
DEPLOY_USER="tgstream"
if id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$DEST"
else
  echo "User $DEPLOY_USER not found — leaving ownership as-is (running as $(whoami))"
fi

# Update atomic symlink: create new symlink tmp then rename
TMP_LINK="$APP_DIR/.current_tmp_$VER"
ln -sfn "$DEST" "$TMP_LINK"
mv -Tf "$TMP_LINK" "$CURRENT_LINK"
echo "Updated $CURRENT_LINK -> $DEST"

# Ensure .env permissions and ownership on the newly activated release (best-effort)
ENV_PATH="$CURRENT_LINK/.env"
if [ -f "$ENV_PATH" ]; then
  echo "Ensuring $ENV_PATH ownership and permissions"
  if id -u "$DEPLOY_USER" >/dev/null 2>&1; then
    chown "$DEPLOY_USER":"$DEPLOY_USER" "$ENV_PATH" || true
  fi
  chmod 600 "$ENV_PATH" || true
fi

# Copy systemd unit if present in release and enable
if [ -f "$DEST/tg_video_streamer.service" ]; then
  cp "$DEST/tg_video_streamer.service" /etc/systemd/system/tg_video_streamer.service
  systemctl daemon-reload || true
  systemctl enable tg_video_streamer || true
fi

# Restart service (best-effort). If service is configured to run as deploy user,
# make sure that user and permissions are correct before this step.
systemctl restart tg_video_streamer || true

echo "Deployed release $VER"
echo "remote_deploy.sh finished"
