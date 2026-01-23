# E2E Testing Guide for Authentication Flow

## Overview
This guide explains how to perform end-to-end testing of the authentication flow in the mobile app, including login, biometric authentication, and logout functionality.

## Prerequisites

### Required Tools
- **iOS Device:** iPhone or iPad running iOS 13.0+
  **OR**
- **Android Device:** Android phone or tablet running Android 5.0+ (API 21+)
- **Backend Server:** Running and accessible from device
- **Test Accounts:** Pre-created test user accounts (see Test Accounts section)

### Network Setup
1. Ensure mobile device and backend server are on the same network
2. Or configure backend with public URL/VPN access
3. Update API base URL in mobile app if needed (`.env` file)

### Test Accounts Setup
Create these test accounts in your backend:

| Account Type | Email | Password | Notes |
|--------------|-------|----------|-------|
| Standard User | `email+standard@test.com` | `Test1234!` | No 2FA, approved |
| 2FA User | `email+2fa@test.com` | `Test1234!` | TOTP enabled, approved |
| Pending User | `email+pending@test.com` | `Test1234!` | Not approved by admin |

## Quick Start

### 1. Install the App

**Development Build (via Expo):**
```bash
cd mobile
npm install
npx expo start --tunnel
```
Then scan the QR code with Expo Go app on your device.

**Production Build (via EAS):**
```bash
cd mobile
npm install
npx eas build --platform ios --profile development
# or
npx eas build --platform android --profile development
```
Install the built app on your device.

### 2. Configure API Endpoint

If your backend is not at `http://localhost:8000/api`, update the API URL:

**iOS:**
1. Open app in development build
2. Shake device or use keyboard shortcut to open Developer Menu
3. Tap "Configure API Endpoint"
4. Enter your backend URL

**Android:**
1. Open app in development build
2. Shake device or use keyboard shortcut to open Developer Menu
3. Tap "Configure API Endpoint"
4. Enter your backend URL

**Or update `.env` file:**
```bash
API_BASE_URL=https://your-backend-url.com/api
```

### 3. Enable Biometric on Device

**iOS:**
1. Open Settings > Face ID & Passcode (or Touch ID & Passcode)
2. Enable Face ID / Touch ID
3. Enroll at least one fingerprint or face

**Android:**
1. Open Settings > Security
2. Tap "Fingerprint" or "Face Unlock"
3. Enroll your biometric data

## Running the Tests

### Manual Testing

#### Option 1: Follow the Test Plan

1. Open `mobile/docs/e2e-authentication-test-plan.md`
2. For each test case (TC-AUTH-001 through TC-AUTH-016):
   - Read the test steps
   - Perform the actions on your device
   - Record the result (Pass/Fail)
   - Add notes for any issues found

3. Complete the "Test Execution Summary" at the end

#### Option 2: Use the Test Reporter (Recommended)

The app includes test helper utilities to record your test results:

1. Open React Native Debugger or use Chrome DevTools:
   ```bash
   npm run react-devtools
   ```

2. In the app console, access the test reporter:
   ```javascript
   // Create a test reporter
   const reporter = require('./src/utils/testHelpers').createTestReporter();

   // Run TC-AUTH-001: Login Screen Display
   reporter.record('TC-AUTH-001: Login Screen Display', true, 'Screen loads correctly');

   // Run TC-AUTH-002: Login with Valid Credentials
   reporter.record('TC-AUTH-002: Login with Valid Credentials', true, 'Login successful');

   // If a test fails:
   reporter.record('TC-AUTH-003: Biometric Prompt', false, 'Prompt did not appear - expected Face ID prompt');

   // Generate markdown report
   console.log(reporter.generateMarkdown());
   ```

3. Copy the generated markdown and paste it into your test report

### Automated Verification Checks

You can run automated checks to verify state during testing:

```javascript
// Import test helpers
const {
  verifyLoginScreen,
  verifyUserAuthenticated,
  verifyBiometricState,
  verifyTokenExists,
  verifyTokenNotExists,
} = require('./src/utils/testHelpers');

// Check if login screen is displayed (you need to pass current route name)
const result1 = verifyLoginScreen('Login');
console.log(result1.message); // "✓ Login screen is displayed"

// After login, verify user is authenticated
const result2 = await verifyUserAuthenticated(user);
console.log(result2.message); // "User is authenticated with all required fields"

// Check biometric state
const result3 = await verifyBiometricState(true);
console.log(result3.message); // "✓ Biometric enabled: true"

// Verify token exists
const result4 = await verifyTokenExists();
console.log(result4.message); // "✓ Auth token is not null"
```

### Running Complete Test Suite

To run the complete automated test suite:

```javascript
// Run the E2E test suite
const { runAuthFlowE2E } = require('./src/utils/testHelpers');

// This will run automated checks and print results
await runAuthFlowE2E();
```

**Note:** This only runs automated state checks. Manual interaction is still required for login, biometric, and logout actions.

## Test Case Checklist

Use this quick checklist to track your progress:

### Login Screen
- [ ] TC-AUTH-001: Initial App Launch and Login Screen Display

### Basic Login
- [ ] TC-AUTH-002: Login with Valid Credentials (No Biometric)
- [ ] TC-AUTH-003: Login with Valid Credentials (Biometric Available)
- [ ] TC-AUTH-008: Login with Invalid Email
- [ ] TC-AUTH-009: Login with Invalid Credentials
- [ ] TC-AUTH-016: Network Error During Login

### Biometric Authentication
- [ ] TC-AUTH-004: Enable Biometric Authentication
- [ ] TC-AUTH-005: Skip Biometric Authentication
- [ ] TC-AUTH-006: Biometric Re-authentication on App Launch
- [ ] TC-AUTH-007: Biometric Authentication Failure

### Advanced Authentication
- [ ] TC-AUTH-010: Login with 2FA Enabled
- [ ] TC-AUTH-011: Login with Pending Approval Account

### Post-Login Verification
- [ ] TC-AUTH-012: View Dashboard After Authentication

### Logout
- [ ] TC-AUTH-013: Logout from Settings
- [ ] TC-AUTH-014: Verify Auth State Cleared After Logout

### Token Management
- [ ] TC-AUTH-015: Token Expiration Handling

## Common Issues and Troubleshooting

### Issue: "Network request failed"

**Cause:** App cannot reach backend server

**Solutions:**
1. Check that backend is running
2. Verify device and server are on same network
3. Update API base URL in `.env` or Developer Menu
4. Check firewall settings

### Issue: "Biometric authentication failed"

**Cause:** Biometric not properly configured or enrolled

**Solutions:**
1. Verify biometric is enabled in device settings
2. Ensure at least one face/fingerprint is enrolled
3. Check that app has biometric permissions
4. Try disabling and re-enabling biometric in device settings

### Issue: "Login succeeds but dashboard doesn't load"

**Cause:** Navigation or state management issue

**Solutions:**
1. Check React Native debugger console for errors
2. Verify backend API is returning user data correctly
3. Check network tab for API response status
4. Try clearing app data and logging in again

### Issue: "Biometric prompt doesn't appear on app launch"

**Cause:** Biometric not enabled or token not stored

**Solutions:**
1. Verify biometric was enabled after initial login
2. Check that auth token exists in secure storage
3. Check that biometricEnabled flag is set to 'true'
4. Try logging out and logging in again

### Issue: "Can't enable biometric"

**Cause:** Device doesn't support biometric or not enrolled

**Solutions:**
1. Verify device has Face ID/Touch ID/fingerprint hardware
2. Ensure biometric is enrolled in device settings
3. Check that app has necessary permissions
4. Try on a different device with biometric support

## Debugging Tips

### Enable React Native Debugger

```bash
# Install React Native Debugger
npm install -g react-native-debugger

# Start debugger
react-native-debugger
```

### View Console Logs

```bash
# iOS
npx expo start --ios

# Android
npx expo start --android

# Then shake device and tap "Debug"
```

### Check Secure Storage

```javascript
// In app console
import * as SecureStore from 'expo-secure-store';

// Check all stored values
const token = await SecureStore.getItemAsync('authToken');
const biometricEnabled = await SecureStore.getItemAsync('biometricEnabled');
const biometricEmail = await SecureStore.getItemAsync('biometricEmail');

console.log({ token, biometricEnabled, biometricEmail });
```

### Clear All Data

```javascript
// Clear all authentication state
const { clearAuthState } = require('./src/utils/testHelpers');
await clearAuthState();

// Or manually
await SecureStore.deleteItemAsync('authToken');
await SecureStore.deleteItemAsync('biometricEnabled');
await SecureStore.deleteItemAsync('biometricEmail');
```

## Reporting Results

### After Testing

1. **Collect Results:**
   - Use the test reporter to generate a markdown report
   - Or manually record results in test plan document

2. **Document Issues:**
   - For each failed test, describe the issue
   - Include screenshots if possible
   - Note device model and OS version
   - Include console error logs

3. **Create Bug Reports:**
   - Title: [Platform] Test Case ID - Brief Description
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots/videos
   - Device information
   - App version

### Example Report

```markdown
# Test Execution Report

**Device:** iPhone 12 Pro
**OS Version:** iOS 16.0
**App Version:** 1.0.0
**Date:** 2026-01-23
**Tester:** John Doe

## Results

✅ Pass: TC-AUTH-001 - Login Screen Display
✅ Pass: TC-AUTH-002 - Login with Valid Credentials
❌ Fail: TC-AUTH-003 - Biometric Prompt
   **Notes:** Biometric prompt did not appear after login. Expected Face ID prompt.
✅ Pass: TC-AUTH-004 - Enable Biometric Authentication
✅ Pass: TC-AUTH-012 - Dashboard Display

## Issues Found

1. **TC-AUTH-003:** Biometric prompt doesn't appear automatically after login
   - **Steps:** Login with valid credentials
   - **Expected:** BiometricPrompt screen appears
   - **Actual:** User navigates directly to Dashboard
   - **Severity:** Medium
   - **Screenshot:** [attached]
```

## Best Practices

1. **Test on Real Devices:** Emulators may not have biometric support
2. **Test Both Platforms:** Run tests on both iOS and Android
3. **Test Network Conditions:** Try with slow/unstable network
4. **Test Edge Cases:** Invalid input, network errors, token expiration
5. **Document Everything:** Record all results, even passes
6. **Use Screenshots:** Capture evidence of issues
7. **Report Promptly:** Report issues as soon as you find them
8. **Verify Fixes:** Re-test after bugs are fixed

## Next Steps

After completing authentication flow testing:

1. Proceed to stream management testing (TC-STREAM-001 to TC-STREAM-010)
2. Test push notifications (TC-PUSH-001 to TC-PUSH-005)
3. Test offline mode (TC-OFFLINE-001 to TC-OFFLINE-005)
4. Test localization (TC-I18N-001 to TC-I18N-007)

See other test plan documents for details.

## Contact

For questions or issues with testing:
- **Developer Team:** dev-team@example.com
- **QA Lead:** qa-lead@example.com
- **Project Repository:** [GitHub link]

---

**Last Updated:** 2026-01-23
**Document Version:** 1.0.0
