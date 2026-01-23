# E2E Stream Management Testing Checklist

## Quick Reference Checklist

Use this checklist during manual testing to track progress. For detailed test steps, see [e2e-stream-management-test-plan.md](./e2e-stream-management-test-plan.md).

---

## Test Environment

**Device:** ___
**OS Version:** ___
**App Version:** ___
**Tester:** ___
**Date:** ___

---

## Channel Screen Display

- [ ] **TC-STREAM-001:** Channel manager screen loads with header, title, and subtitle
- [ ] **TC-STREAM-001:** Channel count banner displays correctly
- [ ] **TC-STREAM-001:** Empty state shows when no channels exist

---

## Channel List Loading

- [ ] **TC-STREAM-002:** Loading spinner displays while fetching
- [ ] **TC-STREAM-002:** All backend channels appear in list
- [ ] **TC-STREAM-002:** Channel cards show name, chat ID, stream type, status
- [ ] **TC-STREAM-002:** Channel count matches backend
- [ ] **TC-STREAM-002:** No duplicate channels

---

## Channel Status Display

- [ ] **TC-STREAM-003:** Stopped channels show gray badge with ⏹ icon
- [ ] **TC-STREAM-003:** Running channels show green badge with 📡 icon
- [ ] **TC-STREAM-003:** Starting channels show blue badge with ⏳ icon and spinner
- [ ] **TC-STREAM-003:** Stopping channels show orange badge with ⏳ icon and spinner
- [ ] **TC-STREAM-003:** Error channels show red badge with ⚠️ icon
- [ ] **TC-STREAM-003:** Error messages display below error status
- [ ] **TC-STREAM-003:** Start/Stop buttons show/hide based on status

---

## Start Channel Flow

- [ ] **TC-STREAM-004:** Tapping Start shows confirmation dialog
- [ ] **TC-STREAM-004:** Dialog title is "Start Stream" (translated)
- [ ] **TC-STREAM-004:** Dialog asks to confirm start action
- [ ] **TC-STREAM-004:** Cancel button closes dialog
- [ ] **TC-STREAM-004:** Start button confirms action
- [ ] **TC-STREAM-005:** Start operation completes successfully
- [ ] **TC-STREAM-005:** Success alert displays: "Stream started successfully"
- [ ] **TC-STREAM-005:** Status changes: Stopped → Starting... → Running
- [ ] **TC-STREAM-005:** Status badge changes color and icon correctly
- [ ] **TC-STREAM-005:** Stop button appears after start
- [ ] **TC-STREAM-005:** Start button disappears after start

---

## Stop Channel Flow

- [ ] **TC-STREAM-006:** Tapping Stop shows confirmation dialog
- [ ] **TC-STREAM-006:** Dialog title is "Stop Stream" (translated)
- [ ] **TC-STREAM-006:** Dialog asks to confirm stop action
- [ ] **TC-STREAM-006:** Stop button has destructive (red) style
- [ ] **TC-STREAM-007:** Stop operation completes successfully
- [ ] **TC-STREAM-007:** Success alert displays: "Stream stopped successfully"
- [ ] **TC-STREAM-007:** Status changes: Running → Stopping... → Stopped
- [ ] **TC-STREAM-007:** Status badge changes color and icon correctly
- [ ] **TC-STREAM-007:** Start button appears after stop
- [ ] **TC-STREAM-007:** Stop button disappears after stop

---

## Refresh Functionality

- [ ] **TC-STREAM-008:** Pull-to-refresh works from top of list
- [ ] **TC-STREAM-008:** Refresh spinner displays
- [ ] **TC-STREAM-008:** Channel list updates after refresh
- [ ] **TC-STREAM-008:** Refresh completes within 2-3 seconds
- [ ] **TC-STREAM-009:** Channels auto-refresh during starting/stopping states
- [ ] **TC-STREAM-009:** Auto-refresh happens every 2 seconds
- [ ] **TC-STREAM-009:** Auto-refresh stops when status is stable
- [ ] **TC-STREAM-009:** Status updates automatically without user interaction

---

## Error Handling

- [ ] **TC-STREAM-010:** Error alert displays when start fails
- [ ] **TC-STREAM-010:** Error message is meaningful and descriptive
- [ ] **TC-STREAM-010:** Channel status changes to "Error"
- [ ] **TC-STREAM-010:** Error message displays on channel card
- [ ] **TC-STREAM-010:** Start button remains available for retry
- [ ] **TC-STREAM-010:** No app crash or freeze

---

## Network Scenarios (Optional)

- [ ] **TC-STREAM-011:** Error displays when loading channels with no network
- [ ] **TC-STREAM-011:** Retry works after network restored
- [ ] **TC-STREAM-012:** Error displays when start fails due to network
- [ ] **TC-STREAM-012:** Can retry after network restored

---

## Edge Cases (Optional)

- [ ] **TC-STREAM-013:** Rapid button taps don't cause duplicate operations
- [ ] **TC-STREAM-014:** Multiple channels can start/stop simultaneously
- [ ] **TC-STREAM-015:** Scrolling performance is good with 20+ channels

---

## Test Results Summary

| Category | Total | Passed | Failed | Notes |
|----------|-------|--------|--------|-------|
| Screen Display | 3 | ___ | ___ | |
| Channel List | 5 | ___ | ___ | |
| Status Display | 7 | ___ | ___ | |
| Start Flow | 11 | ___ | ___ | |
| Stop Flow | 11 | ___ | ___ | |
| Refresh | 8 | ___ | ___ | |
| Error Handling | 6 | ___ | ___ | |
| **TOTAL** | **51** | **___** | **___** | |

---

## Overall Result

⬜ **PASS** - All tests passed successfully
⬜ **PASS WITH MINOR ISSUES** - Minor non-blocking issues found
⬜ **FAIL** - Critical or major blocking issues found

---

## Issues Found

### Critical Issues (Blocker)
1.
2.
3.

### Major Issues
1.
2.
3.

### Minor Issues
1.
2.
3.

---

## Notes and Observations

___
___
___

---

## Quick Tips

- Use the test reporter utilities in `src/utils/testHelpers.ts` to automate verification checks
- Record console logs during testing for debugging
- Take screenshots of failures for bug reports
- Test on both iOS and Android if possible
- Verify translations work in different languages
- Check touch targets are 44x44px minimum

---

## Sign-off

**Tester:** ___

**Date:** ___

**Overall Assessment:**
___ ⬜ Approve  ⬜ Approve with Notes  ⬜ Reject

---

**Document Version:** 1.0.0
**Last Updated:** 2026-01-23

**Reference:** [e2e-stream-management-test-plan.md](./e2e-stream-management-test-plan.md) for detailed test steps
