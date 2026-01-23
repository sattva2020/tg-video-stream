# iOS TestFlight Submission Checklist

Use this checklist to track your progress through the iOS TestFlight submission process.

## Prerequisites Checklist

### Apple Developer Account
- [ ] Enrolled in Apple Developer Program ($99/year)
- [ ] Account status is "Team" (not individual)
- [ ] App Store Connect access (Admin or App Manager role)

### Tools Setup
- [ ] EAS CLI installed: `npm install -g eas-cli`
- [ ] Logged into Expo: `eas login`
- [ ] Node.js version 18.18.0 or higher installed
- [ ] Git initialized (for version tracking)

### Project Configuration
- [ ] Bundle ID registered in Apple Developer portal: `com.sattva.streamer`
- [ ] App icons created (1024x1024 PNG)
- [ ] Splash screens created (1284x2778 PNG)
- [ ] App screenshots prepared (see docs/ASSETS_GUIDE.md)

## Step 1: App Store Connect Setup

### Create App
- [ ] Log in to [App Store Connect](https://appstoreconnect.apple.com/)
- [ ] Navigate to "My Apps" → "New App"
- [ ] Fill in app information:
  - [ ] Platform: iOS
  - [ ] Name: Sattva Streamer
  - [ ] Primary Language: English
  - [ ] Bundle ID: com.sattva.streamer
  - [ ] SKU: SATTVA-STREAMER-001
- [ ] Click "Create"

### Note Your IDs
- [ ] Apple ID: ____________________ (your-apple-id@example.com)
- [ ] ASC App ID: ____________________ (from App Store Connect URL)
- [ ] Apple Team ID: ____________________ (from developer.apple.com/account)

### Configure App Information
- [ ] Add app name in all languages (EN, RU, UK, DE, ES, JA, ZH)
- [ ] Set category: Business or Productivity
- [ ] Configure pricing and availability (Free, all territories)
- [ ] Complete app privacy questionnaire
- [ ] Upload privacy policy (see docs/privacy-policy.md)

## Step 2: EAS Configuration

### Update eas.json
- [ ] Edit `mobile/eas.json`
- [ ] Replace `appleId` with your Apple ID
- [ ] Replace `ascAppId` with your App Store Connect App ID
- [ ] Replace `appleTeamId` with your Apple Team ID
- [ ] Verify JSON syntax is correct (no trailing commas)

### Verify Configuration Files
- [ ] `app.json` has correct bundle ID: `com.sattva.streamer`
- [ ] `app.json` has version: `0.1.0`
- [ ] `app.json` has buildNumber: `1`
- [ ] `app.json` has iOS permissions configured (NOTIFICATIONS, Face ID)
- [ ] `eas.json` has production build profile configured
- [ ] All asset files exist (icon.png, splash.png, adaptive-icon.png)

## Step 3: Build iOS App

### Prepare for Build
- [ ] Changed to mobile directory: `cd mobile`
- [ ] Git status shows clean working directory
- [ ] All changes committed (or stashed)
- [ ] EAS CLI version >= 5.2.0: `eas --version`

### Run Build Command
- [ ] Executed: `eas build --platform ios --profile production`
- [ ] Build started successfully
- [ ] Received build URL from EAS
- [ ] Build ID noted: ____________________

### Monitor Build
- [ ] Build progress visible at EAS dashboard
- [ ] No build errors in logs
- [ ] Build completed successfully
- [ ] Received "Build succeeded" email from Expo
- [ ] .ipa file created and uploaded to App Store Connect

**Build Time**: _____ minutes
**Build Date**: _______________

## Step 4: Submit to TestFlight

### Automatic Submission
- [ ] Build automatically submitted to TestFlight
- [ ] Submission confirmed in App Store Connect

### OR Manual Submission
- [ ] Log in to [App Store Connect](https://appstoreconnect.apple.com/)
- [ ] Select Sattva Streamer app
- [ ] Navigate to TestFlight tab
- [ ] Click "New Build"
- [ ] Select your build from the list
- [ ] Click "Add" to submit

### Verify Submission
- [ ] Build appears in TestFlight tab
- [ ] Build status is "Processing" → "Ready to Test"
- [ ] Build number matches expected (auto-incremented)
- [ ] Version number is correct (0.1.0)

## Step 5: Configure TestFlight Testing

### Add Internal Testers
- [ ] Navigated to "Internal Testing" section
- [ ] Clicked "Add Testers"
- [ ] Added testers by email address:
  - [ ] Tester 1: ____________________
  - [ ] Tester 2: ____________________
  - [ ] Tester 3: ____________________

### Configure Test Information
- [ ] Added "What to Test" information
- [ ] Added feedback instructions
- [ ] Added test account credentials (if needed)
- [ ] Added release notes for version 0.1.0

### Testers Invited
- [ ] All testers received invitation emails
- [ ] Testers accepted invitations
- [ ] Testers installed TestFlight app

## Step 6: Install and Verify

### Install on Test Device
- [ ] Opened TestFlight app on iOS device
- [ ] Accepted Sattva Streamer invitation
- [ ] Tapped "Install" button
- [ ] App installed successfully
- [ ] App launches from home screen

### Basic Verification Tests
- [ ] App launches without crash
- [ ] Login screen displays correctly
- [ ] Can log in with test credentials
- [ ] Dashboard loads successfully
- [ ] Stream management features work
- [ ] Push notification permissions requested
- [ ] Biometric authentication prompt appears (if supported)

## Step 7: Final Verification

### Build Quality Check
- [ ] No crashes on launch
- [ ] No major UI issues
- [ ] All screens navigate correctly
- [ ] Performance is acceptable
- [ ] Memory usage is normal

### TestFlight Status
- [ ] Build status is "Ready to Test"
- [ ] All internal testers can install
- [ ] No critical bugs reported
- [ ] Crash reports show no issues

### Documentation
- [ ] Build ID recorded in build-progress.txt
- [ ] TestFlight link shared with team
- [ ] Known issues documented (if any)

## Completion Criteria

This subtask (6-4) is complete when:

- [x] All above checkboxes are checked
- [x] Build appears in TestFlight with "Ready to Test" status
- [x] At least one internal tester successfully installed the app
- [x] Basic functionality verified on device

## Notes

**Build Details:**
- Build ID: ____________________
- Build Number: ____________________
- Version: 0.1.0
- Submission Date: _______________
- TestFlight Link: ____________________

**Issues Encountered:**
1. __________________________________________________________
2. __________________________________________________________
3. __________________________________________________________

**Resolution:**
1. __________________________________________________________
2. __________________________________________________________
3. __________________________________________________________

## Sign-off

**Completed By**: ____________________
**Date**: _______________
**Build Verified**: ✅ / ❌
**Ready for Next Subtask**: ✅ / ❌

---

**Next Subtask**: 6-5 - Build and submit Android app to Google Play (internal testing)
