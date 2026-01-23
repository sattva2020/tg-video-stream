# Push Notification E2E Test Checklist

## Quick Reference for Testing Push Notifications

**Test Plan:** e2e-push-notification-test-plan.md
**Version:** 1.0
**Date:** 2026-01-23

---

## Prerequisites Checklist

Before starting push notification testing, verify:

- [ ] Backend server is running and accessible
- [ ] Valid test account with operator or higher permissions
- [ ] Physical iOS device (iOS 13+) or Android device (API 21+)
- [ ] App is installed (development or production build)
- [ ] Network connectivity (WiFi or cellular)
- [ ] Push notification credentials configured (APNs for iOS, FCM for Android)
- [ ] Backend API endpoint for sending test notifications is available

---

## Quick Test Commands

### Get Registered Devices
```bash
curl -X GET http://localhost:8000/api/mobile/devices \
  -H "Authorization: Bearer <your-token>"
```

### Send Test Notification (Basic)
```bash
curl -X POST http://localhost:8000/api/mobile/devices/test-notification \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test notification"}'
```

### Send Test Notification (Channel Alert)
```bash
curl -X POST http://localhost:8000/api/mobile/devices/test-notification \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Stream Alert",
    "body": "Channel 1 has stopped",
    "data": {"type": "channel", "channelId": 1}
  }'
```

---

## Test Case Checklist

### Permission and Registration

| # | Test Case | Pass | Fail | Notes |
|---|-----------|------|------|-------|
| 1 | Permission prompt appears on first launch | ☐ | ☐ | |
| 2 | Allow permission - device registers successfully | ☐ | ☐ | |
| 3 | Deny permission - app continues without errors | ☐ | ☐ | |
| 4 | Device registered with valid push token | ☐ | ☐ | Check backend API |
| 5 | Platform detected correctly (ios/android) | ☐ | ☐ | |

### Notification Reception

| # | Test Case | Pass | Fail | Notes |
|---|-----------|------|------|-------|
| 6 | Receive notification in foreground | ☐ | ☐ | App visible |
| 7 | Receive notification in background | ☐ | ☐ | App not visible, not killed |
| 8 | Receive notification when app is killed | ☐ | ☐ | Force quit app |
| 9 | Multiple notifications stack correctly | ☐ | ☐ | Send 3-5 notifications |
| 10 | Dismiss notification works | ☐ | ☐ | Swipe to dismiss |

### Notification Tap and Navigation

| # | Test Case | Pass | Fail | Notes |
|---|-----------|------|------|-------|
| 11 | Tap notification - navigate to channel screen | ☐ | ☐ | type: "channel", channelId: 1 |
| 12 | Tap notification - navigate to notifications screen | ☐ | ☐ | type: "alert" |
| 13 | Tap notification - navigate to dashboard (default) | ☐ | ☐ | No type specified |
| 14 | Tap notification from killed state launches app | ☐ | ☐ | Force quit, then tap |
| 15 | Background notification tap preserves app state | ☐ | ☐ | iOS: background refresh |

### Stream Alerts

| # | Test Case | Pass | Fail | Notes |
|---|-----------|------|------|-------|
| 16 | Stream failure notification appears | ☐ | ☐ | Stop running stream |
| 17 | Stream alert navigates to correct channel | ☐ | ☐ | Tap stream failure notification |
| 18 | Error message displayed in channel detail | ☐ | ☐ | Verify error_message field |

### Advanced Features

| # | Test Case | Pass | Fail | Notes |
|---|-----------|------|------|-------|
| 19 | Custom data preserved in notification | ☐ | ☐ | Check notification log |
| 20 | Notification badge count (iOS) | ☐ | ☐ | Send 3 notifications |
| 21 | Notification sound plays | ☐ | ☐ | Device volume on |
| 22 | Notification vibrates (Android) | ☐ | ☐ | Vibration enabled |
| 23 | Permission revocation handled correctly | ☐ | ☐ | Revoke in Settings, test |
| 24 | Permission re-grant restores notifications | ☐ | ☐ | Re-enable in Settings |

---

## Quick Test Scenarios

### Scenario 1: Basic Push Notification Test (5 minutes)
1. [ ] Login to app
2. [ ] Grant notification permissions
3. [ ] Verify device registered (check backend API)
4. [ ] Put app in background
5. [ ] Send test notification from backend
6. [ ] Verify notification appears
7. [ ] Tap notification
8. [ ] Verify app opens to correct screen

### Scenario 2: Stream Failure Alert Test (10 minutes)
1. [ ] Navigate to Channel Manager
2. [ ] Start a channel
3. [ ] Wait for channel to reach 'running' status
4. [ ] Put app in background
5. [ ] Simulate stream failure (stop source, break network)
6. [ ] Wait for notification (1-2 minutes)
7. [ ] Verify stream failure notification appears
8. [ ] Tap notification
9. [ ] Verify app navigates to channel detail
10. [ ] Verify error state and message displayed

### Scenario 3: Background and Killed State Test (8 minutes)
1. [ ] Send notification with app in foreground (verify received)
2. [ ] Put app in background
3. [ ] Send notification (verify appears in notification center)
4. [ ] Tap notification (verify app opens to correct screen)
5. [ ] Force quit app
6. [ ] Send notification (verify appears)
7. [ ] Tap notification (verify app launches and navigates)

### Scenario 4: Navigation Deep Linking Test (10 minutes)
1. [ ] Test channel notification (type: "channel", channelId: 1)
   - [ ] Navigates to Channel Detail screen
2. [ ] Test alert notification (type: "alert")
   - [ ] Navigates to Notifications screen
3. [ ] Test playlist notification (type: "playlist", channelId: 1)
   - [ ] Navigates to Playlist screen
4. [ ] Test settings notification (type: "settings")
   - [ ] Navigates to Settings screen
5. [ ] Test generic notification (no type)
   - [ ] Navigates to Dashboard screen (default)

### Scenario 5: Permission Handling Test (7 minutes)
1. [ ] Fresh app install
2. [ ] Login and verify permission prompt appears
3. [ ] Allow permissions and verify device registers
4. [ ] Send test notification (verify received)
5. [ ] Go to device Settings, revoke notification permission
6. [ ] Send test notification (verify NOT received)
7. [ ] Re-enable notification permission
8. [ ] Send test notification (verify received again)

---

## Results Summary

### Pass/Fail Counts
- **Total Tests:** ___
- **Passed:** ___
- **Failed:** ___
- **Pass Rate:** ___%

### Failed Tests Detail

| Test # | Test Case | Issue | Severity |
|--------|-----------|-------|----------|
| | | | |
| | | | |
| | | | |
| | | | |

### Issues Found

**Issue 1:** ___________________
- Test Case: TC-PUSH-___
- Severity: ☐ Critical ☐ High ☐ Medium ☐ Low
- Description: ___________________
- Steps to Reproduce: ___________________
- Screenshots: ☐ Yes ☐ No

**Issue 2:** ___________________
- Test Case: TC-PUSH-___
- Severity: ☐ Critical ☐ High ☐ Medium ☐ Low
- Description: ___________________
- Steps to Reproduce: ___________________
- Screenshots: ☐ Yes ☐ No

---

## Test Environment

- **Device Model:** ___________________
- **OS Version:** ___________________
- **App Version:** ___________________
- **Build Type:** ☐ Development ☐ Production
- **Backend URL:** ___________________
- **Test Date:** ___________________
- **Tester Name:** ___________________
- **Test Duration:** ___________________

---

## Quick Tips

### iOS Testing Tips
- Always test on physical device (simulator has limited push notification support)
- Check Settings > Notifications > [App] for permission status
- Force quit app by swiping up from app switcher
- Badge count requires "Badge App Icon" permission

### Android Testing Tips
- Test on Android 13+ for POST_NOTIFICATIONS permission
- Check Settings > Apps > [App] > Notifications
- Force stop app from Settings > Apps > [App] > Force Stop
- Verify FCM configuration in app.json

### Backend Testing Tips
- Use backend API to verify device registration
- Check backend logs for push token errors
- Verify notification payload format
- Test with both Expo push token and direct platform tokens (APNs/FCM)

### Debugging Tips
- Check React Native console for errors
- Use Expo dev tools for logging
- Verify network connectivity
- Check backend API responses
- Test with simple notification first, then add complexity

---

## Sign-off

- **Tester:** ___________________ **Date:** ___________________
- **QA Lead:** ___________________ **Date:** ___________________
- **Status:** ☐ Approved ☐ Conditional Approval ☐ Rejected
- **Notes:** _________________________________________________________

---

**End of Checklist**
