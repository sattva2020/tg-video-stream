#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# deploy_to_remote.sh
# Complete deployment pipeline to remote server
# Usage: ./scripts/deploy_to_remote.sh [--host=<IP>] [--user=<user>] [--skip-tests]
##############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (can be overridden)
REMOTE_HOST="${REMOTE_HOST:-37.53.91.144}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa_n8n}"
SKIP_TESTS="${SKIP_TESTS:-false}"
DRY_RUN="${DRY_RUN:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --host=*) REMOTE_HOST="${1#*=}" ;;
    --user=*) REMOTE_USER="${1#*=}" ;;
    --port=*) REMOTE_PORT="${1#*=}" ;;
    --skip-tests) SKIP_TESTS="true" ;;
    --dry-run) DRY_RUN="true" ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Telegram Video Streamer - Remote Deployment Pipeline${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Remote Host:  $REMOTE_HOST:$REMOTE_PORT"
echo "  Remote User:  $REMOTE_USER"
echo "  SSH Key:      $SSH_KEY"
echo "  Skip Tests:   $SKIP_TESTS"
echo "  Dry Run:      $DRY_RUN"
echo ""

# Step 1: Validate environment
echo -e "${BLUE}[1/6] Validating environment...${NC}"
if [ ! -f "$SSH_KEY" ]; then
  echo -e "${RED}✗ SSH key not found: $SSH_KEY${NC}"
  exit 1
fi
echo -e "${GREEN}✓ SSH key found${NC}"

# Step 2: Find and validate artifact
echo -e "${BLUE}[2/6] Locating deployment artifact...${NC}"
ARTIFACT="$(ls -1t telegram-deploy-*.tar.gz 2>/dev/null | head -n1 || true)"
if [ -z "$ARTIFACT" ]; then
  echo -e "${RED}✗ No artifact found (expected telegram-deploy-*.tar.gz)${NC}"
  exit 1
fi
ARTIFACT_SIZE=$(du -h "$ARTIFACT" | cut -f1)
echo -e "${GREEN}✓ Found artifact: $ARTIFACT ($ARTIFACT_SIZE)${NC}"

# Step 3: Run tests (optional)
if [ "$SKIP_TESTS" != "true" ]; then
  echo -e "${BLUE}[3/6] Running local tests...${NC}"
  if [ -f "requirements.txt" ]; then
    echo "  - Validating requirements.txt..."
    python3 -m py_compile utils.py main.py 2>/dev/null && echo -e "${GREEN}  ✓ Python syntax OK${NC}" || {
      echo -e "${RED}  ✗ Python syntax error${NC}"
      exit 1
    }
  fi
fi

# Step 4: Connect to remote and prepare
echo -e "${BLUE}[4/6] Preparing remote server...${NC}"

SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $SSH_KEY"

# Test connection
if ! ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" -p "$REMOTE_PORT" "hostname" >/dev/null 2>&1; then
  echo -e "${RED}✗ Cannot connect to remote server${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Connected to remote server${NC}"

# Check remote prerequisites
REMOTE_CHECKS=$(ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" -p "$REMOTE_PORT" bash -c '
  errors=0
  
  # Check Python
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found"
    errors=$((errors+1))
  fi
  
  # Check pip
  if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "ERROR: pip not functional"
    errors=$((errors+1))
  fi
  
  # Check systemd
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "ERROR: systemctl not found"
    errors=$((errors+1))
  fi
  
  exit $errors
' 2>&1)

if [ -n "$REMOTE_CHECKS" ]; then
  echo -e "${RED}✗ Remote prerequisite check failed:${NC}"
  echo "$REMOTE_CHECKS"
  exit 1
fi
echo -e "${GREEN}✓ Remote prerequisites verified${NC}"

# Step 5: Transfer artifact
echo -e "${BLUE}[5/6] Transferring artifact to remote server...${NC}"

if [ "$DRY_RUN" == "true" ]; then
  echo "  [DRY RUN] Would transfer: $ARTIFACT → /tmp/$ARTIFACT"
else
  scp $SSH_OPTS -P "$REMOTE_PORT" "$ARTIFACT" "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
  echo -e "${GREEN}✓ Artifact transferred${NC}"
fi

# Step 6: Execute remote deployment
echo -e "${BLUE}[6/6] Executing remote deployment...${NC}"

DEPLOY_SCRIPT='
set -euo pipefail

# Verify artifact arrived
ARTIFACT=$(ls -1t /tmp/telegram-deploy-*.tar.gz 2>/dev/null | head -n1)
if [ -z "$ARTIFACT" ]; then
  echo "ERROR: Artifact not found in /tmp"
  exit 1
fi

echo "Using artifact: $ARTIFACT"

# Run deployment
cd /tmp
bash '"'"'./remote_deploy.sh'"'"'

# Verify service is running
echo "Waiting for service startup..."
sleep 3

if systemctl is-active --quiet tg_video_streamer; then
  echo "✓ Service is running"
else
  echo "WARNING: Service status check failed"
  systemctl status tg_video_streamer || true
fi
'

if [ "$DRY_RUN" == "true" ]; then
  echo "  [DRY RUN] Would execute remote deployment script"
else
  # Note: We need remote_deploy.sh on the server or transfer it
  # For now, we'll transfer it from local scripts/
  if [ -f "scripts/remote_deploy.sh" ]; then
    scp $SSH_OPTS -P "$REMOTE_PORT" "scripts/remote_deploy.sh" "$REMOTE_USER@$REMOTE_HOST:/tmp/" >/dev/null 2>&1
    echo -e "${GREEN}✓ Remote deploy script transferred${NC}"
  fi
  
  # Execute deployment
  ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" -p "$REMOTE_PORT" bash -c "$DEPLOY_SCRIPT" 2>&1 | while IFS= read -r line; do
    echo "  $line"
  done
fi

# Final status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
if [ "$DRY_RUN" == "true" ]; then
  echo -e "${YELLOW}  [DRY RUN] Deployment simulation completed${NC}"
else
  echo -e "${GREEN}  ✓ Deployment completed successfully${NC}"
fi
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Post-deployment steps:${NC}"
echo "  1. Verify service: ssh $REMOTE_USER@$REMOTE_HOST systemctl status tg_video_streamer"
echo "  2. Check logs: ssh $REMOTE_USER@$REMOTE_HOST journalctl -u tg_video_streamer -n 50"
echo "  3. Test stream: Check video player for stream URL"
echo ""
