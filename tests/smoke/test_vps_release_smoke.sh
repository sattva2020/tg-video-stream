#!/usr/bin/env bash
#
# Smoke test: verifies VPS is on a healthy deployed release
#
# Checks:
# - current symlink resolves
# - frontend dist exists
# - tg_video_streamer systemd service is active
# - nginx config is valid
# - release metadata files exist in current/
#
# Usage:
#   ./tests/smoke/test_vps_release_smoke.sh [--host=<IP>] [--user=<user>] [--port=<port>] [--key=<path>]
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REMOTE_HOST="${REMOTE_HOST:-37.53.91.144}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa_n8n}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host=*) REMOTE_HOST="${1#*=}" ;;
    --user=*) REMOTE_USER="${1#*=}" ;;
    --port=*) REMOTE_PORT="${1#*=}" ;;
    --key=*) SSH_KEY="${1#*=}" ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/vps_smoke_$(date +%Y%m%d_%H%M%S).log"

{
  echo "=========================================="
  echo "Smoke Test: VPS Release Health"
  echo "=========================================="
  echo "Host: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT"
  echo "Key:  $SSH_KEY"
  echo ""

  if [[ ! -f "$SSH_KEY" ]]; then
    echo -e "${RED}FAIL${NC} - SSH key not found: $SSH_KEY"
    exit 1
  fi

  SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $SSH_KEY -p $REMOTE_PORT"

  echo -n "Test 1: SSH connectivity... "
  if ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "hostname" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
  else
    echo -e "${RED}FAIL${NC} - cannot connect"
    exit 1
  fi

  echo "Test 2: Remote checks..."
  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "set -euo pipefail; \
    echo 'current ->'; readlink -f /opt/tg_video_streamer/current; \
    test -f /opt/tg_video_streamer/current/frontend/dist/index.html; echo 'frontend: ok'; \
    test -f /opt/tg_video_streamer/current/RELEASE_META.json; echo 'release_meta: ok'; \
    test -f /opt/tg_video_streamer/current/DEPLOY_META.json; echo 'deploy_meta: ok'; \
    systemctl is-active tg_video_streamer >/dev/null && echo 'tg_video_streamer: active'; \
    nginx -t >/dev/null && echo 'nginx: ok'"

  echo ""
  echo -e "${GREEN}All VPS release smoke checks passed!${NC}"
} | tee "$LOG_FILE"
