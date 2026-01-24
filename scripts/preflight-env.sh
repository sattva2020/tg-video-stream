#!/usr/bin/env bash
# Comprehensive preflight validation: sops/age, keys, .env.enc decryptability (no secret output)
# Extensible framework for additional checks (Docker, dependencies, etc.)
set -euo pipefail

ENV_ENC_PATH="${ENV_ENC_PATH:-.env.enc}"
KEY_FILE="${SOPS_AGE_KEY_FILE:-}"
KEY_INLINE="${SOPS_AGE_KEY:-}"

# Check mode
CHECK_MODE="${1:-}"

# Check counters
CHECKS_TOTAL=0
CHECKS_PASSED=0

log() { printf "%s\n" "$*"; }
fail() { printf "ERROR: %s\n" "$*" 1>&2; exit 1; }
check() { CHECKS_TOTAL=$((CHECKS_TOTAL + 1)); printf "[Check %d] %s..." "$CHECKS_TOTAL" "$*"; }
pass() { CHECKS_PASSED=$((CHECKS_PASSED + 1)); printf " \033[32mPASS\033[0m\n"; }
skip() { printf " \033[33mSKIP\033[0m\n"; }

# Docker validation function
validate_docker() {
  log "=== Docker Environment Validation ==="
  log ""

  # Check 1: Docker command availability
  check "docker command"
  if command -v docker >/dev/null 2>&1; then
    pass
    # Try to get version, but handle cases where output might be suppressed
    if DOCKER_VERSION=$(docker --version 2>/dev/null); then
      log "  → $DOCKER_VERSION"
    else
      log "  → docker found (version unavailable)"
    fi
  else
    log ""
    fail "docker not found. Install Docker from https://docs.docker.com/get-docker/"
  fi

  # Check 2: Docker daemon is running
  check "docker daemon"
  if docker info >/dev/null 2>&1; then
    pass
    # Try to get server version, with fallback
    if DAEMON_INFO=$(docker info --format '{{.ServerVersion}}' 2>/dev/null); then
      log "  → Docker daemon running (version: $DAEMON_INFO)"
    else
      log "  → Docker daemon running"
    fi
  else
    log ""
    fail "docker daemon not running. Start Docker with: sudo systemctl start docker (Linux) or open Docker Desktop (Windows/Mac)"
  fi

  # Check 3: Docker Compose availability
  check "docker compose"
  COMPOSE_FOUND=0
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_FOUND=1
    pass
    # Try to get version
    if COMPOSE_VERSION=$(docker compose version --short 2>/dev/null); then
      log "  → $COMPOSE_VERSION"
    else
      log "  → docker compose plugin available"
    fi
  elif docker-compose version >/dev/null 2>&1; then
    COMPOSE_FOUND=1
    pass
    # Try to get version
    if COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null); then
      log "  → $COMPOSE_VERSION (standalone)"
    else
      log "  → docker-compose standalone available"
    fi
  fi

  if [ $COMPOSE_FOUND -eq 0 ]; then
    log ""
    fail "docker compose not found. Install Docker Compose v2 or standalone"
  fi

  # Summary
  log ""
  log "=== Summary ==="
  log "All $CHECKS_PASSED checks passed"
  log ""
  log "Docker environment OK"
}

# SOPS/Age validation function (original checks)
validate_sops() {
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
}

# Main routing logic
case "$CHECK_MODE" in
  --check-docker)
    validate_docker
    ;;
  --check-sops|--check-age)
    validate_sops
    ;;
  --help|-h)
    log "Usage: $0 [OPTION]"
    log ""
    log "Options:"
    log "  (no argument)         Validate sops/age environment (default)"
    log "  --check-docker        Validate Docker environment"
    log "  --check-sops          Validate sops/age environment (explicit)"
    log "  --check-age           Validate sops/age environment (alias)"
    log "  --help, -h            Show this help message"
    exit 0
    ;;
  "")
    # No argument provided, run default sops validation
    validate_sops
    ;;
  *)
    fail "Unknown option: $CHECK_MODE. Use --help for usage information."
    ;;
esac
