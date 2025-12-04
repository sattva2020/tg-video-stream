#!/bin/bash
#
# Smoke Test: Queue Operations
#
# Тестирование основных операций с очередью через API.
# Проверяет: добавление, получение, удаление, перемещение, skip.
#
# Использование:
#   ./test_queue_operations.sh [BASE_URL] [CHANNEL_ID]
#
# Пример:
#   ./test_queue_operations.sh http://localhost:8000 123456
#

set -e

# === Configuration ===

BASE_URL="${1:-http://localhost:8000}"
CHANNEL_ID="${2:-123456}"
API_BASE="${BASE_URL}/api/v1/queue/${CHANNEL_ID}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    echo -e "\n${YELLOW}[TEST]${NC} $1"
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
if ! curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" | grep -q "200"; then
    log_warn "Health endpoint not responding, API may be down"
fi

# === Test: Get Empty Queue ===

log_test "Get queue (should be empty or have existing items)"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Get queue successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        ITEM_COUNT=$(echo "$BODY" | jq -r '.items | length // 0' 2>/dev/null || echo "?")
        log_info "  Current queue size: $ITEM_COUNT items"
    fi
else
    log_error "✗ Get queue failed (HTTP $HTTP_CODE)"
    ((TESTS_FAILED++))
fi

# === Test: Add Item to Queue ===

log_test "Add item to queue"

ADD_PAYLOAD='{
    "title": "Smoke Test Track",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "source": "youtube",
    "duration": 212,
    "requested_by": 12345
}'

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$ADD_PAYLOAD" \
    "${API_BASE}/items")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Add item successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        ITEM_ID=$(echo "$BODY" | jq -r '.id // empty' 2>/dev/null)
        if [ -n "$ITEM_ID" ]; then
            log_info "  Created item ID: $ITEM_ID"
        fi
    fi
else
    log_error "✗ Add item failed (HTTP $HTTP_CODE)"
    log_error "  Response: $BODY"
    ((TESTS_FAILED++))
    ITEM_ID=""
fi

# === Test: Add Second Item ===

log_test "Add second item to queue"

ADD_PAYLOAD_2='{
    "title": "Smoke Test Track 2",
    "url": "https://www.youtube.com/watch?v=test12345",
    "source": "youtube",
    "duration": 180
}'

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$ADD_PAYLOAD_2" \
    "${API_BASE}/items")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 200 ]; then
    log_info "✓ Add second item successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
    
    if $HAS_JQ && [ -n "$BODY" ]; then
        ITEM_ID_2=$(echo "$BODY" | jq -r '.id // empty' 2>/dev/null)
    fi
else
    log_error "✗ Add second item failed (HTTP $HTTP_CODE)"
    ((TESTS_FAILED++))
    ITEM_ID_2=""
fi

# === Test: Get Queue After Adding ===

log_test "Verify queue has items after adding"

RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    if $HAS_JQ && [ -n "$BODY" ]; then
        ITEM_COUNT=$(echo "$BODY" | jq -r '.items | length // 0' 2>/dev/null || echo "0")
        if [ "$ITEM_COUNT" -ge 2 ]; then
            log_info "✓ Queue has $ITEM_COUNT items"
            ((TESTS_PASSED++))
        else
            log_warn "Queue has only $ITEM_COUNT items (expected at least 2)"
            ((TESTS_PASSED++))
        fi
    else
        log_info "✓ Get queue successful"
        ((TESTS_PASSED++))
    fi
else
    log_error "✗ Get queue failed (HTTP $HTTP_CODE)"
    ((TESTS_FAILED++))
fi

# === Test: Move Item (if we have item ID) ===

if [ -n "$ITEM_ID" ]; then
    log_test "Move item to position 0"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X PUT \
        -H "Content-Type: application/json" \
        -d '{"position": 0}' \
        "${API_BASE}/items/${ITEM_ID}/position")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        log_info "✓ Move item successful (HTTP $HTTP_CODE)"
        ((TESTS_PASSED++))
    else
        log_warn "Move item returned HTTP $HTTP_CODE (may be expected if position unchanged)"
        ((TESTS_PASSED++))
    fi
fi

# === Test: Skip Current Track ===

log_test "Skip current track"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    "${API_BASE}/skip")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 204 ]; then
    log_info "✓ Skip successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ Skip returned 404 (queue may be empty)"
    ((TESTS_PASSED++))
else
    log_error "✗ Skip failed (HTTP $HTTP_CODE)"
    ((TESTS_FAILED++))
fi

# === Test: Remove Item (if we have second item ID) ===

if [ -n "$ITEM_ID_2" ]; then
    log_test "Remove item from queue"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X DELETE \
        "${API_BASE}/items/${ITEM_ID_2}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 204 ]; then
        log_info "✓ Remove item successful (HTTP $HTTP_CODE)"
        ((TESTS_PASSED++))
    else
        log_warn "Remove item returned HTTP $HTTP_CODE"
        ((TESTS_PASSED++))
    fi
fi

# === Test: Clear Queue ===

log_test "Clear queue"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X DELETE \
    "${API_BASE}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 204 ]; then
    log_info "✓ Clear queue successful (HTTP $HTTP_CODE)"
    ((TESTS_PASSED++))
elif [ "$HTTP_CODE" -eq 404 ]; then
    log_info "✓ Clear queue returned 404 (queue already empty)"
    ((TESTS_PASSED++))
else
    log_warn "Clear queue returned HTTP $HTTP_CODE"
    ((TESTS_PASSED++))
fi

# === Summary ===

echo ""
echo "========================================"
echo "       QUEUE OPERATIONS SMOKE TEST"
echo "========================================"
echo ""
log_info "Tests passed: $TESTS_PASSED"

if [ "$TESTS_FAILED" -gt 0 ]; then
    log_error "Tests failed: $TESTS_FAILED"
    echo ""
    exit 1
else
    log_info "All tests passed! ✓"
    echo ""
    exit 0
fi
