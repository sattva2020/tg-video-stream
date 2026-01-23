# Push Notification E2E Test Plan

## Document Information

- **Test Plan ID:** TP-E2E-PUSH-001
- **Version:** 1.0
- **Last Updated:** 2026-01-23
- **Test Lead:** QA Team
- **Test Environment:** iOS (13+) and Android (21+) Physical Devices

## Overview

This document outlines the end-to-end test cases for push notification functionality in the mobile app. Tests cover permission handling, device registration, notification reception (foreground, background, and killed state), notification tap handling, navigation to relevant screens, and notification logging.

**Test Scope:**
- Push notification permission requests
- Device registration and push token management
- Stream failure notifications
- System notifications
- Notification reception in all app states (foreground, background, killed)
- Notification tap handling and deep linking
- Navigation to relevant screens
- Notification logging in app

**Test Prerequisites:**
1. Backend server running and accessible
2. Valid test account with operator or higher permissions
3. Physical iOS device (iOS 13+) or Android device (API 21+)
4. Expo development build or production build installed
5. Expo Push Notifications configured (APNs for iOS, FCM for Android)
6. Network connectivity (WiFi or cellular)
7. Backend API endpoint for sending test notifications

**Test Setup:**
1. Login to the mobile app with test account
2. Grant push notification permissions when prompted
3. Verify device is registered with backend (check backend logs or API)
4. Ensure app is in a known state (e.g., Dashboard screen)

---

## Test Cases

### TC-PUSH-001: Push Notification Permission Request

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 2 minutes

**Preconditions:**
- App is installed on device
- User is logged out
- Push notifications not yet granted

**Test Steps:**
1. Launch the app
2. Login with valid credentials
3. Observe the push notification permission prompt

**Expected Results:**
- On iOS: System permission dialog appears with "Allow Notifications" and "Don't Allow" options
- On Android: Permission prompt appears (on Android 13+)
- Dialog explains why notifications are needed (optional, app-provided message)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-002: Allow Push Notification Permissions

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 2 minutes

**Preconditions:**
- Push notification permission prompt is displayed (from TC-PUSH-001)

**Test Steps:**
1. Tap "Allow" on the permission prompt
2. Wait for app to proceed to dashboard
3. Check system settings to verify permission granted

**Expected Results:**
- Permission prompt closes
- App proceeds to dashboard
- System Settings show notifications allowed for the app
- Push token is registered with backend (check backend logs or API)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-003: Deny Push Notification Permissions

**Priority:** P1 (High)
**Test Type:** Functional
**Estimated Time:** 2 minutes

**Preconditions:**
- App is installed
- User is logged out

**Test Steps:**
1. Launch the app
2. Login with valid credentials
3. Tap "Don't Allow" on the permission prompt
4. Navigate to Settings screen
5. Look for notification settings or error message

**Expected Results:**
- App continues to function but without push notifications
- User is informed that notifications are disabled (optional, best practice)
- App can still be used normally
- No errors or crashes occur

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-004: Device Registration After Permission Grant

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notification permissions granted

**Test Steps:**
1. Grant push notification permissions
2. Wait 5-10 seconds for registration
3. Call backend API: `GET /api/mobile/devices`
4. Verify device appears in list
5. Verify device has valid push_token
6. Verify platform is correct (ios or android)

**Expected Results:**
- Device appears in backend device list
- Device has a valid Expo push token (ExponentPushToken[xxx])
- Platform matches device platform (ios or android)
- Device status is 'active'
- Device metadata includes app_version and os_version

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-005: Receive Notification in Foreground

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled and device registered
- App is open and visible on screen (foreground state)

**Test Steps:**
1. Open app and navigate to Dashboard screen
2. Keep app open and visible
3. From backend, send a test push notification:
   ```bash
   curl -X POST http://localhost:8000/api/mobile/devices/test-notification \
     -H "Authorization: Bearer <token>" \
     -d '{"message": "Test notification", "type": "alert", "data": {"screen": "notifications"}}'
   ```
4. Observe app behavior

**Expected Results:**
- Notification is received (may or may not show in notification center, depends on platform)
- App processes the notification in foreground
- No visual interruption to user experience
- Notification can be logged in app (check notification logs screen)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-006: Receive Notification in Background

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled and device registered

**Test Steps:**
1. Open app and navigate to Dashboard screen
2. Press home button to put app in background (app not visible, but not killed)
3. From backend, send a test push notification
4. Check device notification center
5. Verify notification appears

**Expected Results:**
- Notification appears in system notification center
- Notification title and body are correct
- Notification icon is visible
- Vibration/sound plays (if enabled in device settings)
- LED flash (Android, if enabled)
- Notification is timestamped correctly

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-007: Receive Notification When App is Killed

**Priority:** P0 (Critical)
**Test Type:** Functional
**Estimated Time:** 4 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled and device registered

**Test Steps:**
1. Open app
2. Force quit the app (swipe away from recents or force stop)
3. From backend, send a test push notification
4. Check device notification center
5. Verify notification appears
6. Tap the notification

**Expected Results:**
- Notification appears in system notification center (app was killed)
- Notification title and body are correct
- Tapping notification launches the app
- App opens to relevant screen (based on notification data)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-008: Tap Notification - Navigate to Channel Screen

**Priority:** P0 (Critical)
**Test Type:** Functional
**Navigation Flow:** Deep Linking
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- App is in background or killed

**Test Steps:**
1. From backend, send a notification with channel data:
   ```json
   {
     "title": "Stream Alert",
     "body": "Channel 1 has stopped unexpectedly",
     "type": "channel",
     "channelId": 1
   }
   ```
2. Wait for notification to appear
3. Tap the notification
4. Observe navigation behavior

**Expected Results:**
- App opens (or comes to foreground)
- App navigates to Channel Detail screen for channel ID 1
- Channel details are displayed correctly
- Navigation history is preserved (can navigate back)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-009: Tap Notification - Navigate to Notifications Screen

**Priority:** P0 (Critical)
**Test Type:** Functional
**Navigation Flow:** Deep Linking
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- App is in background or killed

**Test Steps:**
1. From backend, send a notification with alert type:
   ```json
   {
     "title": "System Alert",
     "body": "New notification rule created",
     "type": "alert"
   }
   ```
2. Wait for notification to appear
3. Tap the notification
4. Observe navigation behavior

**Expected Results:**
- App opens (or comes to foreground)
- App navigates to Notifications tab/screen
- Notification logs are displayed
- Navigation history is preserved

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-010: Tap Notification - Navigate to Dashboard

**Priority:** P1 (High)
**Test Type:** Functional
**Navigation Flow:** Default Fallback
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- App is in background or killed

**Test Steps:**
1. From backend, send a notification without specific type:
   ```json
   {
     "title": "Generic Notification",
     "body": "This is a test notification"
   }
   ```
2. Wait for notification to appear
3. Tap the notification
4. Observe navigation behavior

**Expected Results:**
- App opens (or comes to foreground)
- App navigates to Dashboard tab (default fallback)
- Dashboard is displayed correctly

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-011: Stream Failure Notification

**Priority:** P0 (Critical)
**Test Type:** Functional
**Scenario:** Real-world Notification
**Estimated Time:** 5 minutes

**Preconditions:**
- User is logged in (operator or higher)
- Push notifications enabled
- At least one channel exists and is running

**Test Steps:**
1. Navigate to Channel Manager screen
2. Start a channel (if not already running)
3. Wait for channel to reach 'running' status
4. Put app in background
5. Simulate a stream failure (e.g., stop source, break network)
6. Wait for notification rule to trigger (may take 1-2 minutes)
7. Check device notification center
8. Tap the notification

**Expected Results:**
- Stream failure notification appears in notification center
- Notification title indicates stream failure
- Notification body includes channel name and error
- Tapping notification navigates to Channel Detail screen
- Channel detail shows error state and error message

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-012: Multiple Notifications - Stack in Notification Center

**Priority:** P1 (High)
**Test Type:** Functional
**Estimated Time:** 4 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- App in background

**Test Steps:**
1. Send 3-5 test notifications from backend in quick succession
2. Check device notification center
3. Verify all notifications appear
4. Verify they are grouped or stacked (platform-dependent)

**Expected Results:**
- All notifications appear in notification center
- Notifications are timestamped correctly
- On iOS: May be grouped by app
- On Android: May show as stacked notification
- Tapping the group expands to show individual notifications
- All notifications are actionable (tappable)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-013: Dismiss Notification

**Priority:** P1 (High)
**Test Type:** Functional
**Estimated Time:** 2 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- At least one notification is present

**Test Steps:**
1. Send a test notification from backend
2. Wait for notification to appear
3. Swipe to dismiss (iOS) or clear (Android)
4. Verify notification is removed from notification center
5. Open app and check notification logs

**Expected Results:**
- Notification is removed from notification center
- No crash or error occurs
- App continues to function normally
- Notification may or may not appear in app's notification log (depends on implementation)

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-014: Notification Badge Count (iOS)

**Priority:** P2 (Medium)
**Test Type:** Functional
**Platform:** iOS Only
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- iOS device

**Test Steps:**
1. Send 3 test notifications from backend
2. Wait for notifications to appear
3. Check app icon badge count
4. Open the app
5. Check if badge count clears

**Expected Results:**
- App icon shows badge count of 3
- Badge count is visible on home screen
- Opening the app clears the badge count
- Badge count updates correctly as notifications are added/dismissed

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-015: Notification with Custom Data

**Priority:** P1 (High)
**Test Type:** Functional
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled

**Test Steps:**
1. Send a notification with custom data from backend:
   ```json
   {
     "title": "Custom Data Test",
     "body": "Testing custom data payload",
     "type": "alert",
     "channelId": 1,
     "streamId": 100,
     "userId": "user123",
     "customField": "customValue"
   }
   ```
2. Wait for notification to appear
3. Tap the notification
4. Navigate to Notification Logs screen
5. Check if custom data is logged

**Expected Results:**
- Notification appears with correct title and body
- Tapping notification navigates correctly
- Custom data is preserved and accessible
- Notification log shows custom data fields
- No data loss or corruption

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-016: Notification Action Buttons (Optional)

**Priority:** P2 (Medium)
**Test Type:** Functional
**Feature Optional:** Yes
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- Notification actions configured in backend

**Test Steps:**
1. Send a notification with action buttons:
   ```json
   {
     "title": "Stream Stopped",
     "body": "Channel 1 has stopped",
     "type": "channel",
     "channelId": 1,
     "actions": [
       {"id": "restart", "title": "Restart Stream"},
       {"id": "dismiss", "title": "Dismiss"}
     ]
   }
   ```
2. Wait for notification to appear
3. Tap "Restart Stream" action button
4. Verify action is executed

**Expected Results:**
- Notification appears with action buttons
- Tapping action button executes the action
- App opens to relevant screen (or action is performed in background)
- No crash or error occurs

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-017: Push Notification with Image Attachment

**Priority:** P2 (Medium)
**Test Type:** Functional
**Feature Optional:** Yes
**Estimated Time:** 3 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- Notification with image URL configured in backend

**Test Steps:**
1. Send a notification with image attachment:
   ```json
   {
     "title": "Notification with Image",
     "body": "Testing image attachment",
     "imageUrl": "https://example.com/image.png"
   }
   ```
2. Wait for notification to appear
3. Verify image is displayed

**Expected Results:**
- Notification appears with correct title and body
- Image is displayed in notification (platform-dependent)
- Image loads correctly and is visible
- No layout issues or broken image icon

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-018: Notification Sound and Vibration

**Priority:** P2 (Medium)
**Test Type:** Functional
**Estimated Time:** 2 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- Device sound is on
- Device vibration is enabled (Android)

**Test Steps:**
1. Set device volume to audible level
2. Send a test notification from backend
3. Listen for notification sound
4. Feel for vibration (Android)
5. Check notification center

**Expected Results:**
- Notification sound plays (default platform sound or custom)
- Vibration occurs on Android (if enabled)
- Notification appears in notification center
- Sound and vibration timing matches notification appearance

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-019: Background App Refresh - Notification Handling

**Priority:** P2 (Medium)
**Test Type:** Functional
**Platform:** iOS
**Estimated Time:** 5 minutes

**Preconditions:**
- User is logged in
- Push notifications enabled
- iOS device

**Test Steps:**
1. Open app and navigate to Dashboard
2. Put app in background (press home button)
3. Wait 30 seconds
4. Send a test notification from backend
5. Tap the notification
6. Verify app state is preserved

**Expected Results:**
- App opens to the correct screen (based on notification data)
- App state is preserved (user session active, data loaded)
- No blank screens or loading issues
- Navigation history is maintained

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

### TC-PUSH-020: Permission Revocation and Re-grant

**Priority:** P1 (High)
**Test Type:** Functional
**Estimated Time:** 5 minutes

**Preconditions:**
- User is logged in
- Push notifications currently enabled

**Test Steps:**
1. Go to device Settings > Apps > [App Name] > Notifications
2. Disable notifications
3. Return to the app
4. Try to send a test notification from backend (should not appear)
5. Go back to Settings and re-enable notifications
6. Return to the app
7. Send another test notification from backend

**Expected Results:**
- After revocation: Notifications are not received
- App continues to function normally without notifications
- After re-granting: Notifications are received again
- Device is re-registered with backend (if needed)
- No errors or crashes occur

**Actual Results:**
- Status: ☐ Pass ☐ Fail ☐ Skipped
- Notes: _________________________________________________________

---

## Test Execution Summary

### Test Results

| Test Case | Status | Actual Results | Issues Found | Severity |
|-----------|--------|----------------|--------------|----------|
| TC-PUSH-001 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-002 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-003 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-004 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-005 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-006 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-007 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-008 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-009 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-010 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-011 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-012 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-013 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-014 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-015 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-016 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-017 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-018 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-019 | ☐ Pass ☐ Fail ☐ Skipped | | | |
| TC-PUSH-020 | ☐ Pass ☐ Fail ☐ Skipped | | | |

### Summary Statistics

- **Total Test Cases:** 20
- **Passed:** ___
- **Failed:** ___
- **Skipped:** ___
- **Pass Rate:** ___%

### Critical Issues Found

1. **Issue ID:** PUSH-___
   - **Test Case:** TC-PUSH-___
   - **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
   - **Description:**
   - **Steps to Reproduce:**
   - **Expected Behavior:**
   - **Actual Behavior:**
   - **Screenshots:**

2. **Issue ID:** PUSH-___
   - **Test Case:** TC-PUSH-___
   - **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
   - **Description:**
   - **Steps to Reproduce:**
   - **Expected Behavior:**
   - **Actual Behavior:**
   - **Screenshots:**

### Test Environment

- **Device Model:** ___________________
- **OS Version:** ___________________
- **App Version:** ___________________
- **Backend URL:** ___________________
- **Test Date:** ___________________
- **Tester Name:** ___________________

### Sign-off

- **Tester:** ___________________ **Date:** ___________________
- **QA Lead:** ___________________ **Date:** ___________________
- **Status:** ☐ Approved ☐ Conditional Approval ☐ Rejected

---

## Appendix A: Backend Test Notification API

### Send Test Notification

```bash
# Send a simple test notification
curl -X POST http://localhost:8000/api/mobile/devices/test-notification \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test notification from backend",
    "device_id": "<device-id>"
  }'

# Send a notification with custom data
curl -X POST http://localhost:8000/api/mobile/devices/test-notification \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Stream Alert",
    "body": "Channel 1 has stopped",
    "data": {
      "type": "channel",
      "channelId": 1
    }
  }'
```

### Get Registered Devices

```bash
curl -X GET http://localhost:8000/api/mobile/devices \
  -H "Authorization: Bearer <your-token>"
```

---

## Appendix B: Troubleshooting

### Notifications Not Appearing

1. **Check Permissions:**
   - iOS: Settings > [App] > Notifications > Allow Notifications
   - Android: Settings > Apps > [App] > Notifications > On

2. **Check Device Registration:**
   - Call backend API to verify device is registered
   - Check push token is valid

3. **Check Notification Content:**
   - Verify notification payload format
   - Check for invalid characters or missing fields

4. **Check App State:**
   - Verify app is not force-killed (for some tests)
   - Check background app refresh is enabled (iOS)

### Navigation Not Working

1. **Check Notification Data:**
   - Verify `type` field is present and valid
   - Verify IDs (channelId, etc.) are correct

2. **Check Navigation Structure:**
   - Verify screen exists in navigation stack
   - Check screen name matches navigation code

3. **Check App State:**
   - Verify navigationRef is set when notification is tapped
   - Check app is fully loaded before navigating

### Badge Count Not Updating

1. **Check iOS Permissions:**
   - Verify "Badge App Icon" is enabled in notification settings

2. **Check App Implementation:**
   - Verify `setBadgeCountAsync` is being called
   - Check for errors in console logs

---

**End of Document**
