# 2FA Enforcement Policy Guide

## Overview

This guide provides comprehensive instructions for configuring and managing Two-Factor Authentication (2FA) enforcement policies for the Telegram Streamer platform. 2FA enforcement policies allow administrators to require two-factor authentication for specific user roles, providing enterprise-grade security for sensitive operations and accounts.

**Last Updated:** 2026-01-23
**Feature Status:** Production Ready
**Supported 2FA Methods:** TOTP (Time-based One-Time Password)

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding 2FA Enforcement](#understanding-2fa-enforcement)
3. [Configuration Overview](#configuration-overview)
4. [Setup Instructions](#setup-instructions)
5. [Common Use Cases](#common-use-cases)
6. [Testing and Verification](#testing-and-verification)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Access

- **Administrator Account**: You must have admin or superadmin privileges
- **Backend Configuration**: Access to backend environment variables
- **User Management**: Understanding of your organization's role structure

### Information to Gather

Before configuring 2FA enforcement, consider the following:

- **User Roles**: Which roles in your organization require 2FA (e.g., admin, superadmin, moderators)
- **Grace Period**: How long new users should have before 2FA is required
- **Enforcement Strategy**: Will 2FA be mandatory, optional, or audit-only
- **Alternative Auth**: Whether users with SAML/SSO should be exempt from 2FA

---

## Understanding 2FA Enforcement

### How 2FA Enforcement Works

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│   User  │                    │   App   │                    │   DB    │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │ 1. Request to Protected      │                              │
     │    Endpoint                  │                              │
     ├─────────────────────────────>│                              │
     │                              │                              │
     │                              │ 2. Fetch Active 2FA Policies│
     │                              ├─────────────────────────────>│
     │                              │                              │
     │                              │ 3. Return Policies           │
     │                              │<─────────────────────────────┤
     │                              │                              │
     │                              │ 4. Check User Role & 2FA     │
     │                              │    Status                    │
     │                              │                              │
     │ 5a. User Has 2FA Enabled    │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
     │ 6. Process Request           │                              │
     │                              ├─────────────────────────────>│
     │                              │                              │
     │ 5b. User Lacks 2FA (Mandatory)                              │
     │<─────────────────────────────┤                              │
     │    (403 Forbidden)           │                              │
     │                              │                              │
```

### Key Components

1. **Security Policies**: Database-stored rules defining when 2FA is required
2. **Enforcement Levels**: Three modes - mandatory, optional, audit-only
3. **Role-Based Application**: Policies can apply to specific roles or all roles
4. **Grace Period**: Configurable time before enforcement begins for new accounts
5. **Exemptions**: Support for alternative authentication methods (e.g., SAML SSO)
6. **Middleware & Dependencies**: Two enforcement mechanisms - global middleware and per-endpoint dependencies

### Enforcement Flow

1. **User Request**: User attempts to access a protected endpoint
2. **Policy Check**: System queries active 2FA enforcement policies
3. **Role Evaluation**: Determines if any policies apply to user's role
4. **2FA Status Check**: Verifies if user has TOTP enabled
5. **Grace Period Check**: Allows temporary access if within grace period
6. **Enforcement Action**:
   - **Mandatory**: Blocks access with 403 Forbidden
   - **Audit Only**: Logs violation but allows access
   - **Optional**: Allows access with warning

---

## Configuration Overview

### Environment Variables

Configure 2FA enforcement behavior in `backend/.env`:

```bash
# Enable/disable 2FA enforcement feature
TWO_FA_ENFORCEMENT_ENABLED=true

# Protected paths (comma-separated) for middleware enforcement
TWO_FA_PROTECTED_PATHS=/api/admin,/api/settings
```

**Note**: These variables control the global middleware enforcement. Individual endpoint enforcement uses dependencies.

### Security Policy Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| **name** | string | Yes | Display name for this policy | `"Admin 2FA Requirement"` |
| **enabled** | boolean | No | Whether this policy is active | `true` |
| **policy_type** | string | Yes | Type of policy | `"2fa_enforcement"` |
| **enforcement_level** | string | Yes | strictness of enforcement | `"mandatory"` |
| **affected_roles** | list | No | Roles this policy applies to | `["admin", "superadmin"]` |
| **grace_period_hours** | integer | No | Grace period in hours | `24` |
| **allow_exempt_alternative_auth** | boolean | No | Exempt SAML users | `false` |
| **description** | string | No | Human-readable description | `"Requires 2FA for all admin users"` |

### Enforcement Levels

| Level | Behavior | Use Case |
|-------|----------|----------|
| **mandatory** | Blocks access if 2FA not enabled | High-security requirements, admin access |
| **optional** | Warns but allows access | Recommended but not required |
| **audit_only** | Logs violations only | Testing policy impact before enforcement |

### Supported User Roles

- **superadmin**: Full system access
- **admin**: Administrative access
- **moderator**: Content moderation access
- **user**: Basic user access (default)

---

## Setup Instructions

### Step 1: Enable 2FA Enforcement

1. Open `backend/.env`
2. Set `TWO_FA_ENFORCEMENT_ENABLED=true`
3. Configure protected paths (optional):
   ```bash
   TWO_FA_PROTECTED_PATHS=/api/admin,/api/settings,/api/users
   ```
4. Restart the backend service

**Note**: Environment variables control middleware-based enforcement. Policy-based enforcement works independently.

### Step 2: Create 2FA Policy via Admin Panel

#### Method 1: Using the Web UI

1. Navigate to **Admin** → **Security** → **2FA Policy**
2. Click **Add Policy**
3. Fill in the form:
   - **Policy Name**: e.g., "Admin 2FA Requirement"
   - **Enforcement Level**: Select mandatory, optional, or audit_only
   - **Grace Period (Hours)**: Enter 0 for immediate, or specify hours
   - **Affected Roles**: Leave empty for all roles, or specify roles (e.g., "admin, superadmin")
   - **Description**: Add a description (e.g., "Requires 2FA for all admin users")
4. Click **Create Policy**

#### Method 2: Using the API

```bash
curl -X POST https://streamer.example.com/api/admin/security-policies/policies \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin 2FA Requirement",
    "policy_type": "2fa_enforcement",
    "enabled": false,
    "enforcement_level": "mandatory",
    "grace_period_hours": 24,
    "affected_roles": ["admin", "superadmin"],
    "allow_exempt_alternative_auth": false,
    "description": "Requires 2FA for all admin and superadmin users"
  }'
```

### Step 3: Enable the Policy

**Important**: Policies are created disabled by default. You must enable them.

1. Navigate to **Admin** → **Security** → **2FA Policy**
2. Find your created policy
3. Click the power button icon (⏻) to enable it
4. Confirm when prompted

**Or via API**:
```bash
curl -X POST https://streamer.example.com/api/admin/security-policies/policies/{policy_id}/enable \
  -H "Authorization: Bearer <admin-token>"
```

### Step 4: Configure Protected Endpoints

There are two ways to enforce 2FA on endpoints:

#### Option A: Middleware (Path-Based)

The middleware automatically protects configured paths:

```python
# In backend/src/frameworks/http/app.py
from src.frameworks.http.middleware.two_factor_enforcement import TwoFactorEnforcementMiddleware

app.add_middleware(TwoFactorEnforcementMiddleware, protected_paths=["/api/admin"])
```

**Protected Paths** (default):
- `/api/admin` - All admin endpoints
- `/api/settings` - Settings management

#### Option B: Dependency (Endpoint-Based)

For fine-grained control, use the dependency:

```python
from fastapi import Depends
from src.frameworks.http.middleware.two_factor_enforcement import enforce_2fa_policy

@app.get("/api/admin/sensitive")
async def sensitive_operation(
    user: User = Depends(enforce_2fa_policy)
):
    # This endpoint requires 2FA if policy applies to user's role
    return {"data": "sensitive information"}
```

### Step 5: Verify Configuration

1. Navigate to **Admin** → **Security** → **2FA Policy**
2. Verify your policy appears in the list with "Enabled" status
3. Check the stats cards:
   - **Total Policies**: Should show at least 1
   - **Enabled**: Should show 1
   - **Mandatory/Optional**: Should match your policy type

---

## Common Use Cases

### Use Case 1: Require 2FA for Administrators

**Scenario**: All admin and superadmin users must have 2FA enabled.

**Configuration**:

```json
{
  "name": "Administrator 2FA Requirement",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "mandatory",
  "affected_roles": ["admin", "superadmin"],
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "All administrators must have 2FA enabled"
}
```

**Result**: Admin users without 2FA will receive 403 Forbidden when accessing protected endpoints.

### Use Case 2: 2FA Recommended for Moderators

**Scenario**: Moderators should have 2FA but it's not required.

**Configuration**:

```json
{
  "name": "Moderator 2FA Recommendation",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "optional",
  "affected_roles": ["moderator"],
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "2FA is recommended for moderators"
}
```

**Result**: Moderators will see warnings but can access the system without 2FA.

### Use Case 3: Test Policy Impact Before Enforcement

**Scenario**: Roll out 2FA policy gradually by monitoring compliance first.

**Configuration**:

```json
{
  "name": "2FA Compliance Monitoring",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "audit_only",
  "affected_roles": null,
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "Monitor 2FA compliance across all users"
}
```

**Result**: All users without 2FA will be logged but access will not be blocked. Review audit logs to assess compliance before switching to "mandatory".

### Use Case 4: Grace Period for New Users

**Scenario**: Require 2FA for all users, but allow 48 hours for setup.

**Configuration**:

```json
{
  "name": "Universal 2FA with Grace Period",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "mandatory",
  "affected_roles": null,
  "grace_period_hours": 48,
  "allow_exempt_alternative_auth": false,
  "description": "All users must enable 2FA within 48 hours of account creation"
}
```

**Result**: New users can access the system for 48 hours, after which 2FA is required.

### Use Case 5: Exempt SAML Users

**Scenario**: Require 2FA for direct login users, but exempt those using SAML SSO.

**Configuration**:

```json
{
  "name": "2FA for Direct Login Only",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "mandatory",
  "affected_roles": null,
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": true,
  "description": "2FA required for password-based login, SAML users exempt"
}
```

**Result**: Users who authenticated via SAML are not required to have 2FA enabled. Users who logged in with email/password must have 2FA.

### Use Case 6: Role-Based Progressive Enforcement

**Scenario**: Different 2FA requirements for different roles.

**Configuration**:

Create multiple policies:

```json
// Policy 1: Superadmins (mandatory, immediate)
{
  "name": "Superadmin 2FA",
  "enabled": true,
  "enforcement_level": "mandatory",
  "affected_roles": ["superadmin"],
  "grace_period_hours": 0
}

// Policy 2: Admins (mandatory, 24h grace)
{
  "name": "Admin 2FA",
  "enabled": true,
  "enforcement_level": "mandatory",
  "affected_roles": ["admin"],
  "grace_period_hours": 24
}

// Policy 3: Moderators (optional)
{
  "name": "Moderator 2FA",
  "enabled": true,
  "enforcement_level": "optional",
  "affected_roles": ["moderator"],
  "grace_period_hours": 0
}
```

**Result**: Each role has appropriate 2FA requirements.

### Use Case 7: Temporary High-Security Event

**Scenario**: Require 2FA for all users during a security-sensitive period.

**Configuration**:

```json
{
  "name": "Temporary Security Event 2FA",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "mandatory",
  "affected_roles": null,
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "Temporary 2FA requirement for security event - 2026-01-23"
}
```

**Result**: All users require 2FA. Disable the policy after the event ends.

### Use Case 8: Compliance Requirement

**Scenario**: Meet regulatory compliance requiring MFA for access to personal data.

**Configuration**:

```json
{
  "name": "GDPR Compliance 2FA",
  "enabled": true,
  "policy_type": "2fa_enforcement",
  "enforcement_level": "mandatory",
  "affected_roles": null,
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "MFA required for GDPR compliance - data access protection"
}
```

**Result**: Compliant with GDPR Article 32 (security of processing).

---

## Testing and Verification

### Test 1: Create Policy via API

**API Request**:
```bash
curl -X POST https://streamer.example.com/api/admin/security-policies/policies \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Policy",
    "policy_type": "2fa_enforcement",
    "enabled": false,
    "enforcement_level": "audit_only",
    "affected_roles": ["admin"],
    "grace_period_hours": 0,
    "description": "Test policy for verification"
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Test Policy",
  "policy_type": "2fa_enforcement",
  "enabled": false,
  "enforcement_level": "audit_only",
  "affected_roles": ["admin"],
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "description": "Test policy for verification",
  "created_by_id": "...",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

### Test 2: List Policies

**API Request**:
```bash
curl https://streamer.example.com/api/admin/security-policies/policies \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response** (200 OK):
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Test Policy",
    "enabled": false,
    "enforcement_level": "audit_only",
    ...
  }
]
```

### Test 3: Enable Policy

**API Request**:
```bash
curl -X POST https://streamer.example.com/api/admin/security-policies/policies/{policy_id}/enable \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Security policy enabled",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "enabled": true
}
```

### Test 4: Check Policy Application

**API Request**:
```bash
curl -X POST "https://streamer.example.com/api/admin/security-policies/policies/check?role=admin" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response** (200 OK):
```json
{
  "policy_id": "123e4567-e89b-12d3-a456-426614174000",
  "policy_name": "Test Policy",
  "policy_type": "2fa_enforcement",
  "role": "admin",
  "applies": true,
  "enabled": true,
  "enforcement_level": "audit_only",
  "is_mandatory": false,
  "is_optional": false,
  "is_audit_only": true,
  "affected_roles": ["admin"]
}
```

### Test 5: Test Mandatory Enforcement (No 2FA)

**Setup**:
1. Create a test user with admin role
2. Create a mandatory 2FA policy for admin role
3. Ensure test user does NOT have 2FA enabled
4. Attempt to access protected endpoint

**API Request**:
```bash
curl -i https://streamer.example.com/api/admin/users \
  -H "Authorization: Bearer <test-user-token-without-2fa>"
```

**Expected Response** (403 Forbidden):
```
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": {
    "error": "2FA_REQUIRED",
    "message": "Two-factor authentication is required for this account",
    "policy": "Test Policy"
  }
}
```

### Test 6: Test Grace Period

**Setup**:
1. Create a new user account
2. Create a mandatory 2FA policy with 24-hour grace period
3. Attempt access immediately after account creation

**API Request**:
```bash
curl -i https://streamer.example.com/api/admin/users \
  -H "Authorization: Bearer <new-user-token-without-2fa>"
```

**Expected Response** (200 OK):
```
HTTP/1.1 200 OK
```

**Reason**: User is within the 24-hour grace period.

### Test 7: Test Audit Only Mode

**Setup**:
1. Create an audit-only 2FA policy
2. Attempt access without 2FA

**API Request**:
```bash
curl -i https://streamer.example.com/api/admin/users \
  -H "Authorization: Bearer <user-token-without-2fa>"
```

**Expected Response** (200 OK):
```
HTTP/1.1 200 OK
```

**Verification**:
1. Check backend logs for audit entry
2. Check audit logs table for `2fa_policy_violation` event

### Test 8: Test with 2FA Enabled

**Setup**:
1. Enable TOTP for a test user
2. Create a mandatory 2FA policy
3. Access protected endpoint

**API Request**:
```bash
curl -i https://streamer.example.com/api/admin/users \
  -H "Authorization: Bearer <user-token-with-2fa>"
```

**Expected Response** (200 OK):
```
HTTP/1.1 200 OK
Content-Type: application/json

{...}
```

### Test 9: Test Role Exemption

**Setup**:
1. Create policy for admin role only
2. Attempt access with regular user (without 2FA)

**API Request**:
```bash
curl -i https://streamer.example.com/api/admin/users \
  -H "Authorization: Bearer <regular-user-token-without-2fa>"
```

**Expected Response** (200 OK):
```
HTTP/1.1 200 OK
```

**Reason**: Policy only applies to admin role, not regular user role.

### Test 10: Verify Audit Logging

**API Request**:
```bash
curl https://streamer.example.com/api/admin/audit \
  -H "Authorization: Bearer <admin-token>" \
  -G \
  --data-urlencode "event_type=2fa_policy_violation"
```

**Expected Response** (200 OK):
```json
[
  {
    "id": "...",
    "event_type": "2fa_policy_violation",
    "message": "2FA policy audit: user {user_id} does not have 2FA enabled",
    "user_id": "...",
    "details": {
      "policy_name": "Test Policy",
      "enforcement_level": "audit_only"
    },
    "created_at": "2026-01-23T10:00:00Z"
  }
]
```

---

## Advanced Configuration

### Understanding Policy Precedence

When multiple policies apply to a user, the system selects the most strict one:

**Precedence Order** (highest to lowest):
1. **Mandatory** → Blocks access without 2FA
2. **Audit Only** → Logs but allows access
3. **Optional** → Warns but allows access

**Example**:
```json
// Policy 1: Optional for admin
{"name": "Policy A", "enforcement_level": "optional", "affected_roles": ["admin"]}

// Policy 2: Mandatory for all roles
{"name": "Policy B", "enforcement_level": "mandatory", "affected_roles": null}
```

**Result**: Admin users will be subject to Policy B (mandatory), as it's stricter.

### Grace Period Calculation

The grace period is based on the user's account creation time:

```python
# Pseudocode
account_age = current_time - user.created_at
grace_period_seconds = policy.grace_period_hours * 3600

if account_age < grace_period_seconds:
    # User is within grace period, allow access
    return True
else:
    # Grace period expired, enforce policy
    return has_2fa_enabled
```

**Example**:
- User created: 2026-01-23 10:00:00
- Grace period: 24 hours
- Current time: 2026-01-23 18:00:00 (8 hours later)
- Account age: 8 hours < 24 hours grace period
- **Result**: Access allowed without 2FA

### Alternative Authentication Exemption

Users who authenticated via SAML SSO can be exempt from 2FA requirements:

```python
# Pseudocode
if policy.allow_exempt_alternative_auth:
    if user.auth_method == "saml":
        # Exempt from 2FA requirement
        return True
```

**Configuration**:
```json
{
  "allow_exempt_alternative_auth": true
}
```

**Use Case**: Your organization uses SAML with MFA at the IdP level, making application-level 2FA redundant.

### Custom Enforcement Logic

You can create custom enforcement logic by extending the base dependency:

```python
from src.frameworks.http.middleware.two_factor_enforcement import enforce_2fa_policy

async def custom_2fa_requirement(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
) -> User:
    # Check basic 2FA policy
    user = await enforce_2fa_dependency(current_user, db)

    # Add custom logic
    if user.email.endswith("@external-partner.com"):
        # External partners always need 2FA, regardless of policy
        if not user.totp_enabled:
            raise HTTPException(
                status_code=403,
                detail="External partners must have 2FA enabled"
            )

    return user

# Use in endpoint
@app.get("/api/partners/data")
async def partner_data(
    user: User = Depends(custom_2fa_requirement)
):
    return {"data": "..."}
```

### Combining with Other Security Features

2FA enforcement works best when combined with other security measures:

#### 1. IP Whitelisting + 2FA

```python
from src.frameworks.http.middleware.ip_whitelist import IPWhitelistMiddleware
from src.frameworks.http.middleware.two_factor_enforcement import TwoFactorEnforcementMiddleware

# Apply both middlewares
app.add_middleware(IPWhitelistMiddleware)
app.add_middleware(TwoFactorEnforcementMiddleware, protected_paths=["/api/admin"])
```

**Result**: Users must be from whitelisted IP AND have 2FA enabled.

#### 2. SAML SSO + 2FA

```json
{
  "name": "Hybrid Authentication Policy",
  "enforcement_level": "mandatory",
  "affected_roles": ["admin"],
  "allow_exempt_alternative_auth": true,
  "description": "2FA required for password login, SAML users exempt"
}
```

**Result**:
- SAML users: Exempt from 2FA (IdP provides MFA)
- Password users: Must have 2FA enabled

#### 3. Role-Based Access Control (RBAC) + 2FA

```python
@app.get("/api/admin/sensitive")
async def sensitive_data(
    user: User = Depends(require_admin),  # RBAC check
    _ = Depends(enforce_2fa_policy)       # 2FA check
):
    return {"data": "..."}
```

**Result**: User must be admin AND have 2FA enabled.

### Endpoint-Level vs Global Enforcement

#### Global Middleware Enforcement

**Pros**:
- Consistent across all protected paths
- Centralized configuration
- No code changes needed for new endpoints

**Cons**:
- Coarse-grained (all-or-nothing per path)
- Can't customize behavior per endpoint

**Use Case**: Protect entire `/api/admin` tree uniformly.

#### Endpoint-Level Dependency Enforcement

**Pros**:
- Fine-grained control per endpoint
- Can customize enforcement logic
- Flexible for different security requirements

**Cons**:
- Requires code changes for each endpoint
- Can be forgotten when adding new endpoints

**Use Case**: Specific sensitive endpoints need stronger security.

### Monitoring Policy Compliance

Create an endpoint to monitor 2FA compliance:

```python
@app.get("/api/admin/security/2fa-compliance")
async def get_2fa_compliance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get 2FA compliance statistics."""
    total_users = db.query(User).count()
    users_with_2fa = db.query(User).filter(User.totp_enabled == True).count()
    compliance_rate = (users_with_2fa / total_users * 100) if total_users > 0 else 0

    # By role
    by_role = {}
    for role in ["superadmin", "admin", "moderator", "user"]:
        role_users = db.query(User).filter(User.role == role).all()
        role_with_2fa = [u for u in role_users if u.totp_enabled]
        by_role[role] = {
            "total": len(role_users),
            "with_2fa": len(role_with_2fa),
            "compliance_rate": len(role_with_2fa) / len(role_users) * 100 if role_users else 0
        }

    return {
        "overall": {
            "total_users": total_users,
            "users_with_2fa": users_with_2fa,
            "compliance_rate": compliance_rate
        },
        "by_role": by_role
    }
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "2FA_REQUIRED" Error

**Symptoms**:
- 403 Forbidden response
- Error: `"Two-factor authentication is required for this account"`

**Possible Causes**:
- User doesn't have 2FA enabled
- Mandatory 2FA policy applies to user's role
- Grace period has expired

**Solutions**:

1. **Enable 2FA for the user**:
   ```bash
   # User must enable TOTP via settings
   # Navigate to /settings/security and enable 2FA
   ```

2. **Check policy configuration**:
   ```bash
   curl https://streamer.example.com/api/admin/security-policies/policies \
     -H "Authorization: Bearer <admin-token>"
   ```

3. **Verify user's role and grace period**:
   ```bash
   curl https://streamer.example.com/api/admin/users/{user_id} \
     -H "Authorization: Bearer <admin-token>"
   ```

4. **Temporarily disable policy** (for testing):
   ```bash
   curl -X POST https://streamer.example.com/api/admin/security-policies/policies/{policy_id}/disable \
     -H "Authorization: Bearer <admin-token>"
   ```

#### 2. Policy Not Enforcing

**Symptoms**:
- Users without 2FA can access protected endpoints
- No 403 errors despite mandatory policy

**Possible Causes**:
- Policy is disabled
- Policy doesn't apply to user's role
- Middleware not configured
- Endpoint not protected

**Solutions**:

1. **Check if policy is enabled**:
   ```bash
   curl https://streamer.example.com/api/admin/security-policies/policies/{policy_id} \
     -H "Authorization: Bearer <admin-token>" | jq '.enabled'
   ```

2. **Verify affected_roles**:
   - If `affected_roles` is `null`, policy applies to all roles
   - If `affected_roles` is `["admin"]`, policy only applies to admins
   - Check user's role matches

3. **Check middleware configuration**:
   ```python
   # In backend/src/frameworks/http/app.py
   # Verify middleware is added
   app.add_middleware(TwoFactorEnforcementMiddleware)
   ```

4. **Verify endpoint uses dependency** (if not using middleware):
   ```python
   @app.get("/api/endpoint")
   async def endpoint(
       user: User = Depends(enforce_2fa_policy)  # Check this
   ):
       pass
   ```

5. **Check environment variables**:
   ```bash
   # backend/.env
   TWO_FA_ENFORCEMENT_ENABLED=true  # Should be true
   ```

#### 3. Grace Period Not Working

**Symptoms**:
- New users blocked immediately despite grace period
- Grace period ignored

**Possible Causes**:
- `grace_period_hours` is 0
- User's `created_at` timestamp is incorrect
- Policy was created after user account

**Solutions**:

1. **Check grace_period_hours**:
   ```bash
   curl https://streamer.example.com/api/admin/security-policies/policies/{policy_id} \
     -H "Authorization: Bearer <admin-token>" | jq '.grace_period_hours'
   ```

2. **Verify user's created_at**:
   ```bash
   curl https://streamer.example.com/api/admin/users/{user_id} \
     -H "Authorization: Bearer <admin-token>" | jq '.created_at'
   ```

3. **Calculate account age manually**:
   ```python
   from datetime import datetime, timezone

   created_at = datetime.fromisoformat("2026-01-23T10:00:00")
   account_age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
   grace_period_hours = 24

   print(f"Account age: {account_age_hours:.2f} hours")
   print(f"Grace period: {grace_period_hours} hours")
   print(f"Within grace period: {account_age_hours < grace_period_hours}")
   ```

#### 4. Audit Mode Not Logging

**Symptoms**:
- Audit-only policy not creating log entries
- No violations recorded

**Possible Causes**:
- Logging not configured
- Audit log table not created
- Event type incorrect

**Solutions**:

1. **Check logging configuration**:
   ```bash
   # backend/.env
   LOG_LEVEL=DEBUG
   ENVIRONMENT=development
   ```

2. **Check backend logs**:
   ```bash
   # Look for log entries like:
   # "2FA policy audit: user {user_id} does not have 2FA enabled"
   ```

3. **Verify audit table exists**:
   ```sql
   SELECT * FROM audit_logs
   WHERE event_type = '2fa_policy_violation'
   ORDER BY created_at DESC
   LIMIT 10;
   ```

#### 5. All Users Locked Out

**Symptoms**:
- Everyone blocked including admins
- Cannot access admin panel to fix

**Possible Causes**:
- Mandatory policy enabled with no grace period
- All users lack 2FA
- Policy applies to all roles

**Solutions**:

1. **Access via direct database**:
   ```sql
   -- Disable the policy
   UPDATE security_policies
   SET enabled = false
   WHERE policy_type = '2fa_enforcement';
   ```

2. **Disable via environment variable**:
   ```bash
   # backend/.env
   TWO_FA_ENFORCEMENT_ENABLED=false
   ```

   Then restart backend service:
   ```bash
   systemctl restart backend
   ```

3. **Access from loopback** (if middleware allows):
   ```bash
   # From server itself
   curl https://localhost/api/admin/security-policies/policies/{policy_id}/disable \
     -H "Authorization: Bearer <admin-token>"
   ```

4. **Enable 2FA for a user via database**:
   ```sql
   -- Enable 2FA for an admin user
   UPDATE users
   SET totp_enabled = true
   WHERE email = 'admin@example.com' AND role = 'admin';
   ```

   Then use that account to disable the policy.

#### 6. Performance Issues

**Symptoms**:
- Slow response times on protected endpoints
- Increased database load

**Possible Causes**:
- Database query on every request
- No caching
- Multiple active policies

**Solutions**:

1. **Reduce number of active policies**:
   - Consolidate policies where possible
   - Disable unused policies

2. **Add database index**:
   ```sql
   CREATE INDEX idx_security_policies_enabled_type
   ON security_policies(enabled, policy_type);
   ```

3. **Implement caching** (if not already):
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def get_cached_policies():
       # Cache policies for 5 minutes
       pass
   ```

#### 7. Policy Not Applying to Expected Role

**Symptoms**:
- Policy should apply to admins but doesn't
- Role mismatch

**Possible Causes**:
- Role name typo in `affected_roles`
- Case sensitivity
- User's role doesn't match

**Solutions**:

1. **Check policy configuration**:
   ```bash
   curl https://streamer.example.com/api/admin/security-policies/policies/{policy_id} \
     -H "Authorization: Bearer <admin-token>" | jq '.affected_roles'
   ```

2. **Check user's role**:
   ```bash
   curl https://streamer.example.com/api/admin/users/{user_id} \
     -H "Authorization: Bearer <admin-token>" | jq '.role'
   ```

3. **Test policy application**:
   ```bash
   curl -X POST "https://streamer.example.com/api/admin/security-policies/policies/check?role=admin" \
     -H "Authorization: Bearer <admin-token>"
   ```

**Note**: Role matching is case-sensitive. Ensure consistency (e.g., "admin" not "Admin").

### Debug Logging

Enable detailed 2FA enforcement logging:

```bash
# backend/.env
LOG_LEVEL=DEBUG
ENVIRONMENT=development
TWO_FA_ENFORCEMENT_ENABLED=true
```

Debug logs will include:
- Active policies retrieved
- User's role and 2FA status
- Policy application decisions
- Grace period calculations
- Enforcement actions taken

### Testing Tools

#### Test Policy Application

```python
import requests

def test_policy_enforcement(user_token, policy_id):
    """Test if policy is enforced for a user."""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Try to access protected endpoint
    response = requests.get(
        "https://streamer.example.com/api/admin/users",
        headers=headers
    )

    if response.status_code == 403:
        print("✓ Policy enforced - 2FA required")
        print(f"  Error: {response.json()}")
    elif response.status_code == 200:
        print("✓ Access granted - user has 2FA or policy doesn't apply")
    else:
        print(f"✗ Unexpected status: {response.status_code}")

# Usage
test_policy_enforcement("your-token-here", "policy-id-here")
```

#### Batch Check User 2FA Status

```python
import requests

def check_users_2fa_status(admin_token):
    """Check which users have 2FA enabled."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get all users
    users = requests.get(
        "https://streamer.example.com/api/admin/users",
        headers=headers
    ).json()

    # Check 2FA status
    for user in users:
        status = "✓" if user.get("totp_enabled") else "✗"
        print(f"{status} {user['email']} ({user.get('role', 'user')})")

# Usage
check_users_2fa_status("your-admin-token")
```

---

## Security Best Practices

### 1. Progressive Rollout

**Recommendation**: Start with audit-only mode, then move to mandatory.

**Implementation**:
```json
// Phase 1: Audit only (1-2 weeks)
{"enforcement_level": "audit_only", ...}

// Phase 2: Mandatory with grace period (2-4 weeks)
{"enforcement_level": "mandatory", "grace_period_hours": 168, ...}

// Phase 3: Mandatory enforcement
{"enforcement_level": "mandatory", "grace_period_hours": 0, ...}
```

**Rationale**: Allows users to adapt and identifies issues before full enforcement.

### 2. Role-Based Policy Design

**Recommendation**: Apply stricter policies to higher-privilege roles.

**Implementation**:
```json
// Superadmins: Mandatory, no grace
{
  "affected_roles": ["superadmin"],
  "enforcement_level": "mandatory",
  "grace_period_hours": 0
}

// Admins: Mandatory, with grace
{
  "affected_roles": ["admin"],
  "enforcement_level": "mandatory",
  "grace_period_hours": 24
}

// Users: Optional
{
  "affected_roles": ["user"],
  "enforcement_level": "optional",
  "grace_period_hours": 0
}
```

**Rationale**: Balances security with user experience based on access level.

### 3. Grace Period Best Practices

**Recommendation**: Use appropriate grace periods for different scenarios.

| Scenario | Recommended Grace Period |
|----------|-------------------------|
| New employee onboarding | 40 hours (1 work week) |
| Existing users (new policy) | 168 hours (1 week) |
| Contractors/temps | 0 hours (immediate) |
| Security event response | 0 hours (immediate) |

**Rationale**: Provides time for setup without compromising security.

### 4. Monitor Compliance

**Recommendation**: Track 2FA adoption rates before mandatory enforcement.

**Implementation**:
```python
# Weekly compliance report
def generate_compliance_report():
    users = db.query(User).all()
    total = len(users)
    with_2fa = len([u for u in users if u.totp_enabled])

    print(f"2FA Compliance: {with_2fa}/{total} ({with_2fa/total*100:.1f}%)")

    # By role
    for role in ["admin", "moderator", "user"]:
        role_users = [u for u in users if u.role == role]
        role_with_2fa = [u for u in role_users if u.totp_enabled]
        print(f"  {role}: {len(role_with_2fa)}/{len(role_users)}")
```

**Rationale**: Data-driven decisions on when to enforce mandatory 2FA.

### 5. Backup Authentication Methods

**Recommendation**: Maintain alternative access for emergency situations.

**Implementation**:
- Keep one emergency admin account with 2FA pre-configured
- Store recovery codes securely
- Document emergency disable procedures

**Rationale**: Prevents lockout scenarios during mass 2FA deployment.

### 6. User Communication

**Recommendation**: Communicate 2FA requirements clearly to users.

**Implementation**:
1. **Announcement**: Notify users 2 weeks before policy change
2. **Documentation**: Provide setup guides
3. **Support**: Offer help desk assistance
4. **Reminders**: Send notifications as grace period expires

**Example Email Template**:
```
Subject: Action Required: Enable Two-Factor Authentication by [Date]

Dear [User Name],

To protect your account and our organization's data, we will require
two-factor authentication (2FA) for all [role] accounts starting [date].

What You Need to Do:
1. Log in to your account
2. Navigate to Settings → Security
3. Enable Two-Factor Authentication
4. Scan the QR code with your authenticator app
5. Save your backup codes

Need Help?
- Documentation: [Link]
- Support: support@example.com

Please complete this setup by [date] to avoid account disruption.

Security Team
```

**Rationale**: Reduces support tickets and user frustration.

### 7. Regular Policy Reviews

**Recommendation**: Review 2FA policies quarterly.

**Review Checklist**:
- [ ] Are all policies still necessary?
- [ ] Are affected_roles still accurate?
- [ ] Should grace periods be adjusted?
- [ ] Have new roles been added that need policies?
- [ ] Are exemption rules still appropriate?

**Rationale**: Ensures policies remain aligned with organizational needs.

### 8. Combining with Other Security Measures

**Recommendation**: Use 2FA as part of a defense-in-depth strategy.

**Complementary Measures**:
- **IP Whitelisting**: Restrict access to trusted networks
- **SAML SSO**: Centralized authentication with IdP MFA
- **Rate Limiting**: Prevent brute force attacks
- **Session Management**: Appropriate timeout values
- **Audit Logging**: Track all access and modifications

**Implementation**:
```python
# Layered security
app.add_middleware(IPWhitelistMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TwoFactorEnforcementMiddleware)
```

**Rationale**: Multiple layers provide better protection than any single measure.

### 9. Backup and Recovery

**Recommendation**: Maintain procedures for 2FA recovery.

**Implementation**:
1. **Backup Codes**: Generate and securely store
2. **Recovery Process**: Document user account recovery
3. **Admin Override**: Emergency admin procedures

```python
# Generate backup codes when enabling 2FA
def generate_backup_codes():
    codes = [secrets.token_hex(4) for _ in range(10)]
    return codes

# Store encrypted in database
backup_codes_encrypted = encrypt_backup_codes(codes)
```

**Rationale**: Prevents permanent lockout if device is lost.

### 10. Compliance Considerations

#### SOC 2 Compliance

2FA enforcement contributes to SOC 2:

- **Access Control**: Implements MFA for system access
- **Monitoring**: Logs all policy violations
- **Audit Trail**: Complete history of enforcement actions

**Evidence for Auditors**:
- 2FA policy configurations from database
- Compliance reports showing 2FA adoption
- Audit logs of enforcement actions
- Policy change history

#### GDPR Compliance

2FA supports GDPR Article 32 (security of processing):

- **Data Protection**: MFA protects personal data
- **Access Control**: Limits unauthorized access
- **Accountability**: Logs provide evidence

**Consideration**:
- 2FA secrets (TOTP) should be encrypted at rest
- Backup codes are sensitive data (protect accordingly)

#### HIPAA Compliance

For healthcare applications:

- 2FA is required for access to ePHI
- Mandatory enforcement for all roles handling patient data
- Audit logging of all access attempts

**Implementation**:
```json
{
  "name": "HIPAA 2FA Requirement",
  "enforcement_level": "mandatory",
  "affected_roles": null,
  "description": "MFA required for HIPAA compliance - ePHI access"
}
```

---

## API Reference

### Security Policy Management Endpoints

#### List All Policies

```http
GET /api/admin/security-policies/policies
Authorization: Bearer <admin-token>

Query Parameters:
  - enabled_only: boolean (default: false)
  - policy_type: string (e.g., "2fa_enforcement")
  - enforcement_level: string (e.g., "mandatory")
```

**Response** (200 OK):
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Admin 2FA Requirement",
    "policy_type": "2fa_enforcement",
    "enabled": true,
    "enforcement_level": "mandatory",
    "affected_roles": ["admin", "superadmin"],
    "grace_period_hours": 0,
    "allow_exempt_alternative_auth": false,
    "policy_config": null,
    "description": "Requires 2FA for admin users",
    "created_by_id": "...",
    "created_at": "2026-01-23T10:00:00Z",
    "updated_at": "2026-01-23T10:00:00Z"
  }
]
```

#### Get Policy Info

```http
GET /api/admin/security-policies/policies/info
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "total_policies": 5,
  "enabled_policies": 3,
  "disabled_policies": 2,
  "mandatory_policies": 2,
  "optional_policies": 1,
  "audit_only_policies": 2,
  "policies_by_type": {
    "2fa_enforcement": 3,
    "password_complexity": 1,
    "session_timeout": 1
  }
}
```

#### Get Single Policy

```http
GET /api/admin/security-policies/policies/{policy_id}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Admin 2FA Requirement",
  "policy_type": "2fa_enforcement",
  "enabled": true,
  "enforcement_level": "mandatory",
  "affected_roles": ["admin", "superadmin"],
  "grace_period_hours": 0,
  "allow_exempt_alternative_auth": false,
  "policy_config": null,
  "description": "Requires 2FA for admin users",
  "created_by_id": "...",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

#### Create Policy

```http
POST /api/admin/security-policies/policies
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "name": "Admin 2FA Requirement",
  "policy_type": "2fa_enforcement",
  "enabled": false,
  "enforcement_level": "mandatory",
  "affected_roles": ["admin", "superadmin"],
  "grace_period_hours": 24,
  "allow_exempt_alternative_auth": false,
  "description": "Requires 2FA for all admin users"
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Admin 2FA Requirement",
  "policy_type": "2fa_enforcement",
  "enabled": false,
  "enforcement_level": "mandatory",
  ...
}
```

**Error Responses**:
- `400 Bad Request`: Invalid policy configuration
- `400 Bad Request`: Policy name already exists

#### Update Policy

```http
PUT /api/admin/security-policies/policies/{policy_id}
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "enabled": true,
  "grace_period_hours": 48
}
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Admin 2FA Requirement",
  ...
}
```

#### Delete Policy

```http
DELETE /api/admin/security-policies/policies/{policy_id}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Security policy deleted",
  "id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Enable Policy

```http
POST /api/admin/security-policies/policies/{policy_id}/enable
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Security policy enabled",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "enabled": true
}
```

#### Disable Policy

```http
POST /api/admin/security-policies/policies/{policy_id}/disable
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Security policy disabled",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "enabled": false
}
```

#### Check Policy Application

```http
POST /api/admin/security-policies/policies/check?role={role}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "policy_id": "123e4567-e89b-12d3-a456-426614174000",
  "policy_name": "Admin 2FA Requirement",
  "policy_type": "2fa_enforcement",
  "role": "admin",
  "applies": true,
  "enabled": true,
  "enforcement_level": "mandatory",
  "is_mandatory": true,
  "is_optional": false,
  "is_audit_only": false,
  "affected_roles": ["admin", "superadmin"]
}
```

---

## Glossary

| Term | Definition |
|------|------------|
| **2FA** | Two-Factor Authentication - Security process requiring two forms of authentication |
| **MFA** | Multi-Factor Authentication - General term for authentication using multiple factors |
| **TOTP** | Time-based One-Time Password - Type of 2FA using time-limited codes (e.g., Google Authenticator) |
| **Security Policy** | Database rule defining security requirements like 2FA enforcement |
| **Enforcement Level** | strictness of policy: mandatory, optional, or audit_only |
| **Grace Period** | Time period after account creation during which policy is not enforced |
| **Affected Roles** | List of user roles to which a policy applies (null = all roles) |
| **Mandatory** | Policy blocks access if requirements not met |
| **Optional** | Policy warns but allows access |
| **Audit Only** | Policy logs violations but does not block access |
| **Alternative Auth** | Authentication methods other than username/password (e.g., SAML SSO) |
| **RBAC** | Role-Based Access Control - Managing access based on user roles |
| **Dependency** | FastAPI mechanism for enforcing requirements on endpoints |
| **Middleware** | Software component that processes requests before handlers |
| **Compliance Rate** | Percentage of users who meet security requirements |

---

## Related Documentation

### Internal Resources

- **Security Dashboard**: `/admin/security` - Compliance and security overview
- **SSO Setup Guide**: `docs/security/SSO_SETUP_GUIDE.md` - SAML configuration
- **IP Whitelist Guide**: `docs/security/IP_WHITELIST_GUIDE.md` - Network access control
- **SOC 2 Compliance**: `docs/compliance/SOC2_README.md` - Compliance documentation
- **GDPR Compliance**: `docs/compliance/GDPR_README.md` - Data protection documentation

### External Resources

- **NIST Digital Identity Guidelines**: https://pages.nist.gov/800-63-3/
- **OWASP Multi-Factor Authentication**: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
- **Authenticator Apps**: Google Authenticator, Authy, Microsoft Authenticator, 1Password
- **TOTP Specification**: RFC 6238 - https://tools.ietf.org/html/rfc6238

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-23 | Initial release with TOTP enforcement, role-based policies, grace periods, and audit logging |

---

**Document ID:** 2FA_ENFORCEMENT_GUIDE
**Status:** Active
**Classification:** Public Documentation
