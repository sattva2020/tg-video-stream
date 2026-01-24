#!/usr/bin/env bash
# Comprehensive preflight validation: sops/age, keys, .env.enc decryptability (no secret output)
# Extensible framework for additional checks (Docker, dependencies, etc.)
set -euo pipefail

ENV_ENC_PATH="${ENV_ENC_PATH:-.env.enc}"
KEY_FILE="${SOPS_AGE_KEY_FILE:-}"
KEY_INLINE="${SOPS_AGE_KEY:-}"

# Check counters
CHECKS_TOTAL=0
CHECKS_PASSED=0

log() { printf "%s\n" "$*"; }
fail() { printf "ERROR: %s\n" "$*" 1>&2; exit 1; }
check() { CHECKS_TOTAL=$((CHECKS_TOTAL + 1)); printf "[Check %d] %s..." "$CHECKS_TOTAL" "$*"; }
pass() { CHECKS_PASSED=$((CHECKS_PASSED + 1)); printf " \033[32mPASS\033[0m\n"; }
skip() { printf " \033[33mSKIP\033[0m\n"; }

log "=== Preflight Validation ==="
log ""

# Check 1: sops availability
check "sops command"
if command -v sops >/dev/null 2>&1; then
  pass
else
  log ""
  fail "sops not found"
fi

# Check 2: age availability
check "age command"
if command -v age >/dev/null 2>&1; then
  pass
else
  log ""
  fail "age not found"
fi

# Check 3: .env.enc file exists
check ".env.enc file"
if [ -f "$ENV_ENC_PATH" ]; then
  pass
else
  log ""
  fail ".env.enc not found at $ENV_ENC_PATH"
fi

# Check 4: Key availability and mode
KEY_MODE=""
check "age key availability"
if [ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ]; then
  KEY_MODE="file"
  pass
  log "  → Using age key file: $KEY_FILE"
elif [ -n "$KEY_INLINE" ]; then
  KEY_MODE="inline"
  pass
  log "  → Using inline SOPS_AGE_KEY"
else
  log ""
  fail "Provide SOPS_AGE_KEY_FILE (existing file) or SOPS_AGE_KEY (inline key)"
fi

# Check 5: Key file permissions (only for file mode)
if [ "$KEY_MODE" = "file" ]; then
  check "age key file permissions"
  # Best effort perms check (skip on Windows/NTFS where chmod doesn't work)
  if command -v stat >/dev/null 2>&1 && [ "$(uname -o 2>/dev/null)" != "Msys" ]; then
    perm=$(stat -c %a "$KEY_FILE" 2>/dev/null || true)
    case "$perm" in
      6*|7*)
        log ""
        fail "age key file $KEY_FILE has permissive mode $perm, tighten to 600"
        ;;
      *)
        pass
        log "  → Permissions: $perm"
        ;;
    esac
  else
    skip
    log "  → Skipped (Windows/NTFS or stat unavailable)"
  fi
fi

# Check 6: Decryption test
check "env decryption test"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

if [ "$KEY_MODE" = "file" ]; then
  SOPS_AGE_KEY_FILE="$KEY_FILE" sops --decrypt --input-type dotenv --output-type dotenv "$ENV_ENC_PATH" > "$TMP" 2>/dev/null
else
  SOPS_AGE_KEY="$KEY_INLINE" sops --decrypt --input-type dotenv --output-type dotenv "$ENV_ENC_PATH" > "$TMP" 2>/dev/null
fi

if [ -s "$TMP" ]; then
  pass
  log "  → Decryption successful (content not printed)"
else
  log ""
  fail "Decryption produced empty output"
fi

rm -f "$TMP"
trap - EXIT

# Summary
log ""
log "=== Summary ==="
log "All $CHECKS_PASSED checks passed"
log ""
log "Preflight validation completed successfully"
