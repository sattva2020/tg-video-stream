# E2E Test Plan: Offline Mode Sync

## Overview

This document outlines the end-to-end (E2E) test plan for offline mode synchronization functionality in the Sattva Streamer mobile app. The tests verify that configuration changes made while offline are properly stored locally and synchronized with the backend when the device comes back online.

## Test Environment

- **Device:** iOS or Android physical device (required for network simulation)
- **Network:** Must be able to enable/disable airplane mode or network connection
- **Backend:** Running backend server at `http://localhost:8000/api`
- **App:** Development build with test helpers enabled

## Prerequisites

1. App is installed on a physical device
2. User is logged into the app
3. Backend server is running and accessible
4. Device has AsyncStorage available (standard on all devices)
5. Network can be disabled/enabled (airplane mode or WiFi toggle)

## Test Cases

### TC-OFFLINE-001: Offline Detection

**Priority:** High
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is connected to network (online)

**Steps:**
1. Enable airplane mode on device (or disable WiFi/cellular)
2. Observe the offline banner appears at top of screen
3. Verify network status shows "Offline" in settings or sync indicator

**Expected Results:**
- Offline banner appears at top of screen within 1-2 seconds
- Network status updates to "Offline"
- Sync indicator shows offline state
- App remains functional for offline-capable features

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-002: Configuration Changes Stored While Offline

**Priority:** High
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline (airplane mode enabled)
- User is on a screen that allows configuration changes (e.g., Settings)

**Steps:**
1. Enable airplane mode
2. Navigate to Settings screen
3. Make a configuration change (e.g., change language from EN to RU)
4. Observe the change is applied in the UI
5. Use test helpers or developer tools to verify AsyncStorage contains the pending change

**Expected Results:**
- Configuration change is applied in the UI immediately
- Pending change is stored in AsyncStorage with:
  - Unique ID
  - Timestamp (current time)
  - Type (update)
  - Endpoint (e.g., `/api/user/settings`)
  - Method (PUT or PATCH)
  - Data object containing the change
- Pending changes count increments
- Sync indicator shows "1 pending change"

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-003: Multiple Offline Changes Stored

**Priority:** Medium
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline

**Steps:**
1. Enable airplane mode
2. Make 3-5 different configuration changes (e.g., language, theme, notification preferences)
3. Use test helpers to verify all changes are stored in AsyncStorage

**Expected Results:**
- All 3-5 changes are stored in AsyncStorage
- Each change has a unique ID
- Each change has a timestamp
- Pending changes count reflects total number of changes
- Changes are stored in order of creation

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-004: Offline Changes Persist Across App Restart

**Priority:** Medium
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline
- At least one pending change exists

**Steps:**
1. Enable airplane mode
2. Make a configuration change
3. Close the app completely (swipe away from recent apps)
4. Reopen the app
5. Verify pending change still exists in AsyncStorage

**Expected Results:**
- Pending change is still present in AsyncStorage
- Pending changes count is accurate
- Configuration change is still visible in UI
- No data loss occurred during app restart

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-005: Automatic Sync When Coming Online

**Priority:** High
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline
- At least 2-3 pending changes exist

**Steps:**
1. Enable airplane mode
2. Make 2-3 configuration changes
3. Disable airplane mode (restore network connection)
4. Observe the sync indicator
5. Wait 1-2 seconds for sync to complete
6. Verify changes are synced to backend

**Expected Results:**
- Network status updates to "Online" within 1-2 seconds
- Sync indicator shows "Syncing..." state
- Pending changes count decreases as items are synced
- After 1-2 seconds, all pending changes are synced
- Pending changes count returns to 0
- Last sync timestamp is updated
- Sync indicator shows success state
- Changes are visible on backend (verify via web interface or API)

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-006: Sync Indicator Shows Success

**Priority:** Medium
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline
- At least 1 pending change exists

**Steps:**
1. Enable airplane mode
2. Make a configuration change
3. Disable airplane mode
4. Observe sync indicator animation/states
5. Verify final state shows success

**Expected Results:**
- Sync indicator shows following progression:
  1. "Offline" while airplane mode is enabled
  2. "1 pending change" after making change
  3. "Syncing..." when coming online
  4. "Synced successfully" or checkmark after completion
- Sync timestamp is displayed (e.g., "Last synced: just now")
- No errors shown in sync indicator

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-007: Manual Sync Button

**Priority:** Low
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is online
- At least 1 pending change exists

**Steps:**
1. Enable airplane mode
2. Make a configuration change
3. Disable airplane mode
4. Before automatic sync triggers, tap manual sync button (if available)
5. Observe sync process

**Expected Results:**
- Manual sync button is visible when pending changes exist
- Tapping sync button triggers immediate sync
- Sync indicator updates to "Syncing..."
- Changes sync successfully
- Pending changes count decreases to 0

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-008: Sync Retry on Failure

**Priority:** Medium
**Type:** Error Handling

**Preconditions:**
- User is logged in
- Device is offline
- Backend server is running but will be stopped during test

**Steps:**
1. Enable airplane mode
2. Make a configuration change
3. Disable airplane mode
4. Stop backend server (or block network access to backend)
5. Wait for automatic sync attempt
6. Observe error handling
7. Restart backend server
8. Verify retry logic works

**Expected Results:**
- Initial sync attempt fails (network error or server error)
- Failed item is moved to sync queue
- Retry count is incremented (now 1)
- Error message is stored with item
- Sync queue shows 1 item with retry count
- When backend comes back online, sync retries
- After 3 failed attempts, item remains in queue but stops retrying
- Error is logged appropriately

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-009: Conflict Resolution - Server Wins

**Priority:** High
**Type:** Functional

**Preconditions:**
- User is logged in on both mobile and web
- Two devices available (or web interface)

**Steps:**
1. Enable airplane mode on mobile device
2. On web interface (different device), make a configuration change to the same setting
3. On mobile device (still offline), make a different change to the same setting
4. Disable airplane mode on mobile device
5. Observe sync behavior and conflict resolution

**Expected Results:**
- Mobile detects conflict (server data differs from local pending change)
- Conflict resolution strategy: Server version wins
- Local pending change is discarded or marked as conflicted
- Server version is applied to mobile device
- User is notified of conflict (via in-app message or notification)
- UI reflects server version after sync

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-010: Conflict Resolution - User Notification

**Priority:** Medium
**Type:** Functional

**Preconditions:**
- User is logged in on both mobile and web
- Conflict scenario exists (from TC-OFFLINE-009)

**Steps:**
1. Create a conflict (make changes on both web and mobile while mobile is offline)
2. Disable airplane mode on mobile
3. Observe user notification about conflict

**Expected Results:**
- User receives clear notification about conflict
- Notification includes:
  - Which setting was conflicted
  - Server value
  - Local value that was discarded
  - Option to review or keep local value (if supported)
- Conflict is logged in sync history

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-011: Conflict Resolution - Multiple Conflicts

**Priority:** Low
**Type:** Functional

**Preconditions:**
- User is logged in on both mobile and web
- Multiple settings can be changed

**Steps:**
1. Enable airplane mode on mobile
2. On web, change 3 different settings
3. On mobile (offline), change the same 3 settings to different values
4. Disable airplane mode on mobile
5. Observe conflict resolution for all 3 settings

**Expected Results:**
- All 3 conflicts are detected
- Each conflict is resolved independently
- Server version wins for all 3
- User receives notification about all conflicts
- All settings reflect server values after sync

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-012: Clear Pending Changes

**Priority:** Low
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline
- At least 2-3 pending changes exist

**Steps:**
1. Enable airplane mode
2. Make 2-3 configuration changes
3. Find option to clear pending changes (in settings or sync menu)
4. Tap "Clear pending changes"
5. Confirm in dialog (if confirmation shown)
6. Verify AsyncStorage is cleared

**Expected Results:**
- Confirmation dialog appears (if implemented)
- After confirmation, all pending changes are removed
- AsyncStorage keys for pending changes and sync queue are cleared
- Pending changes count returns to 0
- UI may revert to original values (before offline changes)

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-013: Offline Data Cleared on Logout

**Priority:** Medium
**Type:** Security

**Preconditions:**
- User is logged in
- Device is offline or online
- At least 1 pending change exists

**Steps:**
1. Enable airplane mode (optional - can test both online and offline)
2. Make a configuration change
3. Logout from app
4. Verify AsyncStorage is cleared

**Expected Results:**
- All pending changes are cleared from AsyncStorage
- Sync queue is cleared
- Last sync timestamp is cleared
- No offline data remains after logout
- Next user starts with clean state

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-014: Large Number of Pending Changes

**Priority:** Low
**Type:** Performance

**Preconditions:**
- User is logged in
- Device is offline

**Steps:**
1. Enable airplane mode
2. Make 20-30 configuration changes (may need to automate or use test helpers)
3. Verify all are stored in AsyncStorage
4. Disable airplane mode
5. Observe sync performance

**Expected Results:**
- All 20-30 changes are stored successfully
- AsyncStorage performance remains acceptable (<1 second to save)
- Pending changes count is accurate
- Sync process handles all changes without crashing
- Sync completes in reasonable time (<5 seconds for 20-30 items)
- No memory issues or crashes

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

### TC-OFFLINE-015: Offline Mode with Different Request Types

**Priority:** Medium
**Type:** Functional

**Preconditions:**
- User is logged in
- Device is offline
- App supports different operations (create, update, delete)

**Steps:**
1. Enable airplane mode
2. Perform a CREATE operation (e.g., create a new playlist)
3. Perform an UPDATE operation (e.g., update channel settings)
4. Perform a DELETE operation (e.g., delete a notification rule)
5. Verify all three request types are stored correctly
6. Disable airplane mode
7. Verify all sync correctly

**Expected Results:**
- All three request types (POST, PUT/PATCH, DELETE) are stored
- Each has correct type, endpoint, and data
- All sync correctly when coming online
- Order of operations is preserved
- Backend applies changes in correct order

**Actual Results:**
-

**Status:** ❌ Pass  ❌ Fail  ⏭️ Skipped

**Notes:**


---

## Test Execution Summary

**Date of Testing:**
**Tester Name:**
**Device:**
**OS Version:**
**App Version:**

### Results Overview

| Test Case | Pass | Fail | Skipped | Notes |
|-----------|------|------|---------|-------|
| TC-OFFLINE-001: Offline Detection | ☐ | ☐ | ☐ | |
| TC-OFFLINE-002: Changes Stored Offline | ☐ | ☐ | ☐ | |
| TC-OFFLINE-003: Multiple Changes | ☐ | ☐ | ☐ | |
| TC-OFFLINE-004: Persist Across Restart | ☐ | ☐ | ☐ | |
| TC-OFFLINE-005: Auto Sync When Online | ☐ | ☐ | ☐ | |
| TC-OFFLINE-006: Sync Indicator | ☐ | ☐ | ☐ | |
| TC-OFFLINE-007: Manual Sync Button | ☐ | ☐ | ☐ | |
| TC-OFFLINE-008: Sync Retry on Failure | ☐ | ☐ | ☐ | |
| TC-OFFLINE-009: Conflict - Server Wins | ☐ | ☐ | ☐ | |
| TC-OFFLINE-010: Conflict Notification | ☐ | ☐ | ☐ | |
| TC-OFFLINE-011: Multiple Conflicts | ☐ | ☐ | ☐ | |
| TC-OFFLINE-012: Clear Pending Changes | ☐ | ☐ | ☐ | |
| TC-OFFLINE-013: Data Cleared on Logout | ☐ | ☐ | ☐ | |
| TC-OFFLINE-014: Large Number of Changes | ☐ | ☐ | ☐ | |
| TC-OFFLINE-015: Different Request Types | ☐ | ☐ | ☐ | |

**Total Passed:** ____ / 15
**Total Failed:** ____ / 15
**Total Skipped:** ____ / 15

### Critical Issues Found

1.
2.
3.

### Overall Assessment

- ❌ All tests passed - Ready for production
- ❌ Minor issues found - Fix before production
- ❌ Major issues found - Significant rework needed
- ❌ Critical issues found - Blocker for release

### Sign-off

**Tester Signature:** ____________________
**Date:** ____________________
**Notes:**
