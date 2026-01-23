# IP Whitelist End-to-End Test Guide

This guide provides comprehensive instructions for manually testing the IP whitelisting feature end-to-end.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Test Procedure](#test-procedure)
3. [Test Scenarios](#test-scenarios)
4. [Expected Results](#expected-results)
5. [Troubleshooting](#troubleshooting)
6. [Test Results Template](#test-results-template)

---

## Prerequisites

### Required Setup
- ✅ Backend server running (`python -m uvicorn src.main:app --reload --port 8000`)
- ✅ Frontend server running (`cd frontend && pnpm dev`)
- ✅ Database with migrations applied (`alembic upgrade head`)
- ✅ Admin account for configuration
- ✅ IP whitelist feature enabled in settings

### Environment Configuration
Verify the following environment variables are set in your `.env` file:

```bash
# IP Whitelist Settings
IP_WHITELIST_ENABLED=true
IP_WHITELIST_STRICT_MODE=false  # Start with false for testing
IP_WHITELIST_ALLOW_LOOPBACK=true
```

**Note:**
- `IP_WHITELIST_STRICT_MODE=false` allows all IPs when whitelist is empty (safer for testing)
- `IP_WHITELIST_STRICT_MODE=true` blocks all non-whitelisted IPs (stricter security)

### Test Data Preparation
Prepare test IP addresses/ranges:
1. **Whitelisted IPv4 CIDR**: `192.168.100.0/24`
2. **Whitelisted Single IP**: `10.0.0.50`
3. **Non-whitelisted IP**: `203.0.113.50` (TEST-NET-3, safe to use)
4. **Loopback IP**: `127.0.0.1` (always allowed)

---

## Test Procedure

### Phase 1: Server Health Check

#### Step 1.1: Verify Backend is Running
```bash
curl http://localhost:8000/api/health
```
**Expected:** `{"status": "ok"}`

#### Step 1.2: Verify Frontend is Running
```bash
curl http://localhost:3000
```
**Expected:** HTML response with 200 status

#### Step 1.3: Verify Database Connection
```bash
cd backend
python -c "from database import engine; print('Database connected:', engine)"
```
**Expected:** No errors, database connection successful

---

### Phase 2: Admin Authentication

#### Step 2.1: Login to Admin Panel
1. Navigate to http://localhost:3000/admin/security/ip-whitelist
2. Login with admin credentials
3. Verify IP whitelist management page loads

**Expected:** IP whitelist table and "Add IP Range" form visible

#### Step 2.2: Obtain Admin API Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_admin_password"
  }'
```

**Expected:** JSON response with `access_token` field

Save the token for subsequent API calls:
```bash
export ADMIN_TOKEN="your_access_token_here"
```

---

### Phase 3: IP Whitelist Configuration via Admin Panel

#### Step 3.1: Access IP Whitelist Page
1. Navigate to http://localhost:3000/admin/security/ip-whitelist
2. Verify the page loads without errors
3. Check browser console for no errors

**Expected:**
- IP whitelist table visible (may be empty initially)
- "Add IP Range" form visible
- CIDR input field
- Description field
- Active/Inactive toggle
- Submit button

#### Step 3.2: Add IPv4 CIDR Range via Admin Panel

1. Click "Add IP Range" button
2. Fill in the form:
   - **CIDR**: `192.168.100.0/24`
   - **Description**: `Office network - Test`
   - **Is Active**: ✅ Enabled
3. Click "Save" or "Add"

**Expected:**
- Success notification appears
- New entry appears in table with:
  - CIDR: `192.168.100.0/24`
  - Description: `Office network - Test`
  - Status: Active
  - Type: IPv4
  - Created date

#### Step 3.3: Add Single IP via Admin Panel

1. Click "Add IP Range" button
2. Fill in the form:
   - **CIDR**: `10.0.0.50`
   - **Description**: `Single admin workstation - Test`
   - **Is Active**: ✅ Enabled
3. Click "Save"

**Expected:**
- Success notification
- New entry visible in table

#### Step 3.4: Add Inactive Entry (for testing)

1. Click "Add IP Range" button
2. Fill in the form:
   - **CIDR**: `172.16.0.0/16`
   - **Description**: `Reserved network (inactive) - Test`
   - **Is Active**: ❌ Disabled
3. Click "Save"

**Expected:**
- Success notification
- Entry visible but marked as "Inactive"

---

### Phase 4: IP Whitelist Configuration via API

#### Step 4.1: List All Whitelist Entries
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:** JSON array with all whitelist entries including the ones created via admin panel

#### Step 4.2: Get Whitelist Info
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries/info" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:**
```json
{
  "total_entries": 3,
  "active_entries": 2,
  "inactive_entries": 1,
  "ipv4_entries": 3,
  "ipv6_entries": 0
}
```

#### Step 4.3: Create Entry via API
```bash
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "192.168.200.0/24",
    "description": "Testing API creation",
    "is_active": true
  }'
```

**Expected:** 201 status with entry details including ID, CIDR, and creation timestamp

#### Step 4.4: Check IP Status
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/check?ip=192.168.100.50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:**
```json
{
  "ip": "192.168.100.50",
  "is_whitelisted": true
}
```

Test with non-whitelisted IP:
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/check?ip=203.0.113.50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:**
```json
{
  "ip": "203.0.113.50",
  "is_whitelisted": false
}
```

---

### Phase 5: Access Control Testing

#### Step 5.1: Test Whitelisted IP Access

Simulate request from whitelisted IP:
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 192.168.100.50"
```

**Expected:** 200 status with list of entries (access allowed)

#### Step 5.2: Test Non-Whitelisted IP Access (Strict Mode OFF)

With `IP_WHITELIST_STRICT_MODE=false`:
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 203.0.113.50"
```

**Expected:** 200 status (access allowed because strict mode is OFF)

#### Step 5.3: Test Non-Whitelisted IP Access (Strict Mode ON)

1. Update `.env` file:
   ```bash
   IP_WHITELIST_STRICT_MODE=true
   ```

2. Restart backend server

3. Test again:
   ```bash
   curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "X-Forwarded-For: 203.0.113.50"
   ```

**Expected:** 403 status with error message:
```json
{
  "detail": "Access denied from IP: 203.0.113.50",
  "error_type": "ip_whitelist_restricted"
}
```

#### Step 5.4: Test Loopback IP

Loopback should always be allowed:
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 127.0.0.1"
```

**Expected:** 200 status (loopback always allowed)

#### Step 5.5: Test CIDR Range Matching

Test various IPs within the whitelisted CIDR range:

**Within range (should be allowed):**
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 192.168.100.1"
```

```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 192.168.100.254"
```

**Outside range (blocked in strict mode):**
```bash
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 192.168.101.1"
```

**Expected:**
- IPs within `192.168.100.0/24` → Allowed
- IPs outside range → Blocked (if strict mode ON)

---

### Phase 6: Whitelist Management Operations

#### Step 6.1: Update Whitelist Entry

1. Via Admin Panel:
   - Find entry with CIDR `192.168.100.0/24`
   - Click "Edit"
   - Change description to: `Main office network (updated)`
   - Click "Save"

2. Verify via API:
   ```bash
   curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries/{entry_id}" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

**Expected:** Description updated successfully

#### Step 6.2: Deactivate Whitelist Entry

1. Via Admin Panel:
   - Find entry with CIDR `192.168.200.0/24`
   - Click "Deactivate"

2. Verify via API:
   ```bash
   curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries?active_only=true" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

**Expected:** Inactive entry no longer appears in active-only list

#### Step 6.3: Reactivate Whitelist Entry

1. Via Admin Panel:
   - Find the deactivated entry
   - Click "Activate"

**Expected:** Entry marked as active again

#### Step 6.4: Delete Whitelist Entry

1. Via Admin Panel:
   - Find entry with CIDR `172.16.0.0/16`
   - Click "Delete"
   - Confirm deletion

2. Verify via API:
   ```bash
   curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

**Expected:** Entry no longer appears in list

---

### Phase 7: Audit Log Verification

#### Step 7.1: Check Audit Logs for IP Whitelist Events

```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs?event_type=ip_whitelist_created&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:** List of audit logs for IP whitelist creation events

#### Step 7.2: Verify Audit Log Details

Each audit log entry should contain:
- `event_type`: "ip_whitelist_created" (or "ip_whitelist_updated", "ip_whitelist_deleted", etc.)
- `message`: Descriptive message
- `user_id` and `user_email`: Who made the change
- `details`: JSON object with:
  - `entry_id`: ID of the whitelist entry
  - `cidr`: CIDR range
  - `description`: Description text
  - `is_active`: Active status
  - `changes`: For update operations, includes old and new values

**Expected Sample:**
```json
{
  "id": "log-id",
  "event_type": "ip_whitelist_created",
  "message": "IP whitelist entry created: 192.168.100.0/24",
  "user_id": "admin-user-id",
  "user_email": "admin@example.com",
  "details": {
    "entry_id": "entry-uuid",
    "cidr": "192.168.100.0/24",
    "description": "Office network - Test",
    "is_active": true
  },
  "created_at": "2026-01-23T12:00:00Z"
}
```

---

### Phase 8: Edge Cases and Error Handling

#### Step 8.1: Invalid CIDR Format

Test invalid CIDR inputs:
```bash
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "invalid-cidr",
    "description": "Test invalid CIDR"
  }'
```

**Expected:** 400 status with error message:
```json
{
  "detail": "Invalid CIDR format: ..."
}
```

#### Step 8.2: Duplicate CIDR Entry

Try to create duplicate entry:
```bash
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "192.168.100.0/24",
    "description": "Duplicate entry"
  }'
```

**Expected:** Either 400 (duplicate rejected) or 201 (duplicate allowed, depending on implementation)

#### Step 8.3: IPv6 CIDR Support

Test IPv6 CIDR range:
```bash
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "2001:db8::/32",
    "description": "IPv6 test range",
    "is_active": true
  }'
```

**Expected:** 201 status with IPv6 entry created

#### Step 8.4: Missing Required Fields

Test missing CIDR:
```bash
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Missing CIDR"
  }'
```

**Expected:** 422 validation error

---

### Phase 9: Frontend Integration

#### Step 9.1: Test Frontend Display

1. Navigate to http://localhost:3000/admin/security/ip-whitelist
2. Verify all entries display correctly
3. Check that IPv4/IPv6 badges are correct
4. Verify active/inactive status indicators work

#### Step 9.2: Test Frontend Form Validation

1. Try to submit form with empty CIDR
2. Try to submit form with invalid CIDR format
3. Verify error messages appear correctly

**Expected:** Client-side validation shows appropriate error messages

#### Step 9.3: Test Frontend CRUD Operations

1. **Create**: Add new entry via form
2. **Read**: Refresh page, verify entry appears
3. **Update**: Edit entry, save changes
4. **Delete**: Remove entry, verify it's gone

**Expected:** All operations complete successfully with UI feedback

---

### Phase 10: Cleanup

#### Step 10.1: Remove Test Entries

Remove all test entries created during testing:
```bash
# Get all entries
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.[].id' \
  | while read entry_id; do
      curl -X DELETE "http://localhost:8000/api/admin/ip-whitelist/entries/$entry_id" \
        -H "Authorization: Bearer $ADMIN_TOKEN"
    done
```

#### Step 10.2: Reset Configuration

Restore original settings in `.env`:
```bash
IP_WHITELIST_ENABLED=false
IP_WHITELIST_STRICT_MODE=false
```

Restart backend server.

---

## Test Scenarios

### Scenario 1: Office Network Access Control
**Use Case:** Company wants to restrict admin access to office network only

**Steps:**
1. Add office network CIDR: `203.0.113.0/24`
2. Enable strict mode
3. Test access from office IP (should succeed)
4. Test access from home IP (should fail)

**Expected Result:** Only office network can access admin endpoints

### Scenario 2: Multiple Office Locations
**Use Case:** Company with multiple offices needs whitelisting for all

**Steps:**
1. Add office 1: `192.168.100.0/24`
2. Add office 2: `10.20.0.0/16`
3. Add office 3: `172.31.0.0/16`
4. Test access from each location

**Expected Result:** All three office networks can access

### Scenario 3: Specific Workstation Access
**Use Case:** Only specific admin workstations should access

**Steps:**
1. Add single IPs: `10.0.0.50`, `10.0.0.51`, `10.0.0.52`
2. Enable strict mode
3. Test from each IP (should succeed)
4. Test from IP not in list (should fail)

**Expected Result:** Only specific IPs allowed

### Scenario 4: Temporary Access Grant
**Use Case:** Grant temporary access to contractor

**Steps:**
1. Add contractor IP: `198.51.100.50`
2. Test access (should succeed)
3. Deactivate entry after contractor work complete
4. Test access again (should fail in strict mode)

**Expected Result:** Access can be temporarily granted and revoked

---

## Expected Results Summary

### ✅ Success Criteria
- [ ] Backend server responds to health checks
- [ ] Frontend admin panel loads without errors
- [ ] Admin can authenticate and obtain API token
- [ ] IP whitelist entries can be created via admin panel
- [ ] IP whitelist entries can be created via API
- [ ] Whitelist info endpoint returns correct statistics
- [ ] IP check endpoint correctly identifies whitelisted/non-whitelisted IPs
- [ ] Whitelisted IPs can access protected endpoints
- [ ] Non-whitelisted IPs are blocked (in strict mode)
- [ ] Loopback IPs always have access
- [ ] CIDR ranges correctly match IPs within range
- [ ] Entries can be updated via admin panel and API
- [ ] Entries can be activated/deactivated
- [ ] Entries can be deleted
- [ ] Audit logs are created for all operations
- [ ] Invalid CIDR formats are rejected
- [ ] IPv4 and IPv6 entries are supported
- [ ] Frontend displays entries correctly
- [ ] Frontend form validation works

### ❌ Common Failure Points
1. **Strict mode confusion**: Forgetting to enable strict mode when testing blocking
2. **Loopback bypass**: Not accounting for loopback always being allowed
3. **X-Forwarded-For**: Not setting header correctly when simulating IPs
4. **Database state**: Previous test entries interfering with new tests
5. **Token expiration**: Admin token expiring during long tests

---

## Troubleshooting

### Issue: "All IPs are allowed, even non-whitelisted ones"

**Cause:** `IP_WHITELIST_STRICT_MODE` is set to `false`

**Solution:**
```bash
# In .env file
IP_WHITELIST_STRICT_MODE=true

# Restart backend
```

### Issue: "Cannot add whitelist entries"

**Cause:** Admin token expired or insufficient permissions

**Solution:**
```bash
# Get new admin token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'

# Update ADMIN_TOKEN variable
export ADMIN_TOKEN="new_token_here"
```

### Issue: "IP whitelist middleware not blocking requests"

**Possible Causes:**
1. IP whitelist feature disabled
2. Path is in skip list (e.g., /health, /api/auth/login)
3. Loopback IP bypass

**Solutions:**
```bash
# 1. Enable IP whitelist in .env
IP_WHITELIST_ENABLED=true

# 2. Test with non-skipped path (e.g., /api/admin/ip-whitelist/entries)

# 3. Test with non-loopback IP (e.g., 203.0.113.50)
```

### Issue: "CIDR validation failing"

**Cause:** Invalid CIDR format

**Solution:** Verify CIDR format is correct:
- IPv4: `192.168.1.0/24` (network address / prefix)
- Single IP: `192.168.1.100` or `192.168.1.100/32`
- IPv6: `2001:db8::/32`

### Issue: "X-Forwarded-For header not working"

**Cause:** Middleware not configured to read header

**Solution:** Verify middleware implementation extracts IP from `X-Forwarded-For` header. Check logs for which IP is being detected.

### Issue: "Audit logs not appearing"

**Cause:** Activity service not configured or disabled

**Solution:** Verify activity logging is enabled in backend configuration.

---

## Test Results Template

Use this template to document your test results:

```markdown
# IP Whitelist E2E Test Results

**Test Date:** YYYY-MM-DD
**Tester:** [Your Name]
**Environment:** [dev/staging/prod]
**Backend Version:** [version]
**Frontend Version:** [version]

## Test Summary

- **Total Tests:** X
- **Passed:** X
- **Failed:** X
- **Success Rate:** X%

## Phase Results

### Phase 1: Server Health Checks
- [ ] Backend server running
- [ ] Frontend server running
- [ ] Database connected

**Notes:**

### Phase 2: Admin Authentication
- [ ] Admin login successful
- [ ] API token obtained

**Notes:**

### Phase 3: IP Whitelist Configuration
- [ ] Admin panel accessible
- [ ] IPv4 CIDR range created
- [ ] Single IP created
- [ ] Inactive entry created

**Notes:**

### Phase 4: API Configuration
- [ ] List entries works
- [ ] Whitelist info returns correct stats
- [ ] Create entry via API works
- [ ] Check IP endpoint works

**Notes:**

### Phase 5: Access Control
- [ ] Whitelisted IP allowed
- [ ] Non-whitelisted IP blocked (strict mode)
- [ ] Loopback IP always allowed
- [ ] CIDR range matching works

**Notes:**

### Phase 6: Management Operations
- [ ] Update entry works
- [ ] Deactivate/activate works
- [ ] Delete entry works

**Notes:**

### Phase 7: Audit Logs
- [ ] Creation events logged
- [ ] Update events logged
- [ ] Deletion events logged
- [ ] Log details complete

**Notes:**

### Phase 8: Edge Cases
- [ ] Invalid CIDR rejected
- [ ] IPv6 supported
- [ ] Missing fields validated

**Notes:**

### Phase 9: Frontend Integration
- [ ] UI displays entries correctly
- [ ] Form validation works
- [ ] CRUD operations work

**Notes:**

## Issues Found

1. **[Issue Title]**
   - Severity: [High/Medium/Low]
   - Description: [Details]
   - Steps to Reproduce: [Steps]
   - Expected: [What should happen]
   - Actual: [What actually happened]

## Overall Assessment

**Status:** [PASS/FAIL/PARTIAL]

**Recommendations:**
- [Any recommendations for improvements]

**Sign-off:**
Tester: _________________ Date: _________
Reviewer: _________________ Date: _________
```

---

## Additional Resources

- [IP Whitelist Configuration Guide](../../../../../docs/security/IP_WHITELIST_GUIDE.md)
- [API Documentation](http://localhost:8000/docs)
- [Database Schema](../../../../../backend/alembic/versions/)

---

## Quick Reference Commands

```bash
# Check if IP is whitelisted
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/check?ip=192.168.100.50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# List all entries
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get whitelist info
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries/info" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Create entry
curl -X POST "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cidr": "192.168.100.0/24", "description": "Test", "is_active": true}'

# Delete entry
curl -X DELETE "http://localhost:8000/api/admin/ip-whitelist/entries/{entry_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test access with specific IP
curl -X GET "http://localhost:8000/api/admin/ip-whitelist/entries" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Forwarded-For: 192.168.100.50"
```
