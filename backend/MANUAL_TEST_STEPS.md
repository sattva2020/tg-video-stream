# Manual Testing Guide: WebSocket JWT Authentication
## Subtask 7-1

### Quick Start Test Procedure

#### Step 1: Prepare Test Environment

```bash
# Open terminal in backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install test dependencies
pip install python-jose websockets

# Ensure .env file exists with JWT_SECRET
cat .env | grep JWT_SECRET
# If not set, add: JWT_SECRET=test_secret_for_development_only
```

#### Step 2: Generate Test Tokens

Create and run `generate_tokens.py`:
```python
# save as backend/generate_tokens.py
from jose import jwt
from datetime import datetime, timedelta, timezone
import uuid

SECRET = "test_secret_for_development_only"  # Match your .env JWT_SECRET
ALGORITHM = "HS256"

# Valid token (15 min expiry)
valid_payload = {
    "sub": str(uuid.uuid4()),
    "user_id": str(uuid.uuid4()),
    "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
}
valid_token = jwt.encode(valid_payload, SECRET, algorithm=ALGORITHM)
print(f"VALID_TOKEN={valid_token}")

# Invalid token (wrong secret)
invalid_token = jwt.encode({"sub": str(uuid.uuid4())}, "wrong_secret", algorithm=ALGORITHM)
print(f"INVALID_TOKEN={invalid_token}")
```

Run it:
```bash
python generate_tokens.py > tokens.txt
source tokens.txt  # This sets the variables
```

#### Step 3: Start Backend Server

```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

Expected output:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Step 4: Install WebSocket Client

```bash
# Option A: Using wscat (Node.js)
npm install -g wscat

# Option B: Using websocat (Rust)
cargo install websocat

# Option C: Python script (see below)
```

#### Step 5: Run Tests

**Test 1: No Token (Should FAIL with code 1008)**
```bash
wscat -c "ws://localhost:8000/api/ws/jsonrpc"
```
Expected: `Connection closed: 1008 (Policy Violation)`

**Test 2: Invalid Token (Should FAIL with code 1008)**
```bash
wscat -c "ws://localhost:8000/api/ws/jsonrpc?token=$INVALID_TOKEN"
```
Expected: `Connection closed: 1008 (Policy Violation)`

**Test 3: Valid Token (Should SUCCEED)**
```bash
wscat -c "ws://localhost:8000/api/ws/jsonrpc?token=$VALID_TOKEN"
```
Expected: `Connected (press CTRL+C to quit)`

Then send a test request:
```json
{"jsonrpc": "2.0", "method": "get_stream_status", "params": {"channel_id": 123}, "id": 1}
```

Should receive a response like:
```json
{"jsonrpc": "2.0", "result": {...}, "id": 1}
```

### Verification Results

#### ✅ Pass Criteria:
- [ ] Test 1: Connection rejected with code 1008
- [ ] Test 2: Connection rejected with code 1008
- [ ] Test 3: Connection accepted (no immediate close)
- [ ] Test 3: Can send/receive JSON-RPC messages
- [ ] Backend logs show authentication attempts

#### Expected Log Output:

**For failed attempts:**
```
WARNING:jsonrpc:WebSocket connection attempt without token
INFO:     websocket: 127.0.0.1:xxxxx - "WebSocket /api/ws/jsonrpc" [rejected]
```

**For successful connection:**
```
INFO:jsonrpc:JSON-RPC WebSocket connected for user=<uuid>
INFO:jsonrpc:Starting JSON-RPC main loop for user=<uuid>
```

### Alternative: Python Test Script

If wscat is not available, use `test_websocket_auth.py`:

```bash
cd backend
python test_websocket_auth.py
```

This will:
1. Test connection without token
2. Test connection with invalid token
3. Test connection with valid token
4. Report results

### Troubleshooting

**Issue:** "ModuleNotFoundError: No module named 'src'"
**Fix:** Ensure you're running from the backend directory

**Issue:** "Connection refused"
**Fix:** Check that backend server is running on port 8000

**Issue:** "JWT validation fails even with valid token"
**Fix:** Ensure JWT_SECRET in .env matches the secret used to generate the token

**Issue:** "Database connection errors"
**Fix:** Set DATABASE_URL in .env or use SQLite: `DATABASE_URL=sqlite:///./test.db`

### Code Implementation Verification

The implementation correctly:

1. ✅ **Validates JWT BEFORE accepting connection** (endpoint.py:83-102)
   ```python
   if not token:
       await websocket.close(code=1008, reason="Policy Violation: Missing authentication token")
       return
   ```

2. ✅ **Closes with code 1008 for missing/invalid tokens**
   ```python
   if not payload:
       await websocket.close(code=1008, reason="Policy Violation: Invalid authentication token")
   ```

3. ✅ **Extracts user_id from JWT payload**
   ```python
   user_id = payload.get("sub") or payload.get("user_id")
   ```

4. ✅ **Only accepts after successful validation**
   ```python
   await websocket.accept()  # Line 108 - AFTER all auth checks
   ```

5. ✅ **Cleans up resources in finally block**
   ```python
   finally:
       db.close()
       log.info(f"JSON-RPC connection cleanup completed for user={user_id}")
   ```

### Test Completion Checklist

- [ ] All 3 test scenarios executed
- [ ] Results match expected behavior
- [ ] Backend logs reviewed for authentication events
- [ ] No resource leaks (connections properly closed)
- [ ] Test results documented in build-progress.txt

When complete, update `implementation_plan.json`:
```json
{
  "id": "subtask-7-1",
  "status": "completed",
  "notes": "Manual testing complete. All authentication flows working correctly."
}
```
