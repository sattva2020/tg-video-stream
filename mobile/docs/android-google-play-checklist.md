# Android Google Play Submission Checklist

Use this checklist to track your progress through the Android Google Play submission process.

**Instructions:**
- Check each box as you complete the step
- Fill in IDs, dates, and notes where prompted
- Review completed checklist before submitting for production

---

## Section 1: Prerequisites

- [ ] **Google Play Developer Account Created**
  - Registration fee: $25 USD
  - Account email: ___________________
  - Account approved: Yes / No
  - Notes: _____________________________

- [ ] **EAS CLI Installed**
  - Version: ___________________
  - Verified with: `eas --version`
  - Notes: _____________________________

- [ ] **Logged into Expo**
  - Username: ___________________
  - Verified with: `eas whoami`
  - Notes: _____________________________

---

## Section 2: Google Play Console Setup

- [ ] **App Created in Google Play Console**
  - App name: Sattva Streamer
  - Package name: com.sattva.streamer
  - App created on: ___________________
  - App ID: ___________________
  - Notes: _____________________________

- [ ] **App Details Configured**
  - App name: Sattva Streamer
  - Short description (80 chars): ✅
  - Full description (4000 chars): ✅
  - Languages configured:
    - [ ] EN (English)
    - [ ] RU (Russian)
    - [ ] UK (Ukrainian)
    - [ ] DE (German)
    - [ ] ES (Spanish)
    - [ ] JA (Japanese)
    - [ ] ZH (Chinese)
  - Notes: _____________________________

- [ ] **App Assets Uploaded**
  - App icon (512x512): ✅
  - Feature graphic (1024x500): ✅
  - Phone screenshots (2+): ✅
  - Tablet screenshots (optional): ✅
  - Notes: _____________________________

- [ ] **Content Rating Completed**
  - Questionnaire completed: Yes / No
  - Rating received: ___________________
  - Notes: _____________________________

- [ ] **Privacy Policy Configured**
  - Privacy policy URL: ___________________
  - Hosted on: ___________________
  - Copied from: `docs/privacy-policy.md`
  - Notes: _____________________________

- [ ] **App Access Configured**
  - Access level: Internal Testing
  - No additional verification required: ✅
  - Notes: _____________________________

---

## Section 3: EAS Build Configuration

- [ ] **eas.json Configured**
  - Build profiles verified: ✅
  - Android build configuration: ✅
  - Notes: _____________________________

- [ ] **Google Cloud Project Linked**
  - Project linked in Google Play Console: ✅
  - Project name: ___________________
  - Project ID: ___________________
  - Notes: _____________________________

- [ ] **Service Account Created**
  - Service account name: eas-submit
  - Roles granted: Release Manager
  - Created on: ___________________
  - Service account email: ___________________
  - Notes: _____________________________

- [ ] **Service Account Key Generated**
  - Key type: JSON
  - Generated on: ___________________
  - Key file location: mobile/google-service-account-key.json
  - Key added to .gitignore: ✅
  - Notes: _____________________________

- [ ] **eas.json Updated with Service Account**
  - serviceAccountKeyPath: ./google-service-account-key.json
  - track: internal
  - JSON valid: ✅
  - Notes: _____________________________

---

## Section 4: Build Preparation

- [ ] **Ran Preparation Script**
  - Script: `./scripts/prepare-android-build.sh`
  - Date: ___________________
  - Result: Passed / Failed
  - Issues found: ___________________
  - Issues fixed: ✅
  - Notes: _____________________________

- [ ] **TypeScript Check Passed**
  - Command: `npx tsc --noEmit`
  - Result: No errors
  - Notes: _____________________________

- [ ] **Dependencies Installed**
  - node_modules exists: ✅
  - npm install completed: ✅
  - Notes: _____________________________

- [ ] **Git Status Checked**
  - Working directory clean: Yes / No
  - Committed changes before building: ✅
  - Notes: _____________________________

---

## Section 5: Build Android App

- [ ] **Build Started**
  - Command: `eas build --platform android --profile production`
  - Start time: ___________________
  - Build ID: ___________________
  - Build URL: ___________________
  - Notes: _____________________________

- [ ] **Build Monitored**
  - Build completed successfully: ✅
  - Completion time: ___________________
  - Build duration: ___________________
  - Artifact downloaded: ✅
  - Notes: _____________________________

- [ ] **Build Verified**
  - File type: .aab
  - File size: ___________________ MB
  - File not corrupted: ✅
  - Notes: _____________________________

---

## Section 6: Submit to Google Play

- [ ] **Submission Completed**
  - Submission method: Automatic / Manual
  - Submission date: ___________________
  - Submission successful: ✅
  - Notes: _____________________________

- [ ] **Release Created in Internal Testing**
  - Release name: ___________________
  - Release version: ___________________
  - Release notes added: ✅
  - Notes: _____________________________

---

## Section 7: Internal Testing Setup

- [ ] **Testers Added**
  - Number of testers: ___________________
  - Tester emails:
    - ___________________
    - ___________________
    - ___________________
  - Notes: _____________________________

- [ ] **Opt-In Link Generated**
  - Opt-in URL: ___________________
  - Link tested: ✅
  - Link shared with testers: ✅
  - Notes: _____________________________

- [ ] **Release Notes Published**
  - Release notes added: ✅
  - Notes describe changes: ✅
  - Feedback contact included: ✅
  - Notes: _____________________________

---

## Section 8: Installation and Verification

- [ ] **App Installed on Test Device**
  - Device model: ___________________
  - Android version: ___________________
  - Installation method: Opt-in link / Play Console
  - Installation successful: ✅
  - Notes: _____________________________

- [ ] **Basic Functionality Tested**
  - [ ] App launches successfully
  - [ ] Login screen appears
  - [ ] Can login with email/password
  - [ ] Dashboard loads
  - [ ] Navigation works
  - Issues found: ___________________
  - Notes: _____________________________

- [ ] **Stream Management Tested**
  - [ ] Channel list loads
  - [ ] Can start stream
  - [ ] Can stop stream
  - [ ] Status updates correctly
  - Issues found: ___________________
  - Notes: _____________________________

- [ ] **Push Notifications Tested**
  - [ ] Notification permissions granted
  - [ ] Test notification received
  - [ ] Tapping notification opens app
  - [ ] Navigation to correct screen works
  - Issues found: ___________________
  - Notes: _____________________________

- [ ] **Offline Mode Tested**
  - [ ] Airplane mode enabled
  - [ ] Configuration change saved locally
  - [ ] Changes synced when online
  - [ ] Sync indicator shows success
  - Issues found: ___________________
  - Notes: _____________________________

- [ ] **Localization Tested**
  - [ ] Language changed in device settings
  - [ ] App UI updates to new language
  - [ ] No missing translation keys
  - Languages tested:
    - [ ] EN
    - [ ] RU
    - [ ] UK
    - [ ] DE
    - [ ] ES
    - [ ] JA
    - [ ] ZH
  - Issues found: ___________________
  - Notes: _____________________________

- [ ] **Biometric Authentication Tested**
  - [ ] Login with email/password successful
  - [ ] Biometric prompt appears
  - [ ] Can enable biometric
  - [ ] Biometric login works on subsequent launches
  - Issues found: ___________________
  - Notes: _____________________________

---

## Section 9: Feedback and Iteration

- [ ] **Tester Feedback Collected**
  - Number of testers responded: ___________________
  - Issues reported: ___________________
  - Feature requests: ___________________
  - Overall satisfaction: ___________________
  - Notes: _____________________________

- [ ] **Critical Issues Fixed**
  - Issues identified: ___________________
  - Fixes implemented: ✅
  - New build created: ✅
  - Build version: ___________________
  - Notes: _____________________________

- [ ] **App Quality Verified**
  - No crashes: ✅
  - No major bugs: ✅
  - Performance acceptable: ✅
  - UI/UX polished: ✅
  - Notes: _____________________________

---

## Section 10: Ready for Next Phase

- [ ] **Internal Testing Complete**
  - All testers satisfied: ✅
  - Critical issues resolved: ✅
  - Notes: _____________________________

- [ ] **Decided on Next Steps**
  - [ ] Move to closed testing (up to 2000 testers)
  - [ ] Move to open testing (public opt-in)
  - [ ] Submit for production release
  - Decision: ___________________
  - Timeline: ___________________
  - Notes: _____________________________

---

## Sign-Off

**Completed by:** ___________________
**Role:** ___________________
**Date:** ___________________

**Internal Testing Status:**
- [ ] Approved for next phase
- [ ] Needs additional testing
- [ ] Needs critical fixes

**Comments:**
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

**Approved by:** ___________________
**Role:** ___________________
**Date:** ___________________

---

## Progress Summary

**Total Sections:** 10
**Sections Completed:** _____ / 10
**Completion Percentage:** _____ %

**Estimated Time to Complete:**
- First-time setup: 1-2 hours
- Subsequent submissions: 30-45 minutes

**Current Status:**
- [ ] Not Started
- [ ] In Progress
- [ ] Completed
- [ ] Ready for Next Phase

---

## Issues Tracking

### Issue #1
- **Description:** ___________________
- **Severity:** Low / Medium / High
- **Status:** Open / In Progress / Resolved
- **Resolution:** ___________________
- **Date Resolved:** ___________________

### Issue #2
- **Description:** ___________________
- **Severity:** Low / Medium / High
- **Status:** Open / In Progress / Resolved
- **Resolution:** ___________________
- **Date Resolved:** ___________________

### Issue #3
- **Description:** ___________________
- **Severity:** Low / Medium / High
- **Status:** Open / In Progress / Resolved
- **Resolution:** ___________________
- **Date Resolved:** ___________________

---

## Quick Reference

**Essential Commands:**
```bash
# Build
eas build --platform android --profile production

# Submit
eas submit --platform android --profile production

# List builds
eas build:list --platform android

# View build
eas build:view BUILD_ID
```

**Important Links:**
- Google Play Console: https://play.google.com/console
- EAS Dashboard: https://expo.dev
- Submission Guide: `docs/android-google-play-submission-guide.md`

---

**Last Updated:** 2026-01-23
**Version:** 1.0
**Next Review:** After completion of internal testing
