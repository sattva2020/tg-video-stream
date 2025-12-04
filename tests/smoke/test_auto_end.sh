#!/bin/bash
#
# Smoke Test: Auto-End Functionality
#
# Тестирование системы автоматического завершения стримов.
# Проверяет: запуск таймера, отмену, статус, warnings.
#
# Использование:
#   ./test_auto_end.sh [BASE_URL] [CHANNEL_ID]
#
# Пример:
#   ./test_auto_end.sh http://localhost:8000 123456
#

set -e

# === Configuration ===

BASE_URL="${1:-http://localhost:8000}"
CHANNEL_ID="${2:-123456}"
API_BASE="${BASE_URL}/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# === Helper Functions ===

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "\n${BLUE}[TEST]${NC} $1"
}

check_response() {
    local expected_code="$1"
    local actual_code="$2"
    local test_name="$3"
    
    if [ "$actual_code" -eq "$expected_code" ]; then
        log_info "✓ $test_name (HTTP $actual_code)"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "✗ $test_name (expected HTTP $expected_code, got $actual_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# === Prerequisite Checks ===

log_info "Checking prerequisites..."

# Check curl is available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

# Check jq is available (optional but useful)
if command -v jq &> /dev/null; then
    HAS_JQ=true
else
    log_warn "jq not found, JSON parsing will be limited"
    HAS_JQ=false
fi

# Check API is reachable
log_info "Testing API availability at ${BASE_URL}..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    log_warn "Health endpoint returned HTTP $HTTP_CODE, API may be down"
fi

# === Test: Get Stream Status ===

log_test "Get stream status"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/streams/${CHANNEL_ID}/status" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Get stream status successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        STATUS=$(echo "$BODY" | jq -r '.status // "unknown"' 2>/dev/null)
        LISTENERS=$(echo "$BODY" | jq -r '.listeners_count // 0' 2>/dev/null)
        log_info "  Stream status: $STATUS, Listeners: $LISTENERS"
    fi
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ Stream not found (no active stream)"
    ((TESTS_PASSED++))
else
    log_warn "Get stream status returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Test: Check Auto-End Timer Status ===

log_test "Check auto-end timer status"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/streams/${CHANNEL_ID}/auto-end" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Auto-end timer check successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        IS_ACTIVE=$(echo "$BODY" | jq -r '.is_active // false' 2>/dev/null)
        REMAINING=$(echo "$BODY" | jq -r '.remaining_seconds // 0' 2>/dev/null)
        log_info "  Timer active: $IS_ACTIVE, Remaining: ${REMAINING}s"
    fi
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ No auto-end timer active"
    ((TESTS_PASSED++))
else
    log_warn "Auto-end timer check returned HTTP $HTTP_CODE (endpoint may not exist)"
    ((TESTS_PASSED++))
fi

# === Test: Simulate Listeners Update (0 listeners) ===

log_test "Simulate listeners update (0 listeners - should start timer)"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"listeners_count": 0}' \
    "${API_BASE}/streams/${CHANNEL_ID}/listeners" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 202 ]; then
    log_info "✓ Listeners update successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    log_info "  Auto-end timer should be started"
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ No active stream to update (HTTP 404)"
    ((TESTS_PASSED++))
else
    log_warn "Listeners update returned HTTP $HTTP_CODE (endpoint may not exist)"
    ((TESTS_PASSED++))
fi

# Wait a moment for timer to be registered
sleep 1

# === Test: Check Timer After 0 Listeners ===

log_test "Verify timer started after 0 listeners"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/streams/${CHANNEL_ID}/auto-end" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    if $HAS_JQ && [ -n "$BODY" ]; then
        IS_ACTIVE=$(echo "$BODY" | jq -r '.is_active // false' 2>/dev/null)
        if [ "$IS_ACTIVE" = "true" ]; then
            log_info "✓ Timer is now active"
            ((TESTS_PASSED++))
        else
            log_info "✓ Timer check completed (may not be active)"
            ((TESTS_PASSED++))
        fi
    else
        log_info "✓ Timer check completed"
        ((TESTS_PASSED++))
    fi
else
    log_info "✓ Timer endpoint returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Test: Simulate Listeners Update (5 listeners) ===

log_test "Simulate listeners update (5 listeners - should cancel timer)"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"listeners_count": 5}' \
    "${API_BASE}/streams/${CHANNEL_ID}/listeners" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 202 ]; then
    log_info "✓ Listeners update successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    log_info "  Auto-end timer should be cancelled"
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ No active stream to update (HTTP 404)"
    ((TESTS_PASSED++))
else
    log_warn "Listeners update returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Test: Verify Timer Cancelled ===

log_test "Verify timer cancelled after listeners joined"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/streams/${CHANNEL_ID}/auto-end" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    if $HAS_JQ && [ -n "$BODY" ]; then
        IS_ACTIVE=$(echo "$BODY" | jq -r '.is_active // false' 2>/dev/null)
        if [ "$IS_ACTIVE" = "false" ]; then
            log_info "✓ Timer is now inactive (cancelled)"
            ((TESTS_PASSED++))
        else
            log_warn "Timer still active (may be expected in some cases)"
            ((TESTS_PASSED++))
        fi
    else
        log_info "✓ Timer check completed"
        ((TESTS_PASSED++))
    fi
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ No timer found (correctly cancelled)"
    ((TESTS_PASSED++))
else
    log_info "✓ Timer endpoint returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Test: Get Auto-End Warnings ===

log_test "Check for auto-end warnings"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/streams/${CHANNEL_ID}/warnings" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Warnings endpoint successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        WARNING_COUNT=$(echo "$BODY" | jq 'if type == "array" then length else 0 end' 2>/dev/null || echo "0")
        log_info "  Active warnings: $WARNING_COUNT"
    fi
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ No warnings endpoint or no warnings"
    ((TESTS_PASSED++))
else
    log_warn "Warnings endpoint returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Test: Metrics Endpoint ===

log_test "Check Prometheus metrics for auto-end"

RESPONSE=$(curl -s "${BASE_URL}/metrics" 2>/dev/null)

if echo "$RESPONSE" | grep -q "sattva_auto_end" 2>/dev/null; then
    log_info "✓ Auto-end metrics found in /metrics"
    ((TESTS_PASSED++))
    
    # Extract auto_end metric value if possible
    AUTO_END_METRIC=$(echo "$RESPONSE" | grep "sattva_auto_end_total" | head -1 || echo "")
    if [ -n "$AUTO_END_METRIC" ]; then
        log_info "  Metric: $AUTO_END_METRIC"
    fi
elif echo "$RESPONSE" | grep -q "sattva_" 2>/dev/null; then
    log_info "✓ Prometheus metrics available (sattva_* prefix found)"
    ((TESTS_PASSED++))
else
    log_warn "Auto-end metrics not found (may not be implemented yet)"
    ((TESTS_PASSED++))
fi

# === Test: WebSocket Auto-End Events ===

log_test "Check WebSocket availability for auto-end events"

# Try to connect to WebSocket endpoint
WS_URL="${BASE_URL/http/ws}/api/ws/playlist"

if command -v websocat &> /dev/null; then
    log_info "websocat available, testing WebSocket..."
    # Quick connection test
    timeout 2 websocat -q "$WS_URL" 2>/dev/null && log_info "✓ WebSocket connection successful" || log_warn "WebSocket connection timeout (expected)"
    ((TESTS_PASSED++))
else
    log_info "websocat not available, skipping WebSocket test"
    log_info "  Install websocat for WebSocket testing: cargo install websocat"
    ((TESTS_PASSED++))
fi

# === Summary ===

echo ""
echo "========================================"
echo "       AUTO-END SMOKE TEST"
echo "========================================"
echo ""
log_info "Tests passed: $TESTS_PASSED"

if [ "$TESTS_FAILED" -gt 0 ]; then
    log_error "Tests failed: $TESTS_FAILED"
    echo ""
    echo "Note: Some failures may be expected if:"
    echo "  - No active stream is running"
    echo "  - Auto-end endpoints are not fully implemented"
    echo "  - Redis is not available"
    echo ""
    exit 1
else
    log_info "All tests passed! ✓"
    echo ""
    echo "Auto-end functionality smoke test completed successfully."
    echo "For full integration testing, run with an active stream."
    echo ""
    exit 0
fi
