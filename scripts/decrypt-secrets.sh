#!/usr/bin/env bash
# =============================================================================
# Decrypt secrets from .env.enc and split to backend/.env and frontend/.env
# 
# Usage:
#   SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/decrypt-secrets.sh
#   # or
#   SOPS_AGE_KEY="AGE-SECRET-KEY-xxx" ./scripts/decrypt-secrets.sh
#
# Options:
#   --dry-run    Show what would be created without writing files
#   --force      Overwrite existing .env files
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ENV_ENC_PATH="${ENV_ENC_PATH:-$PROJECT_ROOT/.env.enc}"
KEY_FILE="${SOPS_AGE_KEY_FILE:-}"
KEY_INLINE="${SOPS_AGE_KEY:-}"

DRY_RUN=false
FORCE=false

# Parse arguments
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

log() { printf "[decrypt-secrets] %s\n" "$*"; }
fail() { printf "[decrypt-secrets] ERROR: %s\n" "$*" 1>&2; exit 1; }

# Check dependencies
command -v sops >/dev/null 2>&1 || fail "sops not found. Install: https://github.com/getsops/sops"

# Check .env.enc exists
[ -f "$ENV_ENC_PATH" ] || fail ".env.enc not found at $ENV_ENC_PATH"

# Determine key source
if [ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ]; then
  log "Using age key file: $KEY_FILE"
  export SOPS_AGE_KEY_FILE="$KEY_FILE"
elif [ -n "$KEY_INLINE" ]; then
  log "Using inline SOPS_AGE_KEY"
  export SOPS_AGE_KEY="$KEY_INLINE"
else
  # Try default location
  DEFAULT_KEY="$PROJECT_ROOT/.internal/age.key"
  if [ -f "$DEFAULT_KEY" ]; then
    log "Using default key: $DEFAULT_KEY"
    export SOPS_AGE_KEY_FILE="$DEFAULT_KEY"
  else
    fail "No age key found. Set SOPS_AGE_KEY_FILE or SOPS_AGE_KEY"
  fi
fi

# Decrypt to temp file
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

log "Decrypting $ENV_ENC_PATH..."
sops --decrypt --input-type dotenv --output-type dotenv "$ENV_ENC_PATH" > "$TMP"

[ -s "$TMP" ] || fail "Decryption produced empty output"
log "Decryption successful"

# Count variables
TOTAL_VARS=$(grep -cE '^[A-Z_]+=.' "$TMP" || echo 0)
VITE_VARS=$(grep -cE '^VITE_' "$TMP" || echo 0)
BACKEND_VARS=$((TOTAL_VARS - VITE_VARS))

log "Found $TOTAL_VARS variables ($BACKEND_VARS backend, $VITE_VARS frontend VITE_*)"

if [ "$DRY_RUN" = true ]; then
  log "[DRY-RUN] Would create:"
  log "  - $PROJECT_ROOT/.env (root, all variables)"
  log "  - $PROJECT_ROOT/backend/.env (non-VITE variables)"
  log "  - $PROJECT_ROOT/frontend/.env (VITE_* variables only)"
  exit 0
fi

# Check for existing files
check_overwrite() {
  local file="$1"
  if [ -f "$file" ] && [ "$FORCE" != true ]; then
    log "WARNING: $file already exists. Use --force to overwrite"
    return 1
  fi
  return 0
}

# Create directories if needed
mkdir -p "$PROJECT_ROOT/backend" "$PROJECT_ROOT/frontend"

# Root .env (all variables)
ROOT_ENV="$PROJECT_ROOT/.env"
if check_overwrite "$ROOT_ENV" || [ "$FORCE" = true ]; then
  cp "$TMP" "$ROOT_ENV"
  chmod 600 "$ROOT_ENV"
  log "Created $ROOT_ENV"
fi

# Backend .env (exclude VITE_* lines)
BACKEND_ENV="$PROJECT_ROOT/backend/.env"
if check_overwrite "$BACKEND_ENV" || [ "$FORCE" = true ]; then
  grep -Ev '^VITE_' "$TMP" > "$BACKEND_ENV"
  chmod 600 "$BACKEND_ENV"
  log "Created $BACKEND_ENV"
fi

# Frontend .env (only VITE_* lines)
FRONTEND_ENV="$PROJECT_ROOT/frontend/.env"
if check_overwrite "$FRONTEND_ENV" || [ "$FORCE" = true ]; then
  grep -E '^VITE_' "$TMP" > "$FRONTEND_ENV" || true
  chmod 600 "$FRONTEND_ENV"
  log "Created $FRONTEND_ENV"
fi

rm -f "$TMP"
trap - EXIT

log "✅ Secrets decrypted and distributed successfully"
log ""
log "Files created:"
log "  $ROOT_ENV"
log "  $BACKEND_ENV"
log "  $FRONTEND_ENV"
