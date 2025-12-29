#!/usr/bin/env bash
# =============================================================================
# Encrypt secrets to .env.enc using sops + age
#
# This script takes the master secrets file and encrypts it.
# The encrypted file can be safely committed to git.
#
# Usage:
#   SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/encrypt-secrets.sh
#   # or
#   SOPS_AGE_KEY="AGE-SECRET-KEY-xxx" ./scripts/encrypt-secrets.sh [source_file]
#
# Arguments:
#   source_file    Path to plaintext .env to encrypt (default: .env.master)
#
# Options:
#   --from-current  Use current .env + backend/.env merged as source
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

KEY_FILE="${SOPS_AGE_KEY_FILE:-}"
KEY_INLINE="${SOPS_AGE_KEY:-}"
AGE_PUBLIC_KEY=""

FROM_CURRENT=false
SOURCE_FILE=""

# Parse arguments
for arg in "$@"; do
  case $arg in
    --from-current) FROM_CURRENT=true ;;
    -*) echo "Unknown option: $arg"; exit 1 ;;
    *) SOURCE_FILE="$arg" ;;
  esac
done

log() { printf "[encrypt-secrets] %s\n" "$*"; }
fail() { printf "[encrypt-secrets] ERROR: %s\n" "$*" 1>&2; exit 1; }

# Check dependencies
command -v sops >/dev/null 2>&1 || fail "sops not found"

# Determine key source and extract public key
if [ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ]; then
  log "Using age key file: $KEY_FILE"
  AGE_PUBLIC_KEY=$(grep -E '^# public key:' "$KEY_FILE" | awk '{print $4}')
  export SOPS_AGE_KEY_FILE="$KEY_FILE"
elif [ -n "$KEY_INLINE" ]; then
  log "Using inline SOPS_AGE_KEY"
  # For inline key, try to get public from .internal/age.pub
  if [ -f "$PROJECT_ROOT/.internal/age.pub" ]; then
    AGE_PUBLIC_KEY=$(cat "$PROJECT_ROOT/.internal/age.pub")
  else
    fail "Need public key in .internal/age.pub when using SOPS_AGE_KEY"
  fi
  export SOPS_AGE_KEY="$KEY_INLINE"
else
  # Try default location
  DEFAULT_KEY="$PROJECT_ROOT/.internal/age.key"
  if [ -f "$DEFAULT_KEY" ]; then
    log "Using default key: $DEFAULT_KEY"
    AGE_PUBLIC_KEY=$(grep -E '^# public key:' "$DEFAULT_KEY" | awk '{print $4}')
    export SOPS_AGE_KEY_FILE="$DEFAULT_KEY"
  else
    fail "No age key found. Set SOPS_AGE_KEY_FILE or SOPS_AGE_KEY"
  fi
fi

[ -n "$AGE_PUBLIC_KEY" ] || fail "Could not extract age public key"
log "Using age public key: ${AGE_PUBLIC_KEY:0:20}..."

# Prepare source file
TMP_SOURCE=""
if [ "$FROM_CURRENT" = true ]; then
  log "Merging current .env files..."
  TMP_SOURCE=$(mktemp)
  trap 'rm -f "$TMP_SOURCE"' EXIT
  
  # Start with root .env
  if [ -f "$PROJECT_ROOT/.env" ]; then
    cat "$PROJECT_ROOT/.env" >> "$TMP_SOURCE"
    echo "" >> "$TMP_SOURCE"
  fi
  
  # Add backend-specific vars not in root
  if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    while IFS= read -r line; do
      # Skip empty lines and comments
      [[ "$line" =~ ^[[:space:]]*$ ]] && continue
      [[ "$line" =~ ^# ]] && continue
      # Extract key name
      key="${line%%=*}"
      # Add if not already present
      if ! grep -qE "^${key}=" "$TMP_SOURCE" 2>/dev/null; then
        echo "$line" >> "$TMP_SOURCE"
      fi
    done < "$PROJECT_ROOT/backend/.env"
  fi
  
  # Add frontend VITE_ vars
  if [ -f "$PROJECT_ROOT/frontend/.env" ]; then
    while IFS= read -r line; do
      [[ "$line" =~ ^VITE_ ]] || continue
      key="${line%%=*}"
      if ! grep -qE "^${key}=" "$TMP_SOURCE" 2>/dev/null; then
        echo "$line" >> "$TMP_SOURCE"
      fi
    done < "$PROJECT_ROOT/frontend/.env"
  fi
  
  SOURCE_FILE="$TMP_SOURCE"
  log "Merged $(wc -l < "$TMP_SOURCE") lines from current env files"
elif [ -n "$SOURCE_FILE" ]; then
  [ -f "$SOURCE_FILE" ] || fail "Source file not found: $SOURCE_FILE"
else
  # Default source
  SOURCE_FILE="$PROJECT_ROOT/.env.master"
  if [ ! -f "$SOURCE_FILE" ]; then
    SOURCE_FILE="$PROJECT_ROOT/.env"
  fi
  [ -f "$SOURCE_FILE" ] || fail "No source file found. Create .env.master or use --from-current"
fi

log "Encrypting from: $SOURCE_FILE"

# Count secrets
SECRET_COUNT=$(grep -cE '^[A-Z_]+=.' "$SOURCE_FILE" || echo 0)
log "Found $SECRET_COUNT variables to encrypt"

# Encrypt
OUTPUT_FILE="$PROJECT_ROOT/.env.enc"

sops --encrypt \
  --age "$AGE_PUBLIC_KEY" \
  --input-type dotenv \
  --output-type dotenv \
  "$SOURCE_FILE" > "$OUTPUT_FILE.tmp"

mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"

# Cleanup
if [ -n "$TMP_SOURCE" ]; then
  rm -f "$TMP_SOURCE"
  trap - EXIT
fi

log "✅ Encrypted to $OUTPUT_FILE"
log ""
log "The encrypted file is safe to commit to git."
log "Original plaintext files should NOT be committed."
log ""
log "To decrypt: ./scripts/decrypt-secrets.sh"
