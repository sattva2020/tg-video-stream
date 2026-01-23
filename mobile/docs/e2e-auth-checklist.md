# Authentication Flow E2E Test Checklist

**Tester:** ___________________
**Device:** ___________________
**OS Version:** ___________________
**Date:** ___________________

## Instructions
- ✓ = Pass
- ✗ = Fail
- ⊘ = Skipped
- Add notes for any failures

---

## Login Screen Tests

### ✓ TC-AUTH-001: Login Screen Display
[ ] Loading screen appears briefly
[ ] Login form with email/password fields
[ ] Show/hide password toggle
[ ] 2FA code field (optional)
[ ] Sign in button
[ ] Forgot password link
[ ] OAuth buttons (Google, Telegram)

**Notes:** ___________________



---

## Basic Login Tests

### ✓ TC-AUTH-002: Login Without Biometric
[ ] Enter email: `email+standard@test.com`
[ ] Enter password: `Test1234!`
[ ] Tap Sign in
[ ] Dashboard appears directly (biometric not available)

**Notes:** ___________________



### ✓ TC-AUTH-003: Login With Biometric Available
[ ] Enter email: `email+standard@test.com`
[ ] Enter password: `Test1234!`
[ ] Tap Sign in
[ ] BiometricPrompt screen appears
[ ] Shows biometric type (Face ID/fingerprint)
[ ] Shows benefits and privacy note
[ ] Enable and Not now buttons visible

**Notes:** ___________________



### ✓ TC-AUTH-008: Invalid Email
[ ] Enter invalid email: `invalid-email`
[ ] Enter any password
[ ] Tap Sign in
[ ] Validation error: "Please enter a valid email address"
[ ] No API call made

**Notes:** ___________________



### ✓ TC-AUTH-009: Invalid Credentials
[ ] Enter email: `wrong@test.com`
[ ] Enter password: `WrongPassword123!`
[ ] Tap Sign in
[ ] Error: "Invalid email or password."
[ ] Stay on login screen

**Notes:** ___________________



### ✓ TC-AUTH-016: Network Error
[ ] Enable airplane mode
[ ] Enter valid credentials
[ ] Tap Sign in
[ ] Error: "Login failed. Please try again later."
[ ] Input fields preserved

**Notes:** ___________________



---

## Biometric Tests

### ✓ TC-AUTH-004: Enable Biometric
[ ] From BiometricPrompt, tap "Enable Face ID" / "Enable fingerprint"
[ ] Authenticate with biometric
[ ] Success message
[ ] Navigated to Dashboard
[ ] Biometric saved for next login

**Notes:** ___________________



### ✓ TC-AUTH-005: Skip Biometric
[ ] From BiometricPrompt, tap "Not now"
[ ] Navigated to Dashboard
[ ] Biometric NOT enabled

**Notes:** ___________________



### ✓ TC-AUTH-006: Biometric Re-auth on App Launch
[ ] Close app completely
[ ] Relaunch app
[ ] Biometric prompt appears automatically
[ ] Authenticate successfully
[ ] Dashboard appears (no password required)

**Notes:** ___________________



### ✓ TC-AUTH-007: Biometric Failure
[ ] Close and relaunch app
[ ] When biometric prompt appears, tap Cancel
[ ] User logged out
[ ] Login screen displayed
[ ] Token cleared from storage

**Notes:** ___________________



---

## Advanced Authentication Tests

### ✓ TC-AUTH-010: Login with 2FA
[ ] Enter email: `email+2fa@test.com`
[ ] Enter password: `Test1234!`
[ ] Leave 2FA empty, tap Sign in
[ ] Error: "Введите одноразовый код 2FA"
[ ] Enter valid 6-digit TOTP code
[ ] Sign in again
[ ] Authentication succeeds

**Notes:** ___________________



### ✓ TC-AUTH-011: Pending Approval Account
[ ] Enter email: `email+pending@test.com`
[ ] Enter password: `Test1234!`
[ ] Tap Sign in
[ ] Error: Account pending approval
[ ] Or navigated to PendingApproval screen

**Notes:** ___________________



---

## Post-Login Tests

### ✓ TC-AUTH-012: Dashboard Display
[ ] After successful login
[ ] Dashboard screen displayed
[ ] Stream status card visible
[ ] Listener count visible
[ ] Quick action buttons visible
[ ] Bottom tab navigation visible (5 tabs)

**Notes:** ___________________



---

## Logout Tests

### ✓ TC-AUTH-013: Logout
[ ] Tap Settings tab
[ ] Scroll to bottom
[ ] Tap Logout button
[ ] Confirmation dialog appears
[ ] Confirm logout
[ ] Login screen displayed

**Notes:** ___________________



### ✓ TC-AUTH-014: Verify State Cleared
[ ] After logout, close app
[ ] Relaunch app
[ ] Login screen displayed (no auto-login)
[ ] No biometric prompt
[ ] No token in storage

**Notes:** ___________________



---

## Token Management Tests

### ✓ TC-AUTH-015: Token Expiration
[ ] Login successfully
[ ] Wait for token to expire (or use expired token)
[ ] Make API call
[ ] User logged out automatically
[ ] Login screen displayed

**Notes:** ___________________



---

## Test Summary

**Total Tests:** 16
**Passed:** _____
**Failed:** _____
**Skipped:** _____

### Failed Tests (List IDs):
- TC-AUTH-___: ___________________
- TC-AUTH-___: ___________________

### Critical Issues Found:
1. ___________________
2. ___________________

### Recommendations:
1. ___________________
2. ___________________

---

## Tester Sign-off

**Name:** ___________________
**Date:** ___________________
**Results Approved:** [ ] Yes [ ] No

**Comments:**
___________________
___________________
___________________

---

**Quick Tips:**
- Use test reporter utilities in console to verify state
- Take screenshots of failures
- Check console for error logs
- Test on both iOS and Android if possible
- Test with different network conditions

**Need Help?** See `e2e-testing-guide.md` for detailed instructions.
