# 2FA Enforcement End-to-End Test Guide

This guide provides comprehensive instructions for manually testing the 2FA (Two-Factor Authentication) enforcement feature end-to-end.

**Table of Contents:**
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Understanding 2FA Enforcement](#understanding-2fa-enforcement)
4. [Test Environment Setup](#test-environment-setup)
5. [Test Scenarios](#test-scenarios)
6. [Verification Steps](#verification-steps)
7. [Troubleshooting](#troubleshooting)
8. [Test Results Template](#test-results-template)

---

## Overview

### What is 2FA Enforcement?

2FA (Two-Factor Authentication) enforcement is a security feature that requires users to enable two-factor authentication before accessing certain parts of the application. This is especially important for:

- **Admin accounts** - Protecting administrative functions
- **Sensitive operations** - Security settings, user management
- **Compliance requirements** - Meeting SOC 2, GDPR, and other security standards

### How It Works

1. **Policy Configuration**: Admins create security policies that require 2FA for specific roles
2. **Enforcement Check**: When users access protected endpoints, the system checks if 2FA is required
3. **Grace Period**: Optional grace period allows new accounts time to enable 2FA
4. **Access Control**: Users without 2FA are blocked from accessing protected resources
5. **Compliance Tracking**: All enforcement actions are logged for audit purposes

### Enforcement Levels

The system supports three enforcement levels:

1. **Mandatory** - Blocks access if 2FA is not enabled (strictest)
2. **Audit Only** - Logs violations but allows access (monitoring mode)
3. **Optional** - Recommends 2FA but doesn't enforce (soft policy)

---

## Prerequisites

### System Requirements

- ✅ Backend server running (typically `http://localhost:8000`)
- ✅ Frontend server running (typically `http://localhost:3000`)
- ✅ Database with migrations applied
- ✅ Admin account with credentials
- ✅ Test user account for 2FA testing

### Required Accounts

1. **Admin Account**
   - Email: `admin@example.com` (or your admin email)
   - Role: Admin or Superadmin
   - Permissions: Create security policies, manage users

2. **Test User Account**
   - Email: Any test email (e.g., `test-user@example.com`)
   - Role: User (or role to be tested)
   - 2FA: Initially disabled

### Tools Needed

- **Web Browser** (Chrome, Firefox, Safari, or Edge)
- **TOTP App** (Google Authenticator, Authy, or similar)
- **API Client** (Postman, curl, or similar) - Optional
- **Admin Panel Access**

---

## Understanding 2FA Enforcement

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Request                          │
│                    (Access Protected Resource)               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  2FA Enforcement Middleware                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Check if user is authenticated                     │   │
│  │ 2. Get active 2FA policies from database              │   │
│  │ 3. Check if user's role requires 2FA                  │   │
│  │ 4. Check if user has 2FA enabled                      │   │
│  │ 5. Check if user is within grace period               │   │
│  │ 6. Apply enforcement level (mandatory/audit/optional)  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
            ┌─────────────┐   ┌──────────────┐
            │  2FA Enabled │   │ 2FA Disabled │
            │  Allow Access│   │  Block Access│
            └─────────────┘   └──────────────┘
```

### Policy Types

**Two-Factor Enforcement Policy**
- Applies to: Specific roles or all users
- Settings:
  - `enabled`: Whether the policy is active
  - `enforcement_level`: mandatory, audit_only, or optional
  - `affected_roles`: List of roles this applies to (null = all)
  - `grace_period_hours`: Hours before enforcement starts (0 = immediate)
  - `allow_exempt_alternative_auth`: Exempt users using SAML/SSO

### Protected Endpoints

Endpoints that enforce 2FA (configurable):
- `/api/admin/*` - All admin endpoints
- `/api/admin/security/*` - Security management
- `/api/admin/users/*` - User management
- `/api/settings/*` - Settings management

### Flow Sequence

**Normal Flow (User With 2FA):**
1. User authenticates with username/password
2. User enters TOTP code from authenticator app
3. System validates TOTP code
4. User receives JWT token
5. User accesses protected endpoint
6. 2FA middleware checks: user has 2FA enabled ✅
7. Access granted

**Blocked Flow (User Without 2FA):**
1. User authenticates with username/password
2. System issues JWT token (2FA not required for basic auth)
3. User attempts to access protected endpoint
4. 2FA middleware checks: user does NOT have 2FA enabled ❌
5. 2FA policy: MANDATORY for this role
6. Access denied with HTTP 403
7. Error response: `{"error": "2FA_REQUIRED", "message": "..."}`

---

## Test Environment Setup

### Step 1: Verify Server Health

**Check Backend:**
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T..."
}
```

**Check Frontend:**
Open browser: `http://localhost:3000`

Expected: Application loads without errors

### Step 2: Prepare Test Accounts

**Create Test User (if needed):**

Via API:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "2fa-test@example.com",
    "password": "SecurePassword123!",
    "role": "user"
  }'
```

Or via admin panel:
1. Navigate to `/admin/users`
2. Click "Add User"
3. Enter email, password, and role
4. Save

**Important:** Note the test user's ID and credentials for later steps.

### Step 3: Install TOTP App

For testing 2FA, you'll need a TOTP authenticator app:

**Mobile Options:**
- Google Authenticator (iOS/Android)
- Authy (iOS/Android)
- Microsoft Authenticator (iOS/Android)

**Desktop Options:**
- WinAuth (Windows)
- Authenticator (Chrome Extension)

### Step 4: Prepare API Client

If using API testing (Postman/curl):

**Admin Token:**
```bash
# Get admin token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_admin_password"
  }'

# Save the access_token from response
```

Set as environment variable:
```bash
export ADMIN_TOKEN="your_admin_access_token_here"
```

---

## Test Scenarios

### Scenario 1: Mandatory 2FA Enforcement for User Role

**Objective:** Verify users cannot access protected endpoints without 2FA when mandatory policy is enabled.

**Test Data:**
- Policy Name: "Test Mandatory 2FA"
- Enforcement Level: `mandatory`
- Affected Roles: `["user"]`
- Grace Period: `0` hours (immediate enforcement)
- Test User: Regular user account without 2FA

**Expected Outcome:**
- User without 2FA is blocked from protected endpoints
- User with 2FA can access protected endpoints
- Compliance dashboard shows 2FA enforcement enabled

---

### Scenario 2: Grace Period Functionality

**Objective:** Verify grace period allows new accounts time to enable 2FA.

**Test Data:**
- Policy Name: "Test Grace Period 2FA"
- Enforcement Level: `mandatory`
- Affected Roles: `["user"]`
- Grace Period: `24` hours
- Test User: Newly created user account

**Expected Outcome:**
- New user can access protected endpoints within grace period
- After grace period expires, access is blocked
- Grace period is calculated from user creation time

---

### Scenario 3: Audit-Only Mode

**Objective:** Verify audit-only mode logs violations but allows access.

**Test Data:**
- Policy Name: "Test Audit 2FA"
- Enforcement Level: `audit_only`
- Affected Roles: `["user"]`
- Grace Period: `0` hours

**Expected Outcome:**
- User without 2FA can access protected endpoints
- Access is logged in audit logs
- Compliance dashboard shows audit events

---

### Scenario 4: Role-Based Enforcement

**Objective:** Verify 2FA enforcement applies only to specified roles.

**Test Data:**
- Policy Name: "Test Role-Based 2FA"
- Enforcement Level: `mandatory`
- Affected Roles: `["admin"]`
- Test User 1: Admin without 2FA
- Test User 2: Regular user without 2FA

**Expected Outcome:**
- Admin without 2FA is blocked
- Regular user without 2FA is NOT blocked
- Policy applies only to specified roles

---

### Scenario 5: Optional Policy Mode

**Objective:** Verify optional policy mode allows access without blocking.

**Test Data:**
- Policy Name: "Test Optional 2FA"
- Enforcement Level: `optional`
- Affected Roles: `["user"]`
- Grace Period: `0` hours

**Expected Outcome:**
- Users without 2FA can access protected endpoints
- Warning is logged but access is granted
- Compliance tracking shows non-compliant users

---

## Verification Steps

### Phase 1: Baseline Verification

#### 1.1 Verify No 2FA Policy Exists

**API Method:**
```bash
curl -X GET http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "policies": [],
  "total": 0
}
```

Or existing policies without 2FA enforcement.

#### 1.2 Verify Test User Can Access Without 2FA

**API Method:**
```bash
# Get test user token
TEST_USER_TOKEN="..."

# Try accessing protected endpoint
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $TEST_USER_TOKEN"
```

**Expected Response:**
- Status: `200 OK` or `401 Unauthorized` (if not admin)
- Should NOT be `403 Forbidden` for 2FA

---

### Phase 2: Create 2FA Enforcement Policy

#### 2.1 Create Policy via Admin Panel

**Frontend Method:**
1. Navigate to: `http://localhost:3000/admin/security/2fa-policy`
2. Click "Add Policy" or "Create New Policy"
3. Fill in the form:
   - **Name:** "E2E Test 2FA Policy"
   - **Enabled:** ✅ Yes
   - **Enforcement Level:** Mandatory
   - **Affected Roles:** User
   - **Grace Period (hours):** 0
   - **Allow Exempt Alternative Auth:** ❌ No
4. Click "Save"

**Expected Result:**
- Policy appears in the policy list
- Status shows as "Enabled"
- No error messages

#### 2.2 Create Policy via API

**API Method:**
```bash
curl -X POST http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test 2FA Policy",
    "policy_type": "two_factor_enforcement",
    "enabled": true,
    "enforcement_level": "mandatory",
    "affected_roles": ["user"],
    "grace_period_hours": 0,
    "allow_exempt_alternative_auth": false,
    "description": "2FA enforcement policy for E2E testing"
  }'
```

**Expected Response:**
```json
{
  "id": "uuid-here",
  "name": "E2E Test 2FA Policy",
  "policy_type": "two_factor_enforcement",
  "enabled": true,
  "enforcement_level": "mandatory",
  "affected_roles": ["user"],
  "grace_period_hours": 0,
  "created_at": "2026-01-23T...",
  "updated_at": "2026-01-23T..."
}
```

#### 2.3 Verify Policy Created

**API Method:**
```bash
curl -X GET http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
Policy list includes the newly created policy with all correct values.

---

### Phase 3: Test Access Without 2FA

#### 3.1 Attempt Access with Test User Without 2FA

**API Method:**
```bash
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -v
```

**Expected Response:**
```json
{
  "detail": {
    "error": "2FA_REQUIRED",
    "message": "Two-factor authentication is required for this account",
    "policy": "E2E Test 2FA Policy"
  }
}
```

**HTTP Status:** `403 Forbidden`

#### 3.2 Verify Audit Log Entry Created

**API Method:**
```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs?limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
Audit log should contain an entry similar to:
```json
{
  "id": "...",
  "action": "2FA_POLICY_VIOLATION",
  "user_id": "...",
  "details": {
    "policy": "E2E Test 2FA Policy",
    "enforcement_level": "mandatory"
  },
  "timestamp": "2026-01-23T..."
}
```

---

### Phase 4: Enable 2FA for Test User

#### 4.1 Setup 2FA (Get TOTP Secret)

**API Method:**
```bash
curl -X POST http://localhost:8000/api/auth/totp/setup \
  -H "Authorization: Bearer $TEST_USER_TOKEN"
```

**Expected Response:**
```json
{
  "secret": "ABCD1234EFGH5678...",
  "otpauth_url": "otpauth://totp/..."
}
```

**Action Required:**
1. Save the `secret` value
2. OR scan the QR code from `otpauth_url`
3. Enter into your TOTP authenticator app

#### 4.2 Verify TOTP Code and Enable 2FA

**Generate TOTP Code:**

**Option A: Using Python**
```python
import pyotp
secret = "ABCD1234EFGH5678..."  # From step 4.1
totp = pyotp.TOTP(secret)
current_code = totp.now()
print(f"Current TOTP code: {current_code}")
```

**Option B: Using Authenticator App**
- Open your TOTP app (Google Authenticator, Authy, etc.)
- Find the entry for your test account
- Use the current 6-digit code

**API Method:**
```bash
curl -X POST http://localhost:8000/api/auth/totp/verify \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456"
  }'
```

Replace `123456` with the actual TOTP code from your app.

**Expected Response:**
```json
{
  "status": "enabled"
}
```

**HTTP Status:** `200 OK`

#### 4.3 Verify 2FA is Enabled

**API Method:**
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TEST_USER_TOKEN"
```

**Expected Response:**
```json
{
  "id": "...",
  "email": "2fa-test@example.com",
  "totp_enabled": true,
  ...
}
```

---

### Phase 5: Test Access With 2FA

#### 5.1 Access Protected Endpoint With 2FA

**API Method:**
```bash
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -v
```

**Expected Response:**
- **HTTP Status:** `200 OK` (if user has admin role) OR `401 Unauthorized` (if not admin)
- **IMPORTANT:** Should NOT be `403 Forbidden` for 2FA

**Success Indicators:**
- ✅ Request passes 2FA enforcement check
- ✅ No "2FA_REQUIRED" error
- ✅ Response contains dashboard data or permission error (not 2FA error)

#### 5.2 Verify Compliance Dashboard Shows 2FA Status

**API Method:**
```bash
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "security_configs": {
    "saml_configs_enabled": 0,
    "saml_configs_total": 0,
    "security_policies_enabled": 1,
    "security_policies_total": 1,
    "ip_whitelist_entries": 0,
    "two_factor_enforcement_enabled": true
  },
  ...
}
```

**Key Field:** `two_factor_enforcement_enabled: true`

#### 5.3 Verify Frontend Dashboard

**Frontend Method:**
1. Navigate to: `http://localhost:3000/admin/security`
2. Verify "2FA Enforcement" status is shown
3. Verify status indicates "Enabled" or "Active"
4. Check for any 2FA-related metrics or alerts

**Expected UI Elements:**
- 2FA status badge/indicator
- Number of users with 2FA enabled
- Compliance status for 2FA requirements

---

### Phase 6: Cleanup

#### 6.1 Delete Test Policy

**API Method:**
```bash
POLICY_ID="uuid-from-creation-step"

curl -X DELETE "http://localhost:8000/api/admin/security-policies/$POLICY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "message": "Policy deleted successfully"
}
```

#### 6.2 Disable 2FA on Test User

**API Method:**
```bash
# Generate a valid TOTP code first
# Then disable 2FA
curl -X POST http://localhost:8000/api/auth/totp/disable \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456"
  }'
```

**Or Without Code (if allowed):**
```bash
curl -X POST http://localhost:8000/api/auth/totp/disable \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "status": "disabled"
}
```

---

## Troubleshooting

### Issue 1: Policy Not Enforcing

**Symptoms:**
- User without 2FA can access protected endpoints
- No 403 Forbidden response
- Policy appears enabled but doesn't work

**Possible Causes:**
1. Policy `enabled` field is `false`
2. User role not in `affected_roles`
3. Grace period hasn't expired
4. Middleware not registered in FastAPI app
5. Endpoint not in protected paths list

**Solutions:**
```bash
# 1. Check policy status
curl -X GET http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Verify user role
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TEST_USER_TOKEN"

# 3. Check if middleware is enabled
# In backend/src/main.py, verify:
# app.add_middleware(TwoFactorEnforcementMiddleware)
```

---

### Issue 2: Cannot Setup 2FA

**Symptoms:**
- `/api/auth/totp/setup` returns error
- No TOTP secret generated
- 401 Unauthorized on setup endpoint

**Possible Causes:**
1. User doesn't have admin permissions
2. Endpoint requires admin role
3. Authentication token invalid or expired

**Solutions:**
```bash
# 1. Verify token is valid
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TEST_USER_TOKEN"

# 2. Check user has permission to setup 2FA
# The /totp/setup endpoint currently requires admin role
# Use admin token or modify endpoint permissions

# 3. Get fresh token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "..."}'
```

---

### Issue 3: Invalid TOTP Code

**Symptoms:**
- `/api/auth/totp/verify` returns 401
- Error: "Invalid TOTP code"
- Code from authenticator app doesn't work

**Possible Causes:**
1. Clock synchronization issue
2. Wrong secret used
3. Code expired (30-second window)
4. Code already used (replay protection)

**Solutions:**
```python
# 1. Verify system time is synchronized
import datetime
print(datetime.datetime.utcnow())

# 2. Generate fresh code
import pyotp
secret = "your-secret-here"
totp = pyotp.TOTP(secret)
print(f"Current code: {totp.now()}")

# 3. Test with valid_window parameter
totp.verify(code, valid_window=1)  # Allow 1 step before/after
```

---

### Issue 4: Compliance Dashboard Not Updating

**Symptoms:**
- `two_factor_enforcement_enabled` shows `false`
- Dashboard doesn't reflect recent policy changes
- Metrics not updating

**Possible Causes:**
1. Caching issue
2. Policy not actually enabled in database
3. Dashboard query not checking correct field

**Solutions:**
```bash
# 1. Verify policy in database
curl -X GET "http://localhost:8000/api/admin/security-policies?policy_type=two_factor_enforcement" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Check dashboard API response
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.security_configs'

# 3. Refresh browser cache (Ctrl+F5)
```

---

### Issue 5: Grace Period Not Working

**Symptoms:**
- New user immediately blocked
- Grace period not being applied
- User creation time not considered

**Possible Causes:**
1. `grace_period_hours` is 0
2. User `created_at` field is NULL
3. Timezone mismatch
4. Calculation logic error

**Solutions:**
```bash
# 1. Check user creation time
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TEST_USER_TOKEN" | jq '.created_at'

# 2. Calculate account age
# If created_at: "2026-01-23T10:00:00Z"
# And current time: "2026-01-23T12:00:00Z"
# Account age = 2 hours = 7200 seconds
# Grace period = 24 hours = 86400 seconds
# Within grace period = true

# 3. Verify policy grace period setting
curl -X GET "http://localhost:8000/api/admin/security-policies/$POLICY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.grace_period_hours'
```

---

## Test Results Template

Copy this template to document your test results:

```markdown
# 2FA Enforcement E2E Test Results

**Test Date:** 2026-01-23
**Tester:** [Your Name]
**Environment:** Development / Staging / Production
**Backend URL:** http://localhost:8000
**Frontend URL:** http://localhost:3000

---

## Test Accounts

| Account Type | Email | Role | 2FA Status |
|--------------|-------|------|------------|
| Admin | admin@example.com | admin | Enabled |
| Test User | 2fa-test@example.com | user | Initially Disabled |

---

## Test Results Summary

| Scenario | Status | Notes |
|----------|--------|-------|
| Phase 1: Baseline Verification | ⬜ Pass / ❌ Fail | |
| Phase 2: Create 2FA Policy | ⬜ Pass / ❌ Fail | |
| Phase 3: Access Without 2FA | ⬜ Pass / ❌ Fail | |
| Phase 4: Enable 2FA | ⬜ Pass / ❌ Fail | |
| Phase 5: Access With 2FA | ⬜ Pass / ❌ Fail | |
| Phase 6: Compliance Dashboard | ⬜ Pass / ❌ Fail | |
| Phase 7: Cleanup | ⬜ Pass / ❌ Fail | |

**Overall Result:** ⬜ PASSED / ❌ FAILED

---

## Detailed Results

### Phase 1: Baseline Verification

**1.1 Verify No 2FA Policy Exists**
- **Result:** ⬜ Pass / ❌ Fail
- **Evidence:** [API response or screenshot]
- **Notes:**

**1.2 Verify Test User Can Access Without 2FA**
- **Result:** ⬜ Pass / ❌ Fail
- **Evidence:** [API response]
- **HTTP Status:** [Code]
- **Notes:**

---

### Phase 2: Create 2FA Policy

**2.1 Create Policy**
- **Method:** API / Frontend
- **Result:** ⬜ Pass / ❌ Fail
- **Policy ID:** [UUID]
- **Evidence:** [API response or screenshot]
- **Notes:**

**2.2 Verify Policy Created**
- **Result:** ⬜ Pass / ❌ Fail
- **Evidence:** [API response]
- **Notes:**

---

### Phase 3: Access Without 2FA

**3.1 Attempt Access Without 2FA**
- **Endpoint Tested:** [URL]
- **Result:** ⬜ Pass / ❌ Fail
- **HTTP Status Expected:** 403
- **HTTP Status Actual:** [Code]
- **Error Response:**
  ```json
  [Paste response here]
  ```
- **Notes:**

**3.2 Verify Audit Log Created**
- **Result:** ⬜ Pass / ❌ Fail
- **Evidence:** [Audit log entry]
- **Notes:**

---

### Phase 4: Enable 2FA

**4.1 Setup 2FA**
- **Result:** ⬜ Pass / ❌ Fail
- **TOTP Secret:** [Secret]
- **Evidence:** [API response]
- **Notes:**

**4.2 Verify TOTP Code**
- **Result:** ⬜ Pass / ❌ Fail
- **TOTP Code Used:** [Code]
- **Evidence:** [API response]
- **Notes:**

**4.3 Verify 2FA Enabled**
- **Result:** ⬜ Pass / ❌ Fail
- **User Profile Response:**
  ```json
  [Paste response here]
  ```
- **Notes:**

---

### Phase 5: Access With 2FA

**5.1 Access Protected Endpoint**
- **Endpoint Tested:** [URL]
- **Result:** ⬜ Pass / ❌ Fail
- **HTTP Status Expected:** 200 or 401
- **HTTP Status Actual:** [Code]
- **Response:**
  ```json
  [Paste response here]
  ```
- **Notes:**

**5.2 Verify Compliance Dashboard**
- **Result:** ⬜ Pass / ❌ Fail
- **`two_factor_enforcement_enabled` Value:** true/false
- **Evidence:** [Screenshot or API response]
- **Notes:**

---

### Phase 6: Cleanup

**6.1 Delete Test Policy**
- **Result:** ⬜ Pass / ❌ Fail
- **Notes:**

**6.2 Disable 2FA on Test User**
- **Result:** ⬜ Pass / ❌ Fail
- **Notes:**

---

## Issues Encountered

| Issue | Severity | Resolution |
|-------|----------|------------|
| [Issue description] | High/Medium/Low | [How resolved] |

---

## Additional Notes

[Any additional observations, recommendations, or concerns]

---

## Sign-Off

**Tester Signature:** ______________________

**Date:** [Date]

**Approved:** ⬜ Yes / ❌ No

**Reviewer Comments:**

```

---

## Quick Reference Commands

### Useful cURL Commands

```bash
# Get admin token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"..."}'

# List all security policies
curl -X GET http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Create 2FA policy
curl -X POST http://localhost:8000/api/admin/security-policies \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Policy",
    "policy_type": "two_factor_enforcement",
    "enabled": true,
    "enforcement_level": "mandatory",
    "affected_roles": ["user"],
    "grace_period_hours": 0
  }'

# Setup 2FA
curl -X POST http://localhost:8000/api/auth/totp/setup \
  -H "Authorization: Bearer $USER_TOKEN"

# Verify TOTP code
curl -X POST http://localhost:8000/api/auth/totp/verify \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'

# Get security dashboard
curl -X GET http://localhost:8000/api/admin/security/dashboard \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Delete policy
curl -X DELETE "http://localhost:8000/api/admin/security-policies/$POLICY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Disable 2FA
curl -X POST http://localhost:8000/api/auth/totp/disable \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

### Environment Setup

```bash
# Set environment variables
export BACKEND_URL="http://localhost:8000"
export FRONTEND_URL="http://localhost:3000"
export ADMIN_TOKEN="your_admin_token_here"
export USER_TOKEN="your_user_token_here"
export POLICY_ID="policy_uuid_here"

# Use in commands
curl -X GET "$BACKEND_URL/api/admin/security-policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Appendix

### A. HTTP Status Codes Reference

| Code | Meaning | Context |
|------|---------|---------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 401 | Unauthorized | Authentication required or invalid |
| 403 | Forbidden | 2FA required (when enforced) |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |

### B. Enforcement Levels Comparison

| Level | Access Without 2FA | Logging | Use Case |
|-------|-------------------|---------|----------|
| `mandatory` | Blocked (403) | Yes | High-security environments |
| `audit_only` | Allowed | Yes | Monitoring/transition period |
| `optional` | Allowed | Warning | Recommendation-only policies |

### C. Related Documentation

- [2FA Enforcement Policy Guide](../../docs/security/2FA_ENFORCEMENT_GUIDE.md)
- [Security Dashboard Documentation](../../docs/security/SECURITY_DASHBOARD.md)
- [TOTP API Reference](../../docs/api/TOTP_API.md)
- [Compliance Monitoring](../../docs/compliance/SOC2_README.md)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-23
**Maintained By:** Security Team
