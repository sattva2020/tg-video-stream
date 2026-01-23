# End-to-End Webhook Verification Guide

This guide provides step-by-step instructions for manually verifying the webhook ecosystem integration.

## Prerequisites

Before running the verification, ensure:

1. **Backend server is running** on http://localhost:8000
   ```bash
   cd backend
   python -m uvicorn src.frameworks.http.app:app --reload
   ```

2. **PostgreSQL database is running** and migrations are applied
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Redis is running** for rate limiting and webhook deduplication
   ```bash
   docker-compose up -d redis
   ```

4. **Celery worker is running** for webhook delivery
   ```bash
   cd backend
   celery -A src.celery_app worker -l info -Q webhooks
   ```

5. **Test user exists** with valid credentials
   - Email: admin@example.com (or create a new user)
   - Password: Set during user creation

6. **Webhook test endpoint** is available
   - Use https://webhook.site for testing (create a unique URL)
   - Or set up a local test server with ngrok/smee

## Verification Steps

### Step 1: Create API Key

**Method A: Using Frontend**
1. Navigate to http://localhost:3000/api-keys
2. Click "Create API Key"
3. Fill in the form:
   - Name: "E2E Test Key"
   - Scopes: Select "read:streams", "write:streams", "read:webhooks", "write:webhooks"
   - Rate Limit: 100 requests / 60 seconds
4. Click "Create"
5. **Copy the key value** (shown only once!) and save it

**Method B: Using API directly**
```bash
# First login to get token
LOGIN_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

# Create API key
KEY_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/keys/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test Key",
    "scopes": ["read:streams", "write:streams", "read:webhooks", "write:webhooks"],
    "rate_limit": {"requests": 100, "window_seconds": 60}
  }')

echo "API Key Response:"
echo $KEY_RESPONSE | jq '.'

# Save the key value
API_KEY=$(echo $KEY_RESPONSE | jq -r '.key')
echo "Your API key: $API_KEY"
```

**Verification:**
- ✅ API key created successfully (201 response)
- ✅ Key value is returned only in creation response
- ✅ Key has correct scopes and rate limits

---

### Step 2: Create Webhook Subscription

**Method A: Using Frontend**
1. Navigate to http://localhost:3000/webhooks
2. Click "Create Webhook"
3. Fill in the form:
   - URL: Your test webhook URL (e.g., https://webhook.site/your-unique-id)
   - Event Types: Select "stream.started", "stream.stopped", "stream.error"
4. Click "Create"
5. **Copy the webhook secret** (shown only once!) and save it

**Method B: Using API directly**
```bash
# Create webhook subscription
WEBHOOK_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/webhooks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-id",
    "event_types": ["stream.started", "stream.stopped", "stream.error"]
  }')

echo "Webhook Response:"
echo $WEBHOOK_RESPONSE | jq '.'

# Save webhook details
WEBHOOK_ID=$(echo $WEBHOOK_RESPONSE | jq -r '.id')
WEBHOOK_SECRET=$(echo $WEBHOOK_RESPONSE | jq -r '.secret')
WEBHOOK_URL=$(echo $WEBHOOK_RESPONSE | jq -r '.url')

echo "Webhook ID: $WEBHOOK_ID"
echo "Webhook Secret: $WEBHOOK_SECRET"
echo "Webhook URL: $WEBHOOK_URL"
```

**Verification:**
- ✅ Webhook created successfully (201 response)
- ✅ Secret is returned only in creation response
- ✅ Webhook is subscribed to correct event types

---

### Step 3: Test Webhook Endpoint

**Method A: Using Frontend**
1. Go to http://localhost:3000/webhooks
2. Find your webhook in the list
3. Click "Test" button
4. Check your webhook test endpoint (webhook.site) for the test event

**Method B: Using API directly**
```bash
# Send test webhook
curl -X POST http://localhost:8000/api/v1/webhooks/$WEBHOOK_ID/test \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
# {
#   "success": true,
#   "status_code": 200,
#   "response": "..."
# }
```

**Verification:**
- ✅ Test webhook sent successfully (200 response)
- ✅ Webhook received at test endpoint
- ✅ Signature header `X-Sattva-Signature` is present
- ✅ Payload contains test event data

**Verify Signature:**
```python
import hmac
import hashlib
import json

# Your webhook secret
secret = "your_webhook_secret"

# The payload received at webhook.site
payload = b'{"id":"...","type":"test","timestamp":"...","data":{}}'

# Calculate signature
signature = hmac.new(
    secret.encode(),
    payload,
    hashlib.sha256
).hexdigest()

# Expected format: sha256=<signature>
expected = f"sha256={signature}"
print(f"Expected signature: {expected}")
```

---

### Step 4: Start a Stream

**Method A: Using Frontend**
1. Navigate to http://localhost:3000 (main dashboard)
2. Select a channel
3. Click "Start Stream"
4. Monitor the webhook test endpoint

**Method B: Using API directly**
```bash
# Get available channels
CHANNELS_RESPONSE=$(curl -X GET http://localhost:8000/api/v1/channels/ \
  -H "Authorization: Bearer $TOKEN")

CHANNEL_ID=$(echo $CHANNELS_RESPONSE | jq -r '.items[0].id')
echo "Using channel ID: $CHANNEL_ID"

# Start stream
STREAM_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/streams/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"channel_id\": \"$CHANNEL_ID\"}")

echo "Stream Response:"
echo $STREAM_RESPONSE | jq '.'

STREAM_ID=$(echo $STREAM_RESPONSE | jq -r '.id')
echo "Stream ID: $STREAM_ID"
```

**Verification:**
- ✅ Stream started successfully (200/201 response)
- ✅ Stream ID is returned
- ✅ Check webhook.test for stream.started event (may take 2-5 seconds)

---

### Step 5: Check Webhook Event Logs

**Method A: Using Frontend**
1. Go to http://localhost:3000/webhooks
2. Find your webhook
3. Click to expand webhook details
4. Check "Recent Events" section

**Method B: Using API directly**
```bash
# Get webhook events
EVENTS_RESPONSE=$(curl -X GET http://localhost:8000/api/v1/webhooks/$WEBHOOK_ID/events \
  -H "Authorization: Bearer $TOKEN")

echo "Webhook Events:"
echo $EVENTS_RESPONSE | jq '.'

# Count events by status
SUCCESS_COUNT=$(echo $EVENTS_RESPONSE | jq '[.items[] | select(.status=="success")] | length')
FAILED_COUNT=$(echo $EVENTS_RESPONSE | jq '[.items[] | select(.status=="failed")] | length')

echo "Successful deliveries: $SUCCESS_COUNT"
echo "Failed deliveries: $FAILED_COUNT"
```

**Verification:**
- ✅ Event logs show delivery attempts
- ✅ Status is "success" for successful deliveries
- ✅ HTTP status code is 200-299
- ✅ Response body contains endpoint response
- ✅ Duration is recorded in milliseconds

---

### Step 6: Verify Rate Limiting

**Test rate limiting with API key:**
```bash
# Make rapid requests using API key
for i in {1..20}; do
  echo "Request $i:"
  curl -X GET http://localhost:8000/api/v1/channels/ \
    -H "X-API-Key: $API_KEY" \
    -w "\nHTTP Status: %{http_code}\n" \
    -o /dev/null \
    -s
  sleep 0.1
done
```

**Expected results:**
- First N requests succeed (200 response)
- After rate limit: 429 Too Many Requests
- Response headers include:
  - `X-RateLimit-Scope: api_key`
  - `Retry-After: <seconds>`

**Verification:**
- ✅ Rate limit enforced after configured threshold
- ✅ 429 status code returned
- ✅ Retry-After header is present
- ✅ Rate limit resets after window expires

---

### Step 7: Verify Webhook Statistics

```bash
# Get webhook details with statistics
curl -X GET http://localhost:8000/api/v1/webhooks/$WEBHOOK_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Check:**
- ✅ `last_success_at` timestamp is updated after successful delivery
- ✅ `last_failure_at` timestamp is updated after failed delivery
- ✅ `failure_count` increments on failures
- ✅ `is_active` becomes false if failure_count > 10

---

## Automated Testing

For automated testing, use the provided Python script:

```bash
# Set environment variables
export API_BASE_URL=http://localhost:8000
export TEST_USER_EMAIL=admin@example.com
export TEST_USER_PASSWORD=your_password
export WEBHOOK_TEST_URL=https://webhook.site/your-unique-id

# Run automated E2E test
cd tests/e2e
python test_webhook_e2e.py
```

Or run with pytest:

```bash
pytest tests/e2e/test_webhook_e2e.py -v -s
```

---

## Troubleshooting

### Webhook not delivered

1. **Check Celery worker is running:**
   ```bash
   celery -A src.celery_app inspect active
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli ping
   ```

3. **Check webhook is active:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/webhooks/$WEBHOOK_ID | jq '.is_active'
   ```

4. **Check webhook health:**
   - If `failure_count > 10`, webhook is automatically disabled
   - Re-enable by updating: `PATCH /api/v1/webhooks/{id}` with `is_active: true`

### Rate limiting not working

1. **Check Redis is running:**
   ```bash
   redis-cli keys "ratelimit:*"
   ```

2. **Check rate limit service logs:**
   ```bash
   tail -f backend/logs/rate_limit.log
   ```

3. **Verify middleware is registered:**
   - Check `backend/src/frameworks/http/app.py` includes `VersionHeadersMiddleware`

### Signature verification fails

1. **Ensure payload format matches:**
   - JSON with no extra whitespace
   - Keys sorted alphabetically
   - No spaces after colons/commas

2. **Use correct signature format:**
   ```
   sha256=<hex_signature>
   ```

3. **Verify secret matches:**
   - Secret shown only during creation
   - Use `/rotate-secret` endpoint if lost

---

## Success Criteria

The verification is successful when all of the following are confirmed:

- ✅ API key created and authentication works
- ✅ Webhook subscription created with correct event types
- ✅ Test webhook delivered successfully to test endpoint
- ✅ Stream start triggers webhook delivery
- ✅ Event logs show delivery attempts with correct status
- ✅ Rate limiting enforced after threshold
- ✅ Webhook statistics updated correctly
- ✅ HMAC signatures verified successfully

---

## Next Steps

After successful verification:

1. **Review logs** for any warnings or errors
2. **Check database** to verify data integrity:
   ```sql
   SELECT * FROM api_keys WHERE name = 'E2E Test Key';
   SELECT * FROM webhooks WHERE url LIKE '%webhook.site%';
   SELECT * FROM webhook_events ORDER BY attempted_at DESC LIMIT 10;
   ```

3. **Clean up test data** (optional):
   ```bash
   # Delete test webhook
   curl -X DELETE http://localhost:8000/api/v1/webhooks/$WEBHOOK_ID \
     -H "Authorization: Bearer $TOKEN"

   # Delete test API key
   curl -X DELETE http://localhost:8000/api/v1/keys/$KEY_ID \
     -H "Authorization: Bearer $TOKEN"
   ```

4. **Update documentation** with any findings

5. **Run integration tests** for comprehensive coverage:
   ```bash
   pytest backend/tests/integration/test_api_keys.py -v
   pytest backend/tests/integration/test_webhooks.py -v
   ```
