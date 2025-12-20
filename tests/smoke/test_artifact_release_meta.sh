#!/usr/bin/env bash
#
# Smoke test: verifies that deployment artifact contains RELEASE_META.json
#
# Usage:
#   ./tests/smoke/test_artifact_release_meta.sh
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_SCRIPT="$PROJECT_ROOT/scripts/build_artifact.sh"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Smoke Test: Artifact Release Metadata"
echo "=========================================="
echo ""

# Test 1: build script exists
echo -n "Test 1: build_artifact.sh exists... "
if [[ -f "$BUILD_SCRIPT" ]]; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL${NC} - scripts/build_artifact.sh not found"
  exit 1
fi

# Test 2: locate artifact (or build one)
echo -n "Test 2: locate artifact... "
ARTIFACT="$(ls -1t telegram-deploy-*.tar.gz 2>/dev/null | head -n1 || true)"
if [[ -z "$ARTIFACT" ]]; then
  echo -e "${YELLOW}INFO${NC} - artifact not found, attempting to build"

  if [[ ! -d "frontend/dist" ]]; then
    echo -e "${RED}FAIL${NC} - frontend/dist not found. Build frontend first (cd frontend && pnpm build)."
    exit 1
  fi

  bash "$BUILD_SCRIPT" >/dev/null
  ARTIFACT="$(ls -1t telegram-deploy-*.tar.gz 2>/dev/null | head -n1 || true)"
fi

if [[ -z "$ARTIFACT" ]]; then
  echo -e "${RED}FAIL${NC} - could not create/find artifact"
  exit 1
fi

echo -e "${GREEN}PASS${NC} ($ARTIFACT)"

# Test 3: tar contains RELEASE_META.json
echo -n "Test 3: RELEASE_META.json present in tar... "
if tar -tzf "$ARTIFACT" | tr -d '\r' | grep -qE '^\./RELEASE_META\.json$|^RELEASE_META\.json$'; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL${NC} - RELEASE_META.json not found in artifact"
  exit 1
fi

# Test 4: validate JSON is parseable
echo -n "Test 4: RELEASE_META.json is valid JSON... "
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

tar -xzf "$ARTIFACT" -C "$TMP_DIR" ./RELEASE_META.json 2>/dev/null || tar -xzf "$ARTIFACT" -C "$TMP_DIR" RELEASE_META.json

META_FILE="$TMP_DIR/RELEASE_META.json"
if command -v node >/dev/null 2>&1; then
  META_FILE="$META_FILE" node - <<'NODE'
const fs = require('fs');

const path = process.env.META_FILE;
const raw = fs.readFileSync(path, 'utf8');
const data = JSON.parse(raw);

const required = ['artifact_name', 'build_time_utc', 'git_sha', 'git_branch', 'git_dirty'];
const missing = required.filter((k) => !(k in data));
if (missing.length) {
  throw new Error(`Missing keys: ${missing.join(', ')}`);
}
process.stdout.write('ok\n');
NODE
elif command -v python >/dev/null 2>&1 && python -c "print('ok')" >/dev/null 2>&1; then
  META_FILE="$META_FILE" python - <<'PY'
import json
import os

path1 = os.environ["META_FILE"]
with open(path1, "r", encoding="utf-8") as f:
    data = json.load(f)

required = ["artifact_name", "build_time_utc", "git_sha", "git_branch", "git_dirty"]
missing = [k for k in required if k not in data]
if missing:
    raise SystemExit(f"Missing keys: {missing}")

print("ok")
PY
elif command -v python3 >/dev/null 2>&1 && python3 -c "print('ok')" >/dev/null 2>&1; then
  META_FILE="$META_FILE" python3 - <<'PY'
import json
import os

path1 = os.environ["META_FILE"]
with open(path1, "r", encoding="utf-8") as f:
    data = json.load(f)

required = ["artifact_name", "build_time_utc", "git_sha", "git_branch", "git_dirty"]
missing = [k for k in required if k not in data]
if missing:
    raise SystemExit(f"Missing keys: {missing}")

print("ok")
PY
else
  echo -e "${RED}FAIL${NC} - Neither node nor a runnable python/python3 found for JSON validation"
  exit 1
fi

echo -e "${GREEN}PASS${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Artifact metadata smoke test passed!${NC}"
echo "=========================================="
