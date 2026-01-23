# E2E Offline Sync Testing Checklist

## Quick Reference for Testers

**Testing Date:** ____________________
**Tester:** ____________________
**Device (iOS/Android):** ____________________
**App Version:** ____________________

---

## Prerequisites Checklist

Before starting testing, verify:

- [ ] App is installed on physical device
- [ ] User is logged into the app
- [ ] Backend server is running and accessible
- [ ] Device can enable/disable airplane mode or WiFi
- [ ] Test helpers are available (for verification)
- [ ] Have access to web interface for conflict testing

---

## Quick Test Commands

### Using Test Helpers (in development mode)

```javascript
// In React Native debugger or console
import * as testHelpers from './src/utils/testHelpers';

// Get sync status
const status = await testHelpers.getSyncStatus(isOnline);

// Get pending changes
const pending = await testHelpers.getPendingChanges();

// Get sync queue
const queue = await testHelpers.getSyncQueue();

// Run E2E test suite
const results = await testHelpers.runOfflineSyncE2E(isOnline, initialChanges, finalChanges);
```

---

## Verification Steps

### 1. Offline Detection (TC-OFFLINE-001)

**Steps:**
1. Enable airplane mode
2. Check for offline banner
3. Verify network status

**Expected:**
- [ ] Offline banner appears within 1-2 seconds
- [ ] Network status shows "Offline"
- [ ] Sync indicator shows offline state

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 2. Changes Stored Offline (TC-OFFLINE-002)

**Steps:**
1. Enable airplane mode
2. Make a configuration change (e.g., change language)
3. Check AsyncStorage using test helpers

**Expected:**
- [ ] Change is applied in UI
- [ ] Pending change stored in AsyncStorage
- [ ] Change has unique ID and timestamp
- [ ] Pending count increments to 1

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 3. Multiple Changes (TC-OFFLINE-003)

**Steps:**
1. Enable airplane mode
2. Make 3-5 different configuration changes
3. Verify all stored in AsyncStorage

**Expected:**
- [ ] All changes stored in AsyncStorage
- [ ] Each has unique ID
- [ ] Pending count accurate (e.g., "5 pending changes")

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 4. Persist Across Restart (TC-OFFLINE-004)

**Steps:**
1. Enable airplane mode
2. Make a configuration change
3. Close app completely (swipe away)
4. Reopen app
5. Check AsyncStorage

**Expected:**
- [ ] Pending change still present
- [ ] No data loss
- [ ] UI still shows offline change

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 5. Auto Sync When Online (TC-OFFLINE-005) ⭐ CRITICAL

**Steps:**
1. Enable airplane mode
2. Make 2-3 configuration changes
3. Disable airplane mode
4. Observe sync process
5. Verify backend receives changes

**Expected:**
- [ ] Network status updates to "Online"
- [ ] Sync indicator shows "Syncing..."
- [ ] Pending count decreases
- [ ] All changes sync to backend
- [ ] Pending count returns to 0
- [ ] Last sync timestamp updated

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 6. Sync Indicator Success (TC-OFFLINE-006)

**Steps:**
1. Make a change while offline
2. Come back online
3. Observe sync indicator states

**Expected:**
- [ ] Shows "Offline" when offline
- [ ] Shows "X pending changes" after change
- [ ] Shows "Syncing..." when syncing
- [ ] Shows "Synced successfully" when done
- [ ] Displays last sync time

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 7. Manual Sync Button (TC-OFFLINE-007)

**Steps:**
1. Make a change while offline
2. Come online
3. Tap manual sync button (if available)

**Expected:**
- [ ] Manual sync button visible when pending changes exist
- [ ] Tapping triggers immediate sync
- [ ] Changes sync successfully
- [ ] Pending count goes to 0

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 8. Sync Retry on Failure (TC-OFFLINE-008)

**Steps:**
1. Make a change while offline
2. Come online with backend stopped
3. Observe error handling
4. Restart backend
5. Verify retry works

**Expected:**
- [ ] Sync attempt fails gracefully
- [ ] Item moved to sync queue
- [ ] Retry count incremented
- [ ] Error stored with item
- [ ] Retry succeeds when backend available
- [ ] After 3 failures, retry stops

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 9. Conflict Resolution - Server Wins (TC-OFFLINE-009) ⭐ CRITICAL

**Steps:**
1. Enable airplane mode on mobile
2. On web, change a setting to Value A
3. On mobile (offline), change same setting to Value B
4. Disable airplane mode on mobile
5. Observe sync behavior

**Expected:**
- [ ] Conflict is detected
- [ ] Server version (Value A) wins
- [ ] Local version (Value B) discarded
- [ ] User notified of conflict
- [ ] UI reflects server value

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 10. Conflict Notification (TC-OFFLINE-010)

**Steps:**
1. Create a conflict (see TC-OFFLINE-009)
2. Observe user notification

**Expected:**
- [ ] User receives clear notification
- [ ] Notification shows which setting conflicted
- [ ] Shows server value and local value
- [ ] Option to review (if supported)
- [ ] Conflict logged in history

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 11. Multiple Conflicts (TC-OFFLINE-011)

**Steps:**
1. Create conflicts for 3 different settings (web + mobile offline)
2. Sync mobile device
3. Observe resolution

**Expected:**
- [ ] All 3 conflicts detected
- [ ] Each resolved independently
- [ ] Server wins for all 3
- [ ] User notified of all conflicts

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 12. Clear Pending Changes (TC-OFFLINE-012)

**Steps:**
1. Make 2-3 changes while offline
2. Find option to clear pending changes
3. Tap "Clear pending changes"
4. Confirm if prompted
5. Verify AsyncStorage cleared

**Expected:**
- [ ] Confirmation dialog appears
- [ ] After confirm, all changes removed
- [ ] AsyncStorage cleared
- [ ] Pending count returns to 0

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 13. Data Cleared on Logout (TC-OFFLINE-013)

**Steps:**
1. Make a change while offline (or online)
2. Logout from app
3. Check AsyncStorage

**Expected:**
- [ ] All pending changes cleared
- [ ] Sync queue cleared
- [ ] Last sync timestamp cleared
- [ ] No offline data remains

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 14. Large Number of Changes (TC-OFFLINE-014)

**Steps:**
1. Enable airplane mode
2. Make 20-30 changes (may need automation)
3. Verify storage and sync performance

**Expected:**
- [ ] All changes stored successfully
- [ ] Storage performance acceptable (<1s)
- [ ] Sync completes in reasonable time (<5s)
- [ ] No crashes or memory issues

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


### 15. Different Request Types (TC-OFFLINE-015)

**Steps:**
1. Enable airplane mode
2. Perform CREATE operation (e.g., create playlist)
3. Perform UPDATE operation (e.g., update settings)
4. Perform DELETE operation (e.g., delete rule)
5. Sync and verify

**Expected:**
- [ ] All three types stored correctly
- [ ] All sync correctly when online
- [ ] Order of operations preserved

**Result:** ❌ Pass  ❌ Fail

**Notes:** ____________________


---

## Test Scenarios

### Scenario 1: Basic Offline Flow

**Setup:** Online → Offline → Make Change → Online

1. [ ] Start with device online
2. [ ] Enable airplane mode
3. [ ] Verify offline banner appears
4. [ ] Change language setting from EN to RU
5. [ ] Verify UI updates to Russian
6. [ ] Check AsyncStorage has pending change
7. [ ] Disable airplane mode
8. [ ] Watch sync indicator show "Syncing..."
9. [ ] Verify sync completes successfully
10. [ ] Verify backend shows RU as language preference

**Result:** ❌ Pass  ❌ Fail


### Scenario 2: Conflict Scenario

**Setup:** Web + Mobile, Mobile goes offline

1. [ ] Log in on web interface (Device A)
2. [ ] Log in on mobile app (Device B)
3. [ ] Enable airplane mode on mobile
4. [ ] On web, change theme from light to dark
5. [ ] On mobile (offline), change theme from light to system
6. [ ] Disable airplane mode on mobile
7. [ ] Observe sync process
8. [ ] Verify conflict detection
9. [ ] Verify server version (dark) wins
10. [ ] Verify user notified of conflict
11. [ ] Verify mobile UI shows dark theme

**Result:** ❌ Pass  ❌ Fail


### Scenario 3: Multiple Offline Sessions

**Setup:** Multiple offline → online cycles

1. [ ] Start online
2. [ ] Enable airplane mode
3. [ ] Make 2 changes
4. [ ] Disable airplane mode
5. [ ] Verify sync completes
6. [ ] Enable airplane mode again
7. [ ] Make 3 more changes
8. [ ] Disable airplane mode
9. [ ] Verify all 5 changes sync correctly
10. [ ] Verify no duplicates or errors

**Result:** ❌ Pass  ❌ Fail


---

## Results Summary

### Test Case Results

| Category | Total | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| Offline Detection | 1 | ___ | ___ | ___ |
| Data Storage | 4 | ___ | ___ | ___ |
| Sync Behavior | 3 | ___ | ___ | ___ |
| Error Handling | 1 | ___ | ___ | ___ |
| Conflict Resolution | 3 | ___ | ___ | ___ |
| Data Management | 2 | ___ | ___ | ___ |
| Performance | 1 | ___ | ___ | ___ |
| **TOTAL** | **15** | **___** | **___** | **___** |

### Critical Tests Status

- [ ] TC-OFFLINE-005: Auto Sync When Online - ❌ Pass  ❌ Fail
- [ ] TC-OFFLINE-009: Conflict Resolution - ❌ Pass  ❌ Fail

**Overall Status:**
- [ ] ✅ All tests passed - Ready for production
- [ ] ⚠️ Minor issues - Fix before production recommended
- [ ] ❌ Major issues - Significant rework needed
- [ ] 🚫 Critical issues - Blocker for release

### Issues Found

**Critical:**
1.
2.
3.

**Major:**
1.
2.
3.

**Minor:**
1.
2.
3.

### Tester Comments




---

## Sign-off

**Tester:** ____________________
**Date:** ____________________
**Overall Assessment:** ____________________
**Approved for Next Phase:** [ ] Yes  [ ] No  [ ] Needs Review

**Reviewer:** ____________________
**Date:** ____________________
**Review Notes:**
