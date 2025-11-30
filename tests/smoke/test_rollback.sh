#!/usr/bin/env bash
#
# Smoke test for rollback script functionality
# Tests: scripts/rollback_release.sh
#
# Usage: ./tests/smoke/test_rollback.sh
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ROLLBACK_SCRIPT="$PROJECT_ROOT/scripts/rollback_release.sh"

echo "=========================================="
echo "Smoke Test: Rollback Script"
echo "=========================================="
echo ""

# Test 1: Script exists
echo -n "Test 1: Rollback script exists... "
if [[ -f "$ROLLBACK_SCRIPT" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - scripts/rollback_release.sh not found"
    exit 1
fi

# Test 2: Script is executable
echo -n "Test 2: Script is executable... "
if [[ -x "$ROLLBACK_SCRIPT" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Script not executable, attempting chmod +x"
    chmod +x "$ROLLBACK_SCRIPT"
    if [[ -x "$ROLLBACK_SCRIPT" ]]; then
        echo -e "${GREEN}PASS${NC} (fixed)"
    else
        echo -e "${RED}FAIL${NC} - Could not make script executable"
        exit 1
    fi
fi

# Test 3: Script has proper shebang
echo -n "Test 3: Script has valid shebang... "
SHEBANG=$(head -1 "$ROLLBACK_SCRIPT")
if [[ "$SHEBANG" == "#!/usr/bin/env bash" ]] || [[ "$SHEBANG" == "#!/bin/bash" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Unexpected shebang: $SHEBANG"
fi

# Test 4: Script passes shellcheck (if available)
echo -n "Test 4: ShellCheck validation... "
if command -v shellcheck &> /dev/null; then
    if shellcheck -e SC2034,SC2086 "$ROLLBACK_SCRIPT" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${YELLOW}WARNING${NC} - ShellCheck found issues (non-blocking)"
    fi
else
    echo -e "${YELLOW}SKIPPED${NC} - shellcheck not installed"
fi

# Test 5: Script contains required functionality
echo -n "Test 5: Script contains git commands... "
if grep -q "git" "$ROLLBACK_SCRIPT"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - No git commands found"
    exit 1
fi

# Test 6: Script contains docker compose commands
echo -n "Test 6: Script contains docker compose commands... "
if grep -qE "(docker compose|docker-compose)" "$ROLLBACK_SCRIPT"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - No docker compose commands found"
fi

# Test 7: Script handles .previous_commit file
echo -n "Test 7: Script references .previous_commit... "
if grep -q ".previous_commit" "$ROLLBACK_SCRIPT"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}INFO${NC} - Does not use .previous_commit (may use different approach)"
fi

# Test 8: Dry-run simulation (if supported)
echo -n "Test 8: Dry-run or help option... "
if grep -qE "(--dry-run|--help|-h)" "$ROLLBACK_SCRIPT"; then
    echo -e "${GREEN}PASS${NC} - Has help/dry-run option"
else
    echo -e "${YELLOW}INFO${NC} - No dry-run option detected"
fi

# Test 9: Error handling
echo -n "Test 9: Error handling (set -e or trap)... "
if grep -qE "(set -e|trap)" "$ROLLBACK_SCRIPT"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - No explicit error handling found"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All critical smoke tests passed!${NC}"
echo "=========================================="
echo ""
echo "Note: This test validates script structure only."
echo "Actual rollback should be tested in staging environment."
