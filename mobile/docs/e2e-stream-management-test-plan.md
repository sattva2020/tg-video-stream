# E2E Test Plan: Stream Management

## Overview
This document contains end-to-end test cases for the stream management functionality in the mobile app, including viewing channels, starting/stopping streams, and verifying status updates.

**Test Suite:** Stream Management E2E Tests
**Platform:** iOS 13.0+ / Android 5.0+ (API 21+)
**Prerequisites:** User authenticated, backend server running, test channels configured

---

## Test Execution Summary

| Metric | Value |
|--------|-------|
| Total Test Cases | 10 |
| Passed | ___ |
| Failed | ___ |
| Skipped | ___ |
| Execution Date | ___ |
| Tester | ___ |
| Device Model | ___ |
| OS Version | ___ |
| App Version | ___ |

**Overall Result:** ⬜ Pass  ⬜ Fail  ⬜ Partial

**Notes:**
___

---

## Test Cases

### TC-STREAM-001: Channel Manager Screen Display

**Description:** Verify channel manager screen loads and displays correctly

**Preconditions:**
- User is authenticated
- Backend server is running
- At least one channel exists in the system

**Steps:**
1. Navigate to Channels tab from bottom navigation
2. Verify channel manager screen loads

**Expected Results:**
- Channel manager screen displays with header icon and title
- Screen shows "Channels" as title
- Subtitle displays "Manage your streaming channels"
- Channel count banner shows total number of channels
- If channels exist, they are displayed in a list
- If no channels, empty state displays with icon and message

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-002: Channel List Loads from Backend

**Description:** Verify channel list loads correctly from backend API

**Preconditions:**
- User is authenticated
- Backend server is running
- At least 2 channels exist with different statuses

**Steps:**
1. Navigate to Channels tab
2. Wait for loading state to complete
3. Verify all channels from backend are displayed

**Expected Results:**
- Loading spinner displays while fetching
- All channels configured in backend appear in the list
- Each channel displays:
  - Channel name
  - Chat username or ID
  - Stream type icon (audio/video)
  - Current status badge
  - Start/Stop buttons (based on status)
- Channel count matches backend count
- No duplicate channels
- Channels are ordered correctly

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-003: Channel Status Display

**Description:** Verify channel status is correctly displayed for all states

**Preconditions:**
- User is authenticated
- Channels exist in different states (stopped, running, starting, stopping, error)

**Steps:**
1. Navigate to Channels tab
2. Review status badges for each channel
3. Verify status-specific styling and icons

**Expected Results:**
- **Stopped channels:**
  - Gray badge with ⏹ icon
  - "Stopped" text
  - Start button visible (green)
- **Running channels:**
  - Green badge with 📡 icon
  - "Running" text
  - Stop button visible (red)
- **Starting channels:**
  - Blue badge with ⏳ icon
  - "Starting..." text with spinner
  - Stop button visible
- **Stopping channels:**
  - Orange/amber badge with ⏳ icon
  - "Stopping..." text with spinner
  - Stop button visible
- **Error channels:**
  - Red badge with ⚠️ icon
  - "Error" text
  - Error message displayed below badge
  - Start button visible (green)

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-004: Start Channel - Confirmation Dialog

**Description:** Verify confirmation dialog appears when starting a stopped channel

**Preconditions:**
- User is authenticated
- At least one channel is in "stopped" status

**Steps:**
1. Navigate to Channels tab
2. Locate a channel with "stopped" status
3. Tap the "Start" button on the channel card

**Expected Results:**
- Alert dialog appears immediately
- Dialog title: "Start Stream" (translated)
- Dialog message: "Start streaming to this channel?" (translated)
- Two buttons displayed:
  - "Cancel" button (closes dialog)
  - "Start" button (confirms action)
- Dialog is modal (blocks background interaction)

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-005: Start Channel - Success Flow

**Description:** Verify channel starts successfully and status updates to 'online'

**Preconditions:**
- User is authenticated
- At least one channel is in "stopped" status

**Steps:**
1. Navigate to Channels tab
2. Tap "Start" button on a stopped channel
3. Confirm start in the dialog
4. Wait for operation to complete

**Expected Results:**
- Confirmation dialog closes
- Success alert displays: "Stream started successfully" (translated)
- Channel status badge changes from "Stopped" to "Starting..." (blue with spinner)
- Within 2-5 seconds, status updates to "Running" (green)
- Status icon changes to 📡
- Stop button becomes available (red button)
- Start button is hidden
- Channel is now streaming
- No error messages displayed

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-006: Stop Channel - Confirmation Dialog

**Description:** Verify confirmation dialog appears when stopping a running channel

**Preconditions:**
- User is authenticated
- At least one channel is in "running" status

**Steps:**
1. Navigate to Channels tab
2. Locate a channel with "running" status
3. Tap the "Stop" button on the channel card

**Expected Results:**
- Alert dialog appears immediately
- Dialog title: "Stop Stream" (translated)
- Dialog message: "Stop streaming to this channel?" (translated)
- Two buttons displayed:
  - "Cancel" button (closes dialog)
  - "Stop" button (red/destructive style, confirms action)
- Dialog is modal (blocks background interaction)

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-007: Stop Channel - Success Flow

**Description:** Verify channel stops successfully and status updates to 'offline'

**Preconditions:**
- User is authenticated
- At least one channel is in "running" status

**Steps:**
1. Navigate to Channels tab
2. Tap "Stop" button on a running channel
3. Confirm stop in the dialog
4. Wait for operation to complete

**Expected Results:**
- Confirmation dialog closes
- Success alert displays: "Stream stopped successfully" (translated)
- Channel status badge changes from "Running" to "Stopping..." (orange/amber with spinner)
- Within 2-5 seconds, status updates to "Stopped" (gray)
- Status icon changes to ⏹
- Start button becomes available (green button)
- Stop button is hidden
- Channel is no longer streaming
- No error messages displayed

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-008: Pull-to-Refresh Channel List

**Description:** Verify pull-to-refresh functionality updates channel list

**Preconditions:**
- User is authenticated
- Channel list is displayed

**Steps:**
1. Navigate to Channels tab
2. Scroll to top of channel list
3. Pull down to trigger refresh
4. Observe refresh indicator
5. Wait for refresh to complete

**Expected Results:**
- Refresh spinner appears at top of list
- Channels reload from backend
- Loading indicator displays during refresh
- Refresh spinner disappears when complete
- Channel statuses update if changed on backend
- Channel count updates if channels added/removed
- No errors during refresh
- Refresh completes within 2-3 seconds

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-009: Auto-Refresh During Transitional States

**Description:** Verify channels auto-refresh while in starting/stopping states

**Preconditions:**
- User is authenticated
- User can start a channel

**Steps:**
1. Navigate to Channels tab
2. Start a channel and confirm the action
3. Observe the channel status
4. Watch for automatic status updates
5. Verify status changes from "Starting..." to "Running"

**Expected Results:**
- After starting, status shows "Starting..." with spinner
- Channel list automatically refreshes every 2 seconds
- No user interaction required
- Status updates automatically when backend changes state
- When status reaches "Running", auto-refresh stops
- Transition from "Starting..." to "Running" happens automatically
- No duplicate refresh requests
- Auto-refresh stops when all channels are in stable states (stopped/running/error)

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

### TC-STREAM-010: Error Handling - Start Failure

**Description:** Verify error handling when starting a channel fails

**Preconditions:**
- User is authenticated
- Backend is configured to fail start operation (or channel has error condition)

**Steps:**
1. Navigate to Channels tab
2. Attempt to start a channel that will fail
3. Confirm the action
4. Observe error handling

**Expected Results:**
- Confirmation dialog closes
- Error alert displays with meaningful message
- Error message describes the failure reason
- Channel status shows "Error" (red badge with ⚠️)
- Error message displays on channel card
- Start button remains available (can retry)
- No app crash or freeze
- User can recover and try again

**Actual Results:**
___

**Status:**
⬜ Pass  ⬜ Fail  ⬜ Skipped

**Notes:**
___

---

## Additional Test Scenarios

### Network Error Scenarios

**TC-STREAM-011: Network Error During Channel Load**
- Enable airplane mode
- Navigate to Channels tab
- Verify error message displays
- Disable airplane mode
- Verify retry works

**TC-STREAM-012: Network Error During Start**
- Start a channel
- Enable airplane mode before completion
- Verify error handling
- Disable airplane mode
- Verify retry capability

### Edge Cases

**TC-STREAM-013: Rapid Start/Stop Taps**
- Rapidly tap Start button multiple times
- Verify only one operation executes
- Verify UI doesn't freeze or crash

**TC-STREAM-014: Multiple Channels Starting Simultaneously**
- Start multiple channels in quick succession
- Verify all status updates correctly
- Verify auto-refresh works for all channels

**TC-STREAM-015: Channel List with Many Channels**
- Configure 20+ channels
- Verify scrolling performance
- Verify all channels load correctly
- Verify status updates work for all

---

## Test Data Requirements

### Minimum Test Channels:
- 1 channel in "stopped" status
- 1 channel in "running" status
- 1 channel in "error" status (if possible)

### Optional Test Channels:
- Channels with different stream types (audio/video)
- Channels with/without chat usernames
- Channels with different video qualities
- Channels with error messages

---

## Bug Report Template

If any test fails, document the issue using this template:

```markdown
**Bug ID:** STREAM-XXX
**Test Case:** TC-STREAM-XXX
**Severity:** ⬜ Critical  ⬜ High  ⬜ Medium  ⬜ Low

**Description:**
[Brief description of the issue]

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Screenshots:**
[Attach screenshots if applicable]

**Device Information:**
- Device Model: [e.g., iPhone 12 Pro]
- OS Version: [e.g., iOS 16.0]
- App Version: [e.g., 1.0.0]

**Console Logs:**
[Paste relevant console errors]

**Additional Notes:**
[Any other relevant information]
```

---

## Sign-off

**Tester Signature:** ___

**Date:** ___

**Comments:**
___

---

**Document Version:** 1.0.0
**Last Updated:** 2026-01-23
