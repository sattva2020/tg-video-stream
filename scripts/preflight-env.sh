#!/usr/bin/env bash
# Preflight check: sops/age presence, key availability, and .env.enc decryptability (no secret output)
set -euo pipefail

ENV_ENC_PATH="${ENV_ENC_PATH:-.env.enc}"
KEY_FILE="${SOPS_AGE_KEY_FILE:-}"
KEY_INLINE="${SOPS_AGE_KEY:-}"

log() { printf "%s\n" "$*"; }
fail() { printf "ERROR: %s\n" "$*" 1>&2; exit 1; }

command -v sops >/dev/null 2>&1 || fail "sops not found"
command -v age >/dev/null 2>&1 || fail "age not found"
log "sops/age detected"

[ -f "$ENV_ENC_PATH" ] || fail ".env.enc not found at $ENV_ENC_PATH"
log "Found $ENV_ENC_PATH"

KEY_MODE=""
if [ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ]; then
  KEY_MODE="file"
  # best effort perms check (skip on Windows/NTFS where chmod doesn't work)
  if command -v stat >/dev/null 2>&1 && [ "$(uname -o 2>/dev/null)" != "Msys" ]; then
    perm=$(stat -c %a "$KEY_FILE" 2>/dev/null || true)
    case "$perm" in
      6*|7*) fail "age key file $KEY_FILE has permissive mode $perm, tighten to 600" ;;
    esac
  fi
  log "Using age key file: $KEY_FILE"
elif [ -n "$KEY_INLINE" ]; then
  KEY_MODE="inline"
  log "Using inline SOPS_AGE_KEY"
else
  fail "Provide SOPS_AGE_KEY_FILE (existing file) or SOPS_AGE_KEY (inline key)"
fi

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

if [ "$KEY_MODE" = "file" ]; then
  SOPS_AGE_KEY_FILE="$KEY_FILE" sops --decrypt --input-type dotenv --output-type dotenv "$ENV_ENC_PATH" > "$TMP"
else
  SOPS_AGE_KEY="$KEY_INLINE" sops --decrypt --input-type dotenv --output-type dotenv "$ENV_ENC_PATH" > "$TMP"
fi

[ -s "$TMP" ] || fail "Decryption produced empty output"
log "Decryption OK (content not printed)"

rm -f "$TMP"
trap - EXIT
log "Preflight completed successfully"
