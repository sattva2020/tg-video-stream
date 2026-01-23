# SAML SSO End-to-End Test Guide

This guide provides comprehensive instructions for manually testing the SAML SSO login flow end-to-end.

## Prerequisites

### Required Setup
- ✅ Backend server running (`python -m uvicorn src.main:app --reload --port 8000`)
- ✅ Frontend server running (`cd frontend && pnpm dev`)
- ✅ Database with migrations applied (`alembic upgrade head`)
- ✅ Admin account for configuration
- ✅ Test Identity Provider (IdP) account (Okta/Azure AD/Google Workspace/OneLogin)

### Test Account Setup
You'll need:
1. **Admin Account**: Local account with admin/superadmin role
2. **Test User Account**: Account in your IdP for testing authentication
3. **IdP Configuration**: Access to configure SAML application in your IdP

---

## Test Procedure

### Phase 1: Server Health Check

**Step 1.1: Verify Backend is Running**
```bash
curl http://localhost:8000/api/health
```
**Expected:** `{"status": "ok"}`

**Step 1.2: Verify Frontend is Running**
```bash
curl http://localhost:3000
```
**Expected:** HTML response with 200 status

---

### Phase 2: SAML IdP Configuration in Admin Panel

**Step 2.1: Access Admin Panel**
1. Navigate to http://localhost:3000/admin/security/sso
2. Login with admin credentials
3. Verify SAML configuration page loads

**Expected:** SAML configuration form visible with fields for IdP settings

**Step 2.2: Configure SAML IdP**

For **Okta**:
1. Login to Okta Admin Console
2. Go to Applications → Applications → Create App Integration
3. Select "SAML 2.0"
4. Fill in app details:
   - App name: "Test SAML App"
   - Configure SAML:
     - Single Sign On URL: `http://localhost:8000/api/auth/saml/acs`
     - Audience URI (SP Entity ID): `http://localhost:8000/saml/metadata`
     - Name ID Format: `EmailAddress`
     - Application username: `Email`
     - Attribute statements:
       - `email` = `user.email`
       - `firstName` = `user.firstName`
       - `lastName` = `user.lastName`
5. Click "Next" → assign to your test user → "Finish"
6. Copy the following from Okta:
   - Identity Provider SSOL URL (IdP SSO URL)
   - Identity Provider Certificate (X.509 cert)
   - Identity Provider Entity ID

For **Azure AD / Microsoft Entra ID**:
1. Login to Azure Portal → Azure Active Directory
2. Enterprise applications → New application
3. "Create your own application" → name: "Test SAML App"
4. In the app, go to "Single sign-on" → "SAML"
5. Download the "Federation Metadata XML" to get IdP details
6. Configure:
   - Identifier (Entity ID): `http://localhost:8000/saml/metadata`
   - Reply URL (ACS): `http://localhost:8000/api/auth/saml/acs`
   - Sign SAML assertion: Yes
7. Copy IdP SSO URL and X.509 certificate from metadata

For **Google Workspace**:
1. Admin Console → Apps → Web and mobile apps
2. "Add app" → "Add custom SAML app"
3. Fill in details:
   - Name: "Test SAML App"
   - ACS URL: `http://localhost:8000/api/auth/saml/acs`
   - Entity ID: `http://localhost:8000/saml/metadata`
4. Copy SSO URL, certificate, and entity ID
5. Add attributes:
   - Primary email → `email`
   - First name → `firstName`
   - Last name → `lastName`

**Step 2.3: Add SAML Configuration via Admin Panel**

1. In admin panel at http://localhost:3000/admin/security/sso
2. Click "Add SAML Configuration"
3. Fill in the form:
   ```
   Name: Test IdP
   Enabled: ✅
   IdP Entity ID: [from your IdP]
   IdP SSO URL: [from your IdP]
   IdP X.509 Certificate: [paste certificate from IdP]
   SP Entity ID: http://localhost:8000/saml/metadata
   SP ACS URL: http://localhost:8000/api/auth/saml/acs
   Name ID Format: urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
   Attribute Mapping:
     email: email
     full_name: firstName + ' ' + lastName
   Role Mapping:
     admin: [IdP group name for admins]
     user: [IdP group name for users]
   ```
4. Click "Save"

**Expected:** Configuration saved successfully, appears in SAML configs list

**Step 2.4: Verify Configuration via API**

```bash
# Get admin token first
ADMIN_TOKEN="your-admin-jwt-token"

# List SAML configs
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/saml/configs
```

**Expected:** JSON array with your test configuration

---

### Phase 3: SAML Metadata Verification

**Step 3.1: Fetch SP Metadata**

```bash
curl http://localhost:8000/api/auth/saml/metadata
```

**Expected:** XML response with:
- `<md:EntityDescriptor>` with entity ID
- `<md:SPSSODescriptor>` with AssertionConsumerService endpoint
- X.509 certificate for signing requests

**Step 3.2: Register Metadata with IdP**
- Copy the metadata XML URL or download the XML file
- Upload/register in your IdP's SAML configuration
- Verify IdP accepts the metadata

---

### Phase 4: Initiate SAML Login from Frontend

**Step 4.1: Access Login Page**
1. Navigate to http://localhost:3000/auth
2. Verify "Login with SSO" button is visible
3. Check browser console for no errors

**Expected:** SAML login button displays with Shield icon

**Step 4.2: Click SAML Login Button**
1. Click "Login with SSO" button
2. Observe redirect behavior

**Expected:**
- Browser redirects to backend: `GET /api/auth/saml/login`
- Backend returns redirect (307) to IdP SSO URL
- Browser loads IdP login page

**Step 4.3: Complete IdP Authentication**
1. Enter IdP credentials (test user account)
2. Complete any MFA if configured
3. Authorize the application (if first login)

**Expected:** IdP redirects back to ACS URL with SAML response

---

### Phase 5: Process SAML Response

**Step 5.1: Backend Processes SAML Response**

Watch backend logs for:
```
INFO: Received SAML response from IdP
INFO: Validating SAML assertion...
INFO: Extracting user attributes from SAML
INFO: User provisioned from SAML: user@example.com
INFO: Role mapped from SAML groups: user
INFO: SAML authentication successful
INFO: Issuing JWT token
```

**Expected:** User successfully authenticated and JWT issued

**Step 5.2: Frontend Receives Token**

**Expected:**
- Frontend receives JWT token in response
- Token stored in localStorage/cookies
- User redirected to dashboard
- User info displayed (email, name, role)

---

### Phase 6: Verify User is Logged In

**Step 6.1: Check User Session**

```bash
# Get the token from browser localStorage
TOKEN="your-saml-jwt-token"

# Verify user info
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/users/me
```

**Expected:** JSON response with:
```json
{
  "id": "...",
  "email": "user@example.com",
  "full_name": "Test User",
  "role": "user",
  "saml_name_id": "user@example.com",
  "saml_config_id": "...",
  "status": "active"
}
```

**Step 6.2: Verify User Attributes**
- ✅ Email matches IdP email
- ✅ Name matches IdP name (first + last)
- ✅ Role matches IdP group mapping
- ✅ `saml_name_id` is set
- ✅ `saml_config_id` references the SAML config

**Step 6.3: Test Subsequent Logins**
1. Logout from application
2. Click "Login with SSO" again
3. This time, IdP may auto-authenticate (SSO session)

**Expected:** User logged in without entering credentials (IdP SSO session)

---

### Phase 7: Verify Audit Log Entry Created

**Step 7.1: Check Audit Logs via API**

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/admin/audit-logs?action=login&resource_type=user&limit=5"
```

**Expected:** Audit log entry with:
```json
{
  "id": "...",
  "action": "login",
  "resource_type": "user",
  "resource_id": "user-id",
  "user_email": "user@example.com",
  "user_role": "user",
  "ip_address": "...",
  "user_agent": "...",
  "endpoint": "/api/auth/saml/acs",
  "method": "POST",
  "timestamp": "2024-01-23T..."
}
```

**Step 7.2: Verify Audit Log Details**
- ✅ Action is "login"
- ✅ Resource type is "user"
- ✅ User email matches authenticated user
- ✅ IP address captured
- ✅ User-Agent captured
- ✅ Endpoint shows SAML ACS URL
- ✅ Timestamp is accurate

---

### Phase 8: Test Role Mapping

**Step 8.1: Test Admin Role Mapping**

1. In your IdP, assign your test user to the admin group
2. Logout and login again via SAML
3. Check user role via API:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/users/me
```

**Expected:** Role is now "admin" (mapped from IdP group)

**Step 8.2: Test User Role Mapping**

1. In IdP, assign user to regular user group (not admin)
2. Logout and login again
3. Verify role is "user"

**Expected:** Role is "user" based on group mapping

---

### Phase 9: Test Error Handling

**Step 9.1: Invalid SAML Response**

1. Manually send malformed SAML response to ACS endpoint
2. Verify error handling:

```bash
curl -X POST http://localhost:8000/api/auth/saml/acs \
  -d "SAMLResponse=invalid_base64"
```

**Expected:** 400 or 500 error with descriptive message

**Step 9.2: Disabled SAML Config**

1. Disable the SAML configuration in admin panel
2. Attempt SAML login

**Expected:** Error message indicating SAML is disabled

**Step 9.3: Unknown User Provisioning**

1. Login with IdP user that hasn't been provisioned before
2. Verify new user is created

**Expected:** New user created with correct attributes

---

### Phase 10: Cleanup

**Step 10.1: Delete Test Users**
```bash
# Delete test SAML users (if needed)
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/users/{user_id}
```

**Step 10.2: Disable or Delete Test SAML Config**
1. Go to admin panel SAML configuration
2. Click "Delete" on test config
3. Confirm deletion

---

## Automated Verification Script

You can also run the automated verification script:

```bash
# From project root
cd backend
python tests/e2e/verify_sso_login_flow.py --backend-url http://localhost:8000 --frontend-url http://localhost:3000
```

This will perform automated checks and generate a report.

---

## Success Criteria

✅ **All phases completed successfully:**
1. Backend and frontend servers running
2. SAML IdP configured in admin panel
3. SAML metadata endpoint accessible
4. SAML login button visible in frontend
5. IdP authentication completes
6. User provisioned with correct attributes
7. User logged in with correct role
8. Audit log entry created
9. Role mapping works correctly
10. Error handling works as expected

---

## Troubleshooting

### Issue: "Invalid SAML response"
**Solution:**
- Verify IdP certificate is correct (no extra spaces/newlines)
- Check IdP entity ID matches exactly
- Verify ACS URL matches what's configured in IdP

### Issue: "User not created"
**Solution:**
- Check attribute mapping matches IdP attributes
- Verify email attribute is being sent
- Check backend logs for SAML parsing errors

### Issue: "Role not mapped correctly"
**Solution:**
- Verify role_mapping configuration matches IdP group names exactly
- Check IdP is sending group attributes
- Try with simple string mapping instead of list

### Issue: "Audit log not created"
**Solution:**
- Verify @audit_log decorator is applied to SAML ACS endpoint
- Check audit logging is enabled in config
- Verify AdminAuditLog table exists

---

## Additional Tests

### Test Multiple IdPs
- Configure multiple SAML IdPs
- Verify login works with each
- Verify user is linked to correct saml_config_id

### Test Single Logout (SLO)
- Configure SLO URL in IdP
- Initiate logout from application
- Verify user is logged out from IdP as well

### Test Token Expiry
- Wait for JWT token to expire
- Verify user is prompted to login again
- Verify SAML login works again

---

## Notes

- **Local Testing**: Use ngrok or similar for testing IdP callbacks to localhost
- **HTTPS Required**: Most IdPs require HTTPS for ACS URLs (use ngrok or local HTTPS)
- **Certificates**: IdP certificates must be valid and not expired
- **Time Sync**: Ensure server time is synchronized (SAML assertions are time-sensitive)
- **Browser**: Test in multiple browsers (Chrome, Firefox, Safari)
- **Network**: Test from different IP addresses if using IP whitelisting

---

## Test Results Template

| Phase | Test | Status | Notes |
|-------|------|--------|-------|
| 1 | Backend Health | ✅/❌ | |
| 1 | Frontend Health | ✅/❌ | |
| 2 | SAML Config UI | ✅/❌ | |
| 2 | Create SAML Config | ✅/❌ | |
| 3 | SP Metadata | ✅/❌ | |
| 4 | SAML Login Button | ✅/❌ | |
| 4 | Redirect to IdP | ✅/❌ | |
| 5 | IdP Authentication | ✅/❌ | |
| 5 | SAML Response Processed | ✅/❌ | |
| 6 | User Logged In | ✅/❌ | |
| 6 | User Attributes Correct | ✅/❌ | |
| 6 | Role Mapping Correct | ✅/❌ | |
| 7 | Audit Log Created | ✅/❌ | |
| 8 | Admin Role Mapping | ✅/❌ | |
| 9 | Error Handling | ✅/❌ | |

**Overall Result:** ✅ PASS / ❌ FAIL

**Date:** ___________________
**Tester:** ___________________
**IdP Used:** Okta / Azure AD / Google Workspace / OneLogin
