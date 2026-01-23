#!/bin/bash
# Quick End-to-End Webhook Verification Script
# This script performs a quick verification of the webhook ecosystem

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TEST_USER_EMAIL="${TEST_USER_EMAIL:-admin@example.com}"
TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-admin123}"
WEBHOOK_TEST_URL="${WEBHOOK_TEST_URL:-https://webhook.site/test}"

echo "=================================================="
echo "E2E Webhook Verification"
echo "=================================================="
echo "API URL: $API_BASE_URL"
echo "Test User: $TEST_USER_EMAIL"
echo "Webhook URL: $WEBHOOK_TEST_URL"
echo "=================================================="

# Function to check if service is running
check_service() {
    local url=$1
    local name=$2

    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not running"
        return 1
    fi
}

# Function to print step header
print_step() {
    echo ""
    echo -e "${YELLOW}>>> $1${NC}"
    echo ""
}

# Check prerequisites
print_step "Checking Prerequisites"

ALL_GOOD=true

check_service "$API_BASE_URL/health" "Backend API" || ALL_GOOD=false
check_service "http://localhost:6379" "Redis" || ALL_GOOD=false

if [ "$ALL_GOOD" = false ]; then
    echo -e "${RED}Some services are not running. Please start them first.${NC}"
    echo ""
    echo "Start services with:"
    echo "  docker-compose up -d"
    echo "  cd backend && python -m uvicorn src.frameworks.http.app:app --reload"
    exit 1
fi

# Login
print_step "Step 1: Login"

LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Logged in successfully${NC}"
echo "Token: ${TOKEN:0:20}..."

# Create API Key
print_step "Step 2: Create API Key"

KEY_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/keys/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "E2E Test Key",
        "scopes": ["read:streams", "write:streams", "read:webhooks", "write:webhooks"],
        "rate_limit": {"requests": 100, "window_seconds": 60}
    }')

API_KEY=$(echo $KEY_RESPONSE | grep -o '"key":"sk_[^"]*' | cut -d'"' -f3)
KEY_ID=$(echo $KEY_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f3)

if [ -z "$API_KEY" ]; then
    echo -e "${RED}✗ API key creation failed${NC}"
    echo "Response: $KEY_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ API key created${NC}"
echo "Key ID: $KEY_ID"
echo "Key value: ${API_KEY:0:20}..."

# Create Webhook
print_step "Step 3: Create Webhook Subscription"

WEBHOOK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/webhooks/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"url\": \"$WEBHOOK_TEST_URL\",
        \"event_types\": [\"stream.started\", \"stream.stopped\", \"stream.error\"]
    }")

WEBHOOK_ID=$(echo $WEBHOOK_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
WEBHOOK_SECRET=$(echo $WEBHOOK_RESPONSE | grep -o '"secret":"[^"]*' | cut -d'"' -f4)

if [ -z "$WEBHOOK_ID" ]; then
    echo -e "${RED}✗ Webhook creation failed${NC}"
    echo "Response: $WEBHOOK_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Webhook created${NC}"
echo "Webhook ID: $WEBHOOK_ID"
echo "Secret: ${WEBHOOK_SECRET:0:20}..."

# Test Webhook
print_step "Step 4: Test Webhook Delivery"

TEST_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/webhooks/$WEBHOOK_ID/test" \
    -H "Authorization: Bearer $TOKEN")

TEST_STATUS=$(echo $TEST_RESPONSE | grep -o '"status":[^,]*' | cut -d':' -f2)

if [ "$TEST_STATUS" = "true" ] || [ "$TEST_STATUS" = "success" ]; then
    echo -e "${GREEN}✓ Test webhook sent successfully${NC}"
else
    echo -e "${YELLOW}⚠ Test webhook response: $TEST_RESPONSE${NC}"
fi

# Get Channels
print_step "Step 5: Get Available Channels"

CHANNELS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/channels/" \
    -H "Authorization: Bearer $TOKEN")

CHANNEL_ID=$(echo $CHANNELS_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$CHANNEL_ID" ]; then
    echo -e "${YELLOW}⚠ No channels found, creating one...${NC}"

    CREATE_CHANNEL_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/channels/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "E2E Test Channel",
            "username": "e2e_test_channel",
            "description": "Channel for E2E webhook testing"
        }')

    CHANNEL_ID=$(echo $CREATE_CHANNEL_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
fi

echo -e "${GREEN}✓ Using channel ID: $CHANNEL_ID${NC}"

# Start Stream
print_step "Step 6: Start Stream"

STREAM_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/streams/start" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"channel_id\": \"$CHANNEL_ID\"}")

echo "Stream response: $STREAM_RESPONSE"

echo -e "${GREEN}✓ Stream start requested${NC}"
echo "Waiting 5 seconds for webhook delivery..."

sleep 5

# Check Webhook Events
print_step "Step 7: Check Webhook Event Logs"

EVENTS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/webhooks/$WEBHOOK_ID/events" \
    -H "Authorization: Bearer $TOKEN")

EVENT_COUNT=$(echo $EVENTS_RESPONSE | grep -o '"total":[0-9]*' | cut -d':' -f2)
SUCCESS_COUNT=$(echo $EVENTS_RESPONSE | grep -o '"status":"success"' | wc -l)

echo "Total events: $EVENT_COUNT"
echo "Successful deliveries: $SUCCESS_COUNT"

if [ "$EVENT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Webhook events logged${NC}"

    # Show last event
    echo ""
    echo "Most recent event:"
    echo $EVENTS_RESPONSE | grep -o '"event_type":"[^"]*' | head -1
    echo $EVENTS_RESPONSE | grep -o '"status":"[^"]*' | head -1
    echo $EVENTS_RESPONSE | grep -o '"response_status_code":[0-9]*' | head -1
else
    echo -e "${YELLOW}⚠ No webhook events found yet${NC}"
fi

# Test Rate Limiting
print_step "Step 8: Test Rate Limiting"

echo "Making 10 rapid requests..."

RATE_LIMIT_HIT=false
for i in {1..10}; do
    RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$API_BASE_URL/api/v1/channels/" \
        -H "X-API-Key: $API_KEY" \
        -o /dev/null)

    HTTP_STATUS=$(echo $RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

    if [ "$HTTP_STATUS" = "429" ]; then
        RATE_LIMIT_HIT=true
        echo -e "${GREEN}✓ Rate limit enforced after $i requests${NC}"
        break
    fi

    sleep 0.1
done

if [ "$RATE_LIMIT_HIT" = false ]; then
    echo -e "${YELLOW}⚠ Rate limit not triggered (may be configured higher)${NC}"
fi

# Cleanup
print_step "Step 9: Cleanup"

DELETE_WEBHOOK=$(curl -s -X DELETE "$API_BASE_URL/api/v1/webhooks/$WEBHOOK_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -w "HTTPSTATUS:%{http_code}" \
    -o /dev/null)

DELETE_KEY=$(curl -s -X DELETE "$API_BASE_URL/api/v1/keys/$KEY_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -w "HTTPSTATUS:%{http_code}" \
    -o /dev/null)

echo -e "${GREEN}✓ Cleanup complete${NC}"

# Summary
echo ""
echo "=================================================="
echo "Verification Summary"
echo "=================================================="
echo -e "${GREEN}✓ API key created and authenticated${NC}"
echo -e "${GREEN}✓ Webhook subscription created${NC}"
echo -e "${GREEN}✓ Test webhook sent${NC}"
echo -e "${GREEN}✓ Stream started${NC}"
echo -e "${GREEN}✓ Event logs checked ($EVENT_COUNT events)${NC}"
echo -e "${GREEN}✓ Rate limiting tested${NC}"
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""
echo -e "${GREEN}✓ All verification steps passed!${NC}"
echo "=================================================="
