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
FALLBACK_ENV="/opt/sattva-streamer/.env"

ensure_env_from_sops() {
  local base_dir="$1"
  local enc_path="$base_dir/.env.enc"
  local out_path="$base_dir/.env"

  if [ -f "$out_path" ]; then
    return 0
  fi

  if [ ! -f "$enc_path" ]; then
    return 0
  fi

  if ! command -v sops >/dev/null 2>&1; then
    echo "sops not installed, cannot decrypt $enc_path"
    return 1
  fi

  if [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "$SOPS_AGE_KEY_FILE" ]; then
    SOPS_AGE_KEY_FILE="$SOPS_AGE_KEY_FILE" sops --decrypt --input-type dotenv --output-type dotenv "$enc_path" > "$out_path"
  elif [ -n "${SOPS_AGE_KEY:-}" ]; then
    SOPS_AGE_KEY="$SOPS_AGE_KEY" sops --decrypt --input-type dotenv --output-type dotenv "$enc_path" > "$out_path"
  else
    echo "SOPS_AGE_KEY_FILE or SOPS_AGE_KEY is required for $enc_path"
    return 1
  fi

  chmod 600 "$out_path" || true
  echo "Decrypted $enc_path -> $out_path"
}

split_envs() {
  local base_dir="$1"
  local root_env="$base_dir/.env"
  local backend_env="$base_dir/backend/.env"
  local frontend_env="$base_dir/frontend/.env"

  if [ ! -f "$root_env" ]; then
    echo "Root .env not found for splitting"
    return 1
  fi

  mkdir -p "$base_dir/backend" "$base_dir/frontend"

  # Backend получает все, кроме VITE_*
  grep -Ev '^VITE_' "$root_env" > "$backend_env" || true
  # Frontend получает только VITE_*
  grep -E '^VITE_' "$root_env" > "$frontend_env" || true

  chmod 600 "$backend_env" "$frontend_env" 2>/dev/null || true
  echo "Generated backend/.env and frontend/.env from root .env"
}

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

# Record deployment metadata for troubleshooting
DEPLOY_TIME_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPLOY_HOST="$(hostname 2>/dev/null || echo unknown)"
cat > "$DEST/DEPLOY_META.json" <<EOF
{
  "release_ver": "${VER}",
  "deploy_time_utc": "${DEPLOY_TIME_UTC}",
  "deploy_host": "${DEPLOY_HOST}",
  "source_artifact": "$(basename "$TARFILE")"
}
EOF

# Расшифровываем .env, если в релизе присутствует .env.enc
if ! ensure_env_from_sops "$DEST"; then
  echo "Failed to decrypt $DEST/.env.enc"
  exit 1
fi
if ! split_envs "$DEST"; then
  echo "Failed to split .env into backend/frontend"
  exit 1
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

# Preserve environment file from previous release or fallback location
PREVIOUS_ENV=""
if [ -L "$CURRENT_LINK" ] && [ -f "$CURRENT_LINK/.env" ]; then
  PREVIOUS_ENV="$CURRENT_LINK/.env"
elif [ -f "$FALLBACK_ENV" ]; then
  PREVIOUS_ENV="$FALLBACK_ENV"
fi

if [ -n "$PREVIOUS_ENV" ] && [ ! -f "$DEST/.env.enc" ] && [ ! -f "$DEST/.env" ]; then
  echo "Copying environment file from $PREVIOUS_ENV"
  cp "$PREVIOUS_ENV" "$DEST/.env"
  split_envs "$DEST" || true
fi

if [ ! -f "$DEST/.env" ]; then
  echo "Environment file .env is missing in release and cannot be copied. Add .env.enc with key (SOPS_AGE_KEY/_FILE) or provide .env."
  exit 1
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

# Keep a copy of metadata in current/ for quick access
cp -f "$DEST/DEPLOY_META.json" "$CURRENT_LINK/DEPLOY_META.json" || true
if [ -f "$DEST/RELEASE_META.json" ]; then
  cp -f "$DEST/RELEASE_META.json" "$CURRENT_LINK/RELEASE_META.json" || true
fi

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
SERVICE_FILE="$DEST/config/systemd/tg_video_streamer.service"
TARGET_SERVICE="tg_video_streamer.service"

if [ -f "$SERVICE_FILE" ]; then
  cp "$SERVICE_FILE" "/etc/systemd/system/$TARGET_SERVICE"
  systemctl daemon-reload || true
  systemctl enable "$TARGET_SERVICE" || true
elif [ -f "$DEST/tg_video_streamer.service" ]; then
  # Fallback for flat structure
  cp "$DEST/tg_video_streamer.service" "/etc/systemd/system/$TARGET_SERVICE"
  systemctl daemon-reload || true
  systemctl enable "${TARGET_SERVICE%.service}" || true
fi

# Update Nginx config if present
NGINX_CONFIG="$DEST/config/nginx/sattva-streamer"
if [ -f "$NGINX_CONFIG" ]; then
  echo "Updating Nginx configuration..."
  cp "$NGINX_CONFIG" /etc/nginx/sites-available/sattva-streamer
  # Ensure symlink exists
  ln -sf /etc/nginx/sites-available/sattva-streamer /etc/nginx/sites-enabled/sattva-streamer
  # Test and reload
  if nginx -t; then
    systemctl reload nginx
    echo "Nginx reloaded successfully"
  else
    echo "WARNING: Nginx configuration test failed, not reloading"
  fi
fi

# Restart service (best-effort). If service is configured to run as deploy user,
# make sure that user and permissions are correct before this step.
systemctl restart tg_video_streamer || true

echo "Deployed release $VER"
echo "remote_deploy.sh finished"
