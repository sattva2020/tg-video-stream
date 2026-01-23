# SSO/SAML Setup Guide for Administrators

## Overview

This guide provides step-by-step instructions for configuring Single Sign-On (SSO) using SAML 2.0 for the Telegram Streamer platform. SSO allows users to authenticate using their corporate identity provider credentials, providing a seamless and secure authentication experience.

**Last Updated:** 2026-01-23
**Supported Protocols:** SAML 2.0
**Supported Identity Providers:** Okta, Azure AD, Google Workspace, OneLogin,及其他SAML-compatible IdPs

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding SAML SSO](#understanding-saml-sso)
3. [Configuration Overview](#configuration-overview)
4. [Setup Instructions by Identity Provider](#setup-instructions-by-identity-provider)
5. [Application Configuration](#application-configuration)
6. [Testing and Verification](#testing-and-verification)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Access

- **Administrator Account**: You must have admin or superadmin privileges in the Telegram Streamer application
- **IdP Admin Access**: Administrator access to your organization's Identity Provider (Okta, Azure AD, etc.)
- **HTTPS**: Your application must be accessible via HTTPS with a valid SSL certificate

### Information to Gather

Before starting the setup, collect the following information:

- **Application Base URL**: e.g., `https://streamer.example.com`
- **ACS URL**: The Assertion Consumer Service URL where SAML responses will be sent
  - Format: `https://streamer.example.com/api/auth/saml/acs`
- **Entity ID**: Unique identifier for your application instance
  - Typically: `https://streamer.example.com` or a custom string
- **SAML Metadata URL**: (Optional) URL where your application's SAML metadata is published
  - Format: `https://streamer.example.com/api/auth/saml/metadata`

### Required IdP Information

From your Identity Provider, you will need:

- **IdP Entity ID**: Unique identifier for the IdP
- **SSO URL**: The IdP's Single Sign-On service URL
- **SLO URL**: (Optional) The IdP's Single Logout service URL
- **X.509 Certificate**: The IdP's public certificate for verifying SAML signatures
- **Metadata URL**: (Optional) URL to download IdP metadata

---

## Understanding SAML SSO

### How SAML Authentication Works

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│   User  │                    │   App   │                    │   IdP   │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │ 1. Click SSO Login           │                              │
     ├─────────────────────────────>│                              │
     │                              │                              │
     │                              │ 2. Redirect to IdP           │
     │                              ├─────────────────────────────>│
     │                              │                              │
     │                              │ 3. Authenticate User         │
     │                              │<─────────────────────────────┤
     │                              │                              │
     │                              │ 4. SAML Assertion (POST)      │
     │                              │<─────────────────────────────┤
     │                              │                              │
     │ 5. Create Session            │                              │
     │ 6. Redirect to Dashboard     │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
```

### Key Components

1. **Service Provider (SP)**: Your Telegram Streamer application
2. **Identity Provider (IdP)**: Your corporate authentication system (Okta, Azure AD, etc.)
3. **SAML Assertion**: XML document containing user authentication and attribute data
4. **ACS (Assertion Consumer Service)**: Endpoint that receives and processes SAML responses
5. **Metadata**: XML document describing configuration and capabilities

### User Provisioning

When users authenticate via SAML:

1. **First Login**: User account is automatically created if it doesn't exist
2. **Attribute Mapping**: User attributes (email, name, etc.) are extracted from SAML assertion
3. **Role Assignment**: User roles are mapped from IdP groups to application roles
4. **Subsequent Logins**: Existing user accounts are updated with latest attributes

---

## Configuration Overview

### Application Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Display name for this SAML configuration | "Okta SSO" |
| **Enabled** | Whether this SSO configuration is active | `true` |
| **IdP Entity ID** | Unique identifier for the IdP | `"https://okta.com/saml-id"` |
| **IdP SSO URL** | URL to initiate SSO at IdP | `"https://okta.com/sso/saml"` |
| **IdP X.509 Certificate** | IdP's public certificate (PEM format) | `"MIIDp...\n..."` |
| **IdP SLO URL** | (Optional) URL for single logout | `"https://okta.com/slo/saml"` |
| **IdP Metadata URL** | (Optional) URL to download IdP metadata | `"https://okta.com/metadata"` |
| **SP Entity ID** | Unique identifier for your application | `"https://streamer.example.com"` |
| **SP ACS URL** | Assertion Consumer Service URL | `"https://streamer.example.com/api/auth/saml/acs"` |
| **SP SLO URL** | (Optional) Single Logout service URL | `"https://streamer.example.com/api/auth/saml/slo"` |
| **Name ID Format** | Format for user identifier | `"urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"` |
| **Attribute Mapping** | Map SAML attributes to user fields | `{"email": "user.email", "full_name": "user.displayName"}` |
| **Role Mapping** | Map IdP groups to application roles | `{"TelegramStreamer-Admins": "admin"}` |

---

## Setup Instructions by Identity Provider

### 1. Okta

#### Step 1: Create Application in Okta

1. Log in to your Okta Admin Console
2. Navigate to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select **SAML 2.0** and click **Next**
5. Configure **General Settings**:
   - **App name**: "Telegram Streamer" (or your preferred name)
   - **App logo**: (Optional) Upload your application logo
   - **App visibility**: Choose who should see this application
6. Click **Next**

#### Step 2: Configure SAML in Okta

On the **SAML Sign-On** settings page:

1. **Single Sign-On URL**:
   ```
   https://streamer.example.com/api/auth/saml/acs
   ```
   Replace with your actual ACS URL

2. **Audience URI (SP Entity ID)**:
   ```
   https://streamer.example.com
   ```
   Replace with your actual application URL

3. **Name ID Format**: Select `EmailAddress`

4. **Application Username**: Select `Email`

5. **Attributes** (Click **Add Attribute** for each):
   | Name (Okta) | Name (Format) | Value |
   |-------------|---------------|-------|
   | `email` | `Unspecified` | `user.email` |
   | `firstName` | `Unspecified` | `user.firstName` |
   | `lastName` | `Unspecified` | `user.lastName` |
   | `displayName` | `Unspecified` | `${user.firstName} ${user.lastName}` |

6. **Group Attribute Statements** (Optional, for role mapping):
   | Name | Name (Format) | Value | Filter |
   |------|---------------|-------|--------|
   | `groups` | `Unspecified` | `user.groups` | `Matches regex: .*` |

7. **Advanced Settings**:
   - **Assertion Encryption**: Uncheck (unless you have SP certificate)
   - **Signature Algorithm**: `RSA-SHA256`
   - **Digest Algorithm**: `SHA256`
   - **Assertion Signed**: ✅
   - **Response Signed**: ✅

8. Click **Next**, review settings, and click **Finish**

#### Step 3: Gather Okta Configuration

On the application's **Sign On** tab:

1. Scroll to **SAML Signing Certificates**
2. Click the certificate link (usually **SHA-256**)
3. Copy the **X.509 Certificate** (PEM format)
   - Click **View** → Copy the certificate
4. Copy **Identity Provider Single Sign-On URL** from the table
5. Note the **Identity Provider Issuer** (Entity ID)

#### Step 4: Configure in Telegram Streamer

1. Navigate to **Admin** → **Security** → **SSO Configuration**
2. Click **Add New SAML Configuration**
3. Fill in the form:
   - **Name**: "Okta SSO"
   - **IdP Entity ID**: (from Step 3)
   - **IdP SSO URL**: (from Step 3)
   - **IdP X.509 Certificate**: (paste certificate from Step 3)
   - **SP Entity ID**: Your application URL
   - **SP ACS URL**: `https://streamer.example.com/api/auth/saml/acs`
   - **Name ID Format**: `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`
   - **Attribute Mapping**:
     ```json
     {
       "email": "email",
       "full_name": "displayName"
     }
     ```
   - **Role Mapping** (if using groups):
     ```json
     {
       "TelegramStreamer-Admins": "admin",
       "TelegramStreamer-Users": "user"
     }
     ```
4. Click **Save**

#### Step 5: Assign Users

In Okta:

1. Navigate to **Applications** → **Applications** → **Telegram Streamer**
2. Click the **Assignments** tab
3. Click **Assign** → **Assign to People**
4. Search for users and assign them to the application
5. For group-based access, click **Assign** → **Assign to Groups**

---

### 2. Azure Active Directory (Azure AD / Microsoft Entra ID)

#### Step 1: Register Application in Azure AD

1. Log in to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory)
3. Click **Enterprise applications** → **New application**
4. Click **Create your own application**
5. **Name**: "Telegram Streamer"
6. **Integrate any other application you don't find in the gallery?**: Select
7. Click **Create**

#### Step 2: Configure SAML SSO

1. In the newly created application, click **Get started**
2. Click **3. Set up single sign-on**
3. Select **SAML** as the SSO method

On the **Basic SAML Configuration** page:

1. **Identifier (Entity ID)**:
   ```
   https://streamer.example.com
   ```

2. **Reply URL (Assertion Consumer Service URL)**:
   ```
   https://streamer.example.com/api/auth/saml/acs
   ```

3. **Sign on URL**:
   ```
   https://streamer.example.com
   ```

4. **Relay State**: Leave empty
5. Click **Save**

#### Step 3: Configure Attributes & Claims

Click **Edit** in the **Attributes & Claims** section:

1. **Unique User Identifier (Name ID)**:
   - Select `user.userprincipalname` or `user.mail`
   - Name ID format: `emailAddress`

2. **Add new claim** for user attributes:
   | Name | Source | Source attribute |
   |------|--------|------------------|
   | `email` | Attribute | `user.mail` |
   | `firstName` | Attribute | `user.givenname` |
   | `lastName` | Attribute | `user.surname` |
   | `displayName` | Attribute | `user.displayname` |

3. **Add groups claim** (for role mapping):
   - Click **Add new claim**
   - **Name**: `groups`
   - **Source**: `Groups`
   - ** Emit groups as role claim**: Uncheck
   - ** Emit groups as a claim**: Select

#### Step 4: Download Certificate & Get URLs

1. In the **SAML Signing Certificate** section:
   - Click **Download** next to **Certificate (Base64)**
   - Open the downloaded file and copy the certificate content
   - Note the **App Federation Metadata Url** - you'll need this

2. Note these values from the **Set up Telegram Streamer** section:
   - **Login URL**: Azure AD SSO URL
   - **Azure AD Identifier**: Azure AD Entity ID

#### Step 5: Configure in Telegram Streamer

1. Navigate to **Admin** → **Security** → **SSO Configuration**
2. Click **Add New SAML Configuration**
3. Fill in the form:
   - **Name**: "Azure AD SSO"
   - **IdP Entity ID**: (Azure AD Identifier from Step 4)
   - **IdP SSO URL**: (Login URL from Step 4)
   - **IdP X.509 Certificate**: (paste certificate from Step 4)
   - **IdP Metadata URL**: (App Federation Metadata Url)
   - **SP Entity ID**: Your application URL
   - **SP ACS URL**: `https://streamer.example.com/api/auth/saml/acs`
   - **Name ID Format**: `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`
   - **Attribute Mapping**:
     ```json
     {
       "email": "email",
       "full_name": "displayName"
     }
     ```
   - **Role Mapping** (if using groups):
     ```json
     {
       "TelegramStreamer-Admins": "admin",
       "TelegramStreamer-Users": "user"
     }
     ```
4. Click **Save**

#### Step 6: Assign Users

In Azure Portal:

1. Navigate to your application
2. Click **Users and groups**
3. Click **Add user/group**
4. Select users or groups to assign
5. Click **Assign**

---

### 3. Google Workspace (Google Cloud Identity)

#### Step 1: Add SAML App in Google Admin Console

1. Log in to [Google Admin Console](https://admin.google.com)
2. Navigate to **Apps** → **Web and mobile apps**
3. Click **Add app** → **Add custom SAML app**
4. **App name**: "Telegram Streamer"
5. **App description**: "Audio streaming platform"
6. Upload app icon (optional)
7. Click **Continue**

#### Step 2: Configure Google Identity Provider Details

Copy these values for later use:

- **SSO URL**: `https://accounts.google.com/o/saml2/idp?idpid=YOUR_IDP_ID`
- **Entity ID**: `https://accounts.google.com/o/saml2?idpid=YOUR_IDP_ID`
- **Certificate**: Download the X.509 certificate

Click **Continue**

#### Step 3: Configure Service Provider Details

Fill in your application details:

1. **ACS URL**:
   ```
   https://streamer.example.com/api/auth/saml/acs
   ```

2. **Entity ID**:
   ```
   https://streamer.example.com
   ```

3. **Start URL**:
   ```
   https://streamer.example.com
   ```

4. **Signed Response**: Select
5. **Name ID**: Select **Basic Information** → **Primary Email**
6. **Name ID Format**: Select `EMAIL`
7. Click **Continue**

#### Step 4: Configure Attribute Mapping

Click **Add Mapping** for each attribute:

| Application Attribute | Category | Google Directory Attribute |
|-----------------------|----------|---------------------------|
| `email` | Basic Information | Primary Email |
| `firstName` | Basic Information | First Name |
| `lastName` | Basic Information | Last Name |
| `displayName` | Basic Information | (Custom) Use: `${firstName} ${lastName}` |

For role mapping:

| Application Attribute | Category | Google Directory Attribute |
|-----------------------|----------|---------------------------|
| `groups` | Groups | (Select relevant groups) |

Click **Finish**

#### Step 5: Configure in Telegram Streamer

1. Navigate to **Admin** → **Security** → **SSO Configuration**
2. Click **Add New SAML Configuration**
3. Fill in the form:
   - **Name**: "Google Workspace SSO"
   - **IdP Entity ID**: (from Step 2)
   - **IdP SSO URL**: (from Step 2)
   - **IdP X.509 Certificate**: (paste certificate from Step 2)
   - **SP Entity ID**: Your application URL
   - **SP ACS URL**: `https://streamer.example.com/api/auth/saml/acs`
   - **Name ID Format**: `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`
   - **Attribute Mapping**:
     ```json
     {
       "email": "email",
       "full_name": "displayName"
     }
     ```
   - **Role Mapping** (if using groups):
     ```json
     {
       "TelegramStreamer-Admins": "admin",
       "TelegramStreamer-Users": "user"
     }
     ```
4. Click **Save**

#### Step 6: Enable Service for Users

In Google Admin Console:

1. Navigate to the app
2. Click **User access**
3. Select **ON** for everyone or specific organizational units
4. Click **Save**

---

### 4. OneLogin

#### Step 1: Create App in OneLogin

1. Log in to OneLogin Admin Portal
2. Navigate to **Applications** → **Applications**
3. Click **Add App**
4. Search for "SAML Test Connector" or create a custom SAML app
5. **Display Name**: "Telegram Streamer"
6. Click **Save**

#### Step 2: Configure SSO in OneLogin

On the **Configuration** tab:

1. **Relay State**: Leave empty
2. **ACS URL**:
   ```
   https://streamer.example.com/api/auth/saml/acs
   ```

3. **ACS URL Validator**: (Optional) Add your domain

On the **Parameters** tab, add user attributes:

| Parameter | Value |
|-----------|-------|
| `email` | `Email` |
| `firstName` | `First Name` |
| `lastName` | `Last Name` |
| `displayName` | `First Name` + `Last Name` |

On the **SSO** tab:

1. Note the **SAML 2.0 Endpoint (HTTP)** - this is your IdP SSO URL
2. Note the **SAML 2.0 Issuer** - this is your IdP Entity ID
3. Click **X.509 Certificate** → **View** and copy the certificate

#### Step 3: Configure in Telegram Streamer

1. Navigate to **Admin** → **Security** → **SSO Configuration**
2. Click **Add New SAML Configuration**
3. Fill in the form with values from OneLogin
4. Click **Save**

---

## Application Configuration

### Enable SAML in Environment Variables

Ensure SAML is enabled in your backend configuration:

```bash
# backend/.env or environment variables
SAML_ENABLED=true
SAML_IDP_ENTITY_ID=https://your-idp.com/entity-id
SAML_IDP_SSO_URL=https://your-idp.com/sso
SAML_IDP_X509_CERT="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
SAML_SP_ENTITY_ID=https://streamer.example.com
SAML_SP_ACS_URL=https://streamer.example.com/api/auth/saml/acs
SAML_SECURITY_SIGNED_ASSERTIONS=true
SAML_SECURITY_ENCRYPTED_ASSERTIONS=false
```

**Note**: These values can be overridden by database configurations, allowing for multiple IdPs.

### Install Required Dependencies

```bash
cd backend
pip install python3-saml>=1.15.0
```

Or update `requirements.txt`:
```
python3-saml>=1.15.0
```

### Verify SAML Metadata Endpoint

The application publishes SAML metadata at:

```
https://streamer.example.com/api/auth/saml/metadata
```

You can provide this URL to your IdP for automatic configuration.

**Example Metadata Response**:
```xml
<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="https://streamer.example.com">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocols:protocol">
    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat>
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                 Location="https://streamer.example.com/api/auth/saml/acs"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>
```

---

## Testing and Verification

### 1. Verify Configuration

Before testing SSO login, verify your configuration:

1. Navigate to **Admin** → **Security** → **SSO Configuration**
2. Click on your SAML configuration
3. Verify all fields are correct
4. Check **Enabled** is checked
5. Click **Save** if any changes were made

### 2. Test SAML Login

#### Method 1: From Login Page

1. Navigate to `https://streamer.example.com/auth`
2. Click the **SSO Login** button (shield icon)
3. You should be redirected to your IdP login page
4. Enter your credentials
5. Upon successful authentication, you should be redirected back to the application
6. Verify you are logged in with the correct email and role

#### Method 2: Direct URL

You can test SSO login using a direct URL:

```
https://streamer.example.com/api/auth/saml/login?idp_id=YOUR_CONFIG_ID
```

Replace `YOUR_CONFIG_ID` with the ID of your SAML configuration (visible in the URL when editing the configuration in the admin panel).

### 3. Verify User Provisioning

After first login:

1. Navigate to **Admin** → **Users**
2. Search for the user by email
3. Verify the user was created with:
   - Correct email address
   - Correct name (from attribute mapping)
   - Correct role (from role mapping or default `user`)
   - `saml_name_id` field populated
   - `saml_config_id` field populated

### 4. Check Audit Logs

1. Navigate to **Admin** → **Audit Logs**
2. Filter by `saml_login` event type
3. Verify successful SAML login events are logged with:
   - User email
   - SAML configuration used
   - IP address
   - Timestamp

### 5. Test Multiple IdPs

If you have multiple SAML configurations:

1. Ensure each has a unique name and configuration
2. Test logging in with each IdP
3. Verify users are mapped to the correct SAML configuration

---

## Advanced Configuration

### Attribute Mapping

Attribute mapping controls how user data is extracted from SAML assertions and populated in the user model.

#### Simple Attribute Mapping

Map a SAML attribute directly to a user field:

```json
{
  "email": "user.email",
  "full_name": "user.displayName"
}
```

#### Expression-Based Mapping

Use expressions to combine multiple attributes:

```json
{
  "full_name": "firstName + ' ' + lastName",
  "email": "emailAddress.toLowerCase()"
}
```

**Supported expressions:**
- String concatenation: `firstName + ' ' + lastName`
- Method calls: `.toLowerCase()`, `.toUpperCase()`, `.trim()`
- Conditional logic: `displayName || firstName + ' ' + lastName`

#### Default Values

Provide default values if attributes are missing:

```json
{
  "full_name": "displayName || 'Unknown User'",
  "email": "email || 'unknown@example.com'"
}
```

### Role Mapping

Role mapping controls how IdP groups are mapped to application roles.

#### Basic Role Mapping

```json
{
  "TelegramStreamer-Admins": "admin",
  "TelegramStreamer-Users": "user"
}
```

#### Multiple Groups to Single Role

```json
{
  "TelegramStreamer-Admins": "admin",
  "TelegramStreamer-SuperAdmins": "admin",
  "TelegramStreamer-Users": "user"
}
```

#### Default Role

If no group mapping matches, users are assigned the `user` role by default.

**Supported Application Roles:**
- `user` - Basic user access
- `admin` - Administrative access
- `superadmin` - Full system access

### Security Configuration

You can customize SAML security settings in the `security_config` field:

```json
{
  "nameIdEncrypted": false,
  "authnRequestsSigned": true,
  "logoutRequestSigned": true,
  "logoutResponseSigned": true,
  "signMetadata": false,
  "wantMessagesSigned": true,
  "wantAssertionsSigned": true,
  "wantAssertionsEncrypted": false,
  "wantNameIdEncrypted": false,
  "requestedAuthnContext": true,
  "requestedAuthnContextComparison": "exact",
  "requestedAuthnContextClassRef": "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
  "allowRepeatAttributeName": false,
  "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
  "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
}
```

**Recommended Security Settings:**
- ✅ `authnRequestsSigned: true` - Sign authentication requests
- ✅ `wantAssertionsSigned: true` - Require signed assertions
- ✅ `wantMessagesSigned: true` - Require signed messages
- ❌ `wantAssertionsEncrypted: false` - Only enable if you have SP certificate
- ✅ `signatureAlgorithm: "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"` - Use SHA-256

### Name ID Format

Select the appropriate Name ID format for your IdP:

| Format | Use Case |
|--------|----------|
| `urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified` | Default (recommended) |
| `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress` | Email as identifier |
| `urn:oasis:names:tc:SAML:1.1:nameid-format:transient` | Temporary/per-session identifier |
| `urn:oasis:names:tc:SAML:2.0:nameid-format:persistent` | Persistent identifier across sessions |

### Single Logout (SLO)

Single Logout allows users to log out from both the application and IdP simultaneously.

#### Enable SLO

1. Configure **IdP SLO URL** in your SAML configuration
2. Configure **SP SLO URL**: `https://streamer.example.com/api/auth/saml/slo`
3. Ensure your IdP supports SLO

#### Test SLO

1. Log in via SAML
2. Click **Logout** in the application
3. Verify you are logged out from both the application and IdP
4. Verify IdP session is terminated

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "SAML library is not available"

**Error**: `HTTPException: SAML library is not available. Install python3-saml package.`

**Solution**:
```bash
cd backend
pip install python3-saml>=1.15.0
```

#### 2. "Invalid SAML Response"

**Possible Causes**:
- Incorrect X.509 certificate
- Clock skew between servers
- Invalid ACS URL
- Missing or incorrect signature

**Solutions**:
1. Verify the X.509 certificate is copied correctly (include `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`)
2. Check server time synchronization: `timedatectl status` (Linux) or `w32tm /query /status` (Windows)
3. Verify ACS URL matches exactly what's configured in IdP
4. Check SAML security settings (`wantAssertionsSigned`, `wantMessagesSigned`)

#### 3. "User not found" after successful SAML login

**Possible Causes**:
- Attribute mapping incorrect
- Email not included in SAML assertion
- Email format mismatch

**Solutions**:
1. Check attribute mapping configuration
2. Enable SAML debug logging to see assertion contents
3. Verify IdP is sending the expected attributes
4. Check Name ID format matches IdP configuration

#### 4. Users assigned wrong role

**Possible Causes**:
- Role mapping configuration incorrect
- Group names don't match
- User not in expected groups

**Solutions**:
1. Verify role mapping JSON format
2. Check group names in IdP match exactly (case-sensitive)
3. Verify user is member of expected groups in IdP
4. Check audit logs for role assignment details

#### 5. "Certificate expired" error

**Solution**:
1. Download new certificate from IdP
2. Update SAML configuration in admin panel
3. Save configuration

#### 6. Loop during login (redirects back and forth)

**Possible Causes**:
- Incorrect Entity ID
- IdP not trusting SP
- Missing audience configuration

**Solutions**:
1. Verify SP Entity ID matches exactly in both app and IdP
2. Add application as trusted in IdP
3. Check audience restriction in IdP settings
4. Verify ACS URL is correct in IdP

### Debug Logging

Enable detailed SAML logging for troubleshooting:

```bash
# backend/.env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

Debug logs will include:
- SAML request/response content
- Attribute extraction details
- Role mapping decisions
- Error details

### Test SAML Response

You can decode and verify SAML responses using online tools:

1. **SAML Decoder**: https://www.samltool.com/decode.php
2. **SAML Validator**: https://www.samltool.com/validate.php

**Steps**:
1. Enable browser developer tools (F12)
2. Attempt SAML login
3. Check Network tab for SAML response
4. Copy the `SAMLResponse` form field
5. Decode using SAML decoder tool
6. Verify attributes and signature

### Verify IdP Configuration

Most IdPs provide a test page:

- **Okta**: Application → **Sign On** → **View SAML Setup Instructions**
- **Azure AD**: Application → **Test single sign-on with this application**
- **Google Workspace**: Application → **Testing status**

Use these tools to verify your IdP is configured correctly before testing with the application.

---

## Security Best Practices

### 1. Certificate Management

- **Monitor Certificate Expiry**: Set up alerts for certificate expiration
- **Rotate Certificates**: Update certificates when IdP rotates them
- **Secure Storage**: Store certificates securely in the database (encrypted at rest)

### 2. Enable Required Security Features

```json
{
  "authnRequestsSigned": true,
  "wantAssertionsSigned": true,
  "wantMessagesSigned": true,
  "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
}
```

### 3. Use HTTPS Only

- SAML requires HTTPS for production use
- Ensure valid SSL/TLS certificates
- Configure HSTS headers

### 4. Implement Proper Logout

- Enable Single Logout (SLO) for both SP and IdP
- Clear application sessions on logout
- Clear IdP sessions on logout

### 5. Attribute and Role Validation

- Validate attribute mappings before enabling
- Test role mapping with test groups
- Use least privilege principle for role assignments

### 6. Audit and Monitoring

- Review SAML login audit logs regularly
- Monitor for failed login attempts
- Set up alerts for security events
- Track certificate expiration dates

### 7. Disaster Recovery

- Document SAML configuration steps
- Store certificates securely (e.g., password manager)
- Have backup authentication method (e.g., email/password)
- Test failover scenarios

### 8. Compliance

SOC 2 and GDPR considerations:

- **Audit Logging**: All SAML logins are logged with user attribution
- **Data Protection**: SAML assertions contain PII, ensure HTTPS encryption
- **Right to Access**: Users can export their data including SAML identifiers
- **Right to Erasure**: Users can delete their accounts (SAML associations removed)

---

## API Reference

### SAML Configuration API

#### List Configurations
```http
GET /api/admin/saml/configs
Authorization: Bearer <admin-token>
```

#### Get Configuration
```http
GET /api/admin/saml/configs/{config_id}
Authorization: Bearer <admin-token>
```

#### Create Configuration
```http
POST /api/admin/saml/configs
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "name": "Okta SSO",
  "enabled": true,
  "idp_entity_id": "https://okta.com/saml-id",
  "idp_sso_url": "https://okta.com/sso",
  "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
  "sp_entity_id": "https://streamer.example.com",
  "sp_acs_url": "https://streamer.example.com/api/auth/saml/acs",
  "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
  "attribute_mapping": {
    "email": "email",
    "full_name": "displayName"
  },
  "role_mapping": {
    "Admins": "admin"
  }
}
```

#### Update Configuration
```http
PUT /api/admin/saml/configs/{config_id}
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "enabled": false
}
```

#### Delete Configuration
```http
DELETE /api/admin/saml/configs/{config_id}
Authorization: Bearer <admin-token>
```

#### Enable/Disable Configuration
```http
POST /api/admin/saml/configs/{config_id}/enable
Authorization: Bearer <admin-token>

POST /api/admin/saml/configs/{config_id}/disable
Authorization: Bearer <admin-token>
```

### SAML Authentication Endpoints

#### Initiate Login
```http
GET /api/auth/saml/login?idp_id=<config_id>
```

#### Assertion Consumer Service (ACS)
```http
POST /api/auth/saml/acs
Content-Type: application/x-www-form-urlencoded

SAMLResponse=<encoded-saml-response>&RelayState=<relay-state>
```

#### Initiate Logout
```http
GET /api/auth/saml/logout
```

#### Service Provider Metadata
```http
GET /api/auth/saml/metadata
```

---

## Glossary

| Term | Definition |
|------|------------|
| **SAML** | Security Assertion Markup Language - XML-based standard for authentication |
| **SSO** | Single Sign-On - Authentication process allowing one login for multiple applications |
| **IdP** | Identity Provider - Service that authenticates users (e.g., Okta, Azure AD) |
| **SP** | Service Provider - Application requesting authentication (your application) |
| **ACS** | Assertion Consumer Service - Endpoint that receives SAML responses |
| **SLO** | Single Logout - Process that logs user out from both SP and IdP |
| **Entity ID** | Unique identifier for SAML participant (SP or IdP) |
| **Name ID** | User identifier in SAML assertion (typically email) |
| **X.509 Certificate** | Digital certificate used for verifying SAML signatures |
| **Metadata** | XML document describing SAML configuration |
| **Assertion** | SAML statement containing authentication and user data |

---

## Support and Resources

### Internal Resources

- **Admin Panel**: `/admin/security/sso` - SSO configuration UI
- **Security Dashboard**: `/admin/security` - Compliance and security overview
- **Audit Logs**: `/admin/audit` - SAML login activity logs

### External Resources

- **Okta Documentation**: https://help.okta.com
- **Azure AD Documentation**: https://docs.microsoft.com/azure/active-directory/
- **Google Workspace Documentation**: https://support.google.com/a/
- **SAML Specification**: https://www.oasis-open.org/committees/security/
- **SAML Testing Tools**: https://www.samltool.com/

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Enable debug logging and review logs
3. Verify IdP configuration using IdP test tools
4. Contact your IdP support for IdP-specific issues
5. Review SAML response using online decoder tools

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-23 | Initial release with support for Okta, Azure AD, Google Workspace, and OneLogin |

---

**Document ID:** SSO_SETUP_GUIDE
**Status:** Active
**Classification:** Public Documentation
