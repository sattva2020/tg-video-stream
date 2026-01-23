# End-to-End Authentication Flow Test Plan

## Overview
This document outlines the end-to-end testing plan for the authentication flow in the mobile app, including login, biometric authentication, and logout functionality.

## Test Environment

### Prerequisites
- iOS device (iPhone/iPad) running iOS 13.0 or later
- OR Android device running Android 5.0 (API 21) or later
- Backend server running and accessible
- Test user account with email/password
- Biometric authentication enabled on device (Face ID, Touch ID, or fingerprint)

### Test Accounts
Create the following test accounts:
1. **Standard User**: email+standard@test.com / Test1234!
2. **User with 2FA**: email+2fa@test.com / Test1234! (TOTP enabled)
3. **Pending Approval User**: email+pending@test.com / Test1234! (account not approved)

## Test Cases

### TC-AUTH-001: Initial App Launch and Login Screen Display

**Steps:**
1. Launch the mobile app on device
2. Observe the initial screen

**Expected Results:**
- Loading screen appears briefly (SplashLoadingScreen)
- Login screen is displayed
- Login form contains:
  - Email input field
  - Password input field with show/hide toggle
  - 2FA code input field (optional)
  - "Sign in" button
  - "Forgot your password?" link
  - "Create a new account" link
  - Google OAuth button (placeholder)
  - Telegram OAuth button (placeholder)

**Status:** [ ] Pass [ ] Fail

**Notes:**
- All text is properly translated to device language
- Touch targets are at least 44x44px
- Input fields have proper autocomplete attributes
- Keyboard doesn't cover form fields

---

### TC-AUTH-002: Login with Valid Credentials (No Biometric)

**Steps:**
1. On login screen, enter test email: `email+standard@test.com`
2. Enter test password: `Test1234!`
3. Tap "Sign in" button
4. Wait for authentication to complete

**Expected Results:**
- Loading indicator appears on button
- Authentication request is sent to backend
- If biometric is not available/enrolled:
  - User is navigated to Dashboard screen
  - Bottom tab navigation is visible
  - User profile is loaded
- If biometric is available/enrolled:
  - BiometricPrompt screen is displayed
  - User sees option to enable biometric

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-003: Login with Valid Credentials (Biometric Available)

**Preconditions:**
- Device supports biometric authentication (Face ID/Touch ID/fingerprint)
- Biometric is enrolled in device settings
- User has not enabled biometric in app before

**Steps:**
1. On login screen, enter test email: `email+standard@test.com`
2. Enter test password: `Test1234!`
3. Tap "Sign in" button
4. Wait for biometric prompt screen

**Expected Results:**
- Login succeeds
- BiometricPrompt screen is displayed
- Screen shows:
  - Biometric icon (👤 for Face ID, 👆 for fingerprint)
  - Title: "Enable Face ID?" or "Enable fingerprint?"
  - Description of benefits
  - "Enable Face ID" / "Enable fingerprint" button
  - "Not now" button
  - Privacy note about data security

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-004: Enable Biometric Authentication

**Preconditions:**
- BiometricPrompt screen is displayed (from TC-AUTH-003)

**Steps:**
1. Read the benefits and privacy note
2. Tap "Enable Face ID" / "Enable fingerprint" button
3. Authenticate with biometric when prompted
4. Wait for authentication to complete

**Expected Results:**
- Biometric prompt appears (Face ID / Touch ID / fingerprint)
- User successfully authenticates
- Biometric preference is saved in secure storage
- User is navigated to Dashboard screen
- Bottom tab navigation is visible
- User profile is loaded

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-005: Skip Biometric Authentication

**Preconditions:**
- BiometricPrompt screen is displayed (from TC-AUTH-003)

**Steps:**
1. Tap "Not now" button

**Expected Results:**
- User is navigated to Dashboard screen
- Bottom tab navigation is visible
- User profile is loaded
- Biometric is NOT enabled for future logins

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-006: Biometric Re-authentication on App Launch

**Preconditions:**
- User has successfully logged in and enabled biometric (TC-AUTH-004)
- User has closed and relaunched the app
- Valid auth token exists in secure storage

**Steps:**
1. Close the app completely (swipe away from recents)
2. Relaunch the app
3. Wait for initialization

**Expected Results:**
- App detects valid token in storage
- App detects biometric is enabled
- Biometric prompt appears automatically
- User authenticates with Face ID / Touch ID / fingerprint
- Dashboard screen is displayed
- User remains logged in (no password required)

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-007: Biometric Authentication Failure

**Preconditions:**
- User has enabled biometric authentication
- App is launching and requesting biometric

**Steps:**
1. When biometric prompt appears, tap "Cancel" or fail authentication
2. Observe app behavior

**Expected Results:**
- If user cancels or fails biometric:
  - User is logged out
  - Token is removed from secure storage
  - Login screen is displayed
- No error message is shown (silent logout)

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-008: Login with Invalid Email

**Steps:**
1. On login screen, enter invalid email: `invalid-email`
2. Enter any password
3. Tap "Sign in" button

**Expected Results:**
- Form validation fails before API call
- Error message appears: "Please enter a valid email address"
- No API request is made
- User stays on login screen

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-009: Login with Invalid Credentials

**Steps:**
1. On login screen, enter valid email format: `wrong@test.com`
2. Enter invalid password: `WrongPassword123!`
3. Tap "Sign in" button

**Expected Results:**
- Loading indicator appears
- API request is sent to backend
- Error message appears: "Invalid email or password."
- User stays on login screen
- Input fields are still populated for retry

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-010: Login with 2FA Enabled

**Preconditions:**
- Test user has 2FA (TOTP) enabled
- User has authenticator app (Google Authenticator, 1Password, etc.)

**Steps:**
1. On login screen, enter email: `email+2fa@test.com`
2. Enter password: `Test1234!`
3. Leave 2FA code empty
4. Tap "Sign in" button
5. When error appears, enter valid 6-digit TOTP code
6. Tap "Sign in" button again

**Expected Results:**
- First attempt (without 2FA):
  - Error message: "Введите одноразовый код 2FA из приложения."
  - 2FA field is highlighted
- Second attempt (with valid 2FA):
  - Authentication succeeds
  - BiometricPrompt appears (if available)
  - User can proceed to Dashboard

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-011: Login with Pending Approval Account

**Preconditions:**
- Test account exists but is not approved by admin

**Steps:**
1. On login screen, enter email: `email+pending@test.com`
2. Enter password: `Test1234!`
3. Tap "Sign in" button

**Expected Results:**
- Authentication succeeds at password level
- API returns 403 with pending status
- User is navigated to PendingApproval screen (or stays on Login with message)
- Error message indicates account is pending approval

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-012: View Dashboard After Authentication

**Preconditions:**
- User has successfully authenticated (with or without biometric)

**Steps:**
1. Observe the Dashboard screen

**Expected Results:**
- Dashboard screen is displayed
- Stream status card shows:
  - Online/offline status
  - Current track info (if streaming)
  - Listener count
  - Queue statistics
- Quick action buttons are visible (Start/Stop/Restart)
- Bottom tab navigation is visible with 5 tabs:
  - Dashboard
  - Channels
  - Schedule
  - Notifications
  - Settings
- User's name/email is visible in settings

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-013: Logout from Settings

**Preconditions:**
- User is logged in and viewing Dashboard

**Steps:**
1. Tap "Settings" tab in bottom navigation
2. Scroll to bottom of settings screen
3. Tap "Logout" button
4. Confirm logout if prompted

**Expected Results:**
- Confirmation dialog appears: "Are you sure you want to logout?"
- After confirmation:
  - Auth token is removed from secure storage
  - User state is cleared
  - Biometric preference is cleared
  - User is navigated to Login screen
  - Login form is empty (no pre-filled data)

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-014: Verify Auth State Cleared After Logout

**Preconditions:**
- User has just logged out (TC-AUTH-013)

**Steps:**
1. Close the app completely
2. Relaunch the app
3. Wait for initialization

**Expected Results:**
- Login screen is displayed
- No biometric prompt appears
- No automatic login occurs
- Secure storage is empty (no token, no biometric preference)

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-015: Token Expiration Handling

**Preconditions:**
- User is logged in with valid token
- Token is close to expiration or manually expired on backend

**Steps:**
1. Use the app normally (navigate between screens)
2. Attempt an action that requires API call
3. Wait for token to expire or use expired token

**Expected Results:**
- When API call fails with 401 (unauthorized):
  - Token is cleared from storage
  - User is logged out
  - Login screen is displayed
  - Error message may appear (optional)

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

### TC-AUTH-016: Network Error During Login

**Preconditions:**
- Device has no network connection (airplane mode or no service)

**Steps:**
1. Enable airplane mode
2. Open login screen
3. Enter valid credentials
4. Tap "Sign in" button

**Expected Results:**
- Loading indicator appears
- API request fails with network error
- Error message appears: "Login failed. Please try again later."
- User stays on login screen
- Input fields are preserved

**Status:** [ ] Pass [ ] Fail

**Actual Results:**

**Notes:**

---

## Test Execution Summary

### Device Information
- **Device Model:** _______________
- **OS Version:** _______________
- **App Version:** _______________
- **Test Date:** _______________
- **Tester:** _______________

### Results
- **Total Test Cases:** 16
- **Passed:** _____
- **Failed:** _____
- **Skipped:** _____

### Failed Test Cases
List any failed test cases with issue descriptions:

1. TC-AUTH-___: [Description]

2. TC-AUTH-___: [Description]

### Issues Found
List any bugs or issues discovered during testing:

1. [Issue description]

2. [Issue description]

### Recommendations
List any improvements or suggestions:

1. [Recommendation]

2. [Recommendation]

---

## Sign-off
**Tester Name:** _______________
**Test Execution Date:** _______________
**Results Approved:** [ ] Yes [ ] No
**Comments:**
