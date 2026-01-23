# Mobile App Submission Documentation

This directory contains comprehensive documentation for building and submitting the Sattva Streamer mobile app to both the Apple App Store (via TestFlight) and Google Play Console.

---

## Table of Contents

- [iOS Documentation](#ios-documentation)
- [Android Documentation](#android-documentation)
- [Shared Documentation](#shared-documentation)
- [Quick Start](#quick-start)
- [Support](#support)

---

## iOS Documentation

### 1. [iOS TestFlight Submission Guide](./ios-testflight-submission-guide.md)
**Complete step-by-step guide** for submitting the iOS app to TestFlight.

**Covers:**
- Prerequisites (Apple Developer account, tools, setup)
- Creating app in App Store Connect
- Configuring EAS Build
- Building iOS app
- Submitting to TestFlight
- Configuring internal testing
- Installing and verifying
- Troubleshooting common issues

**Length**: ~350 lines
**Best for**: First-time submission, detailed walkthrough

---

### 2. [iOS TestFlight Checklist](./ios-testflight-checklist.md)
**Interactive checklist** to track progress through the submission process.

**Includes:**
- Prerequisites checklist
- Step-by-step checkboxes
- Fields for recording IDs and dates
- Issues tracking section
- Sign-off section

**Length**: ~150 lines
**Best for**: Tracking progress, ensuring nothing is missed

---

### 3. [iOS Build Quick Reference](./ios-build-quick-reference.md)
**Quick command reference** for common build and submission tasks.

**Contains:**
- Essential commands (build, submit, monitor)
- Configuration file examples
- Environment variables
- Troubleshooting commands
- Time estimates
- Common parameters

**Length**: ~200 lines
**Best for**: Quick lookup during build process

---

### 4. [iOS Build Preparation Script](../scripts/prepare-ios-build.sh)
**Automated preparation script** that verifies everything is ready for building.

**Features:**
- Checks prerequisites (Node.js, EAS CLI, Expo login)
- Validates project files (app.json, eas.json, assets)
- Runs TypeScript type checking
- Verifies dependencies
- Checks git status
- Prompts to start build when ready

**Usage:**
```bash
cd mobile
./scripts/prepare-ios-build.sh
```

**Length**: ~300 lines
**Best for**: Pre-build verification, catching issues early

---

## Android Documentation

### 1. [Android Google Play Submission Guide](./android-google-play-submission-guide.md)
**Complete step-by-step guide** for submitting the Android app to Google Play.

**Covers:**
- Prerequisites (Google Play Developer account, tools, setup)
- Creating app in Google Play Console
- Configuring app details and assets
- Setting up content rating
- Creating Google Play service account
- Configuring EAS Build for Android
- Building Android app
- Submitting to Google Play (internal testing)
- Configuring testers and opt-in links
- Installing and verifying
- Troubleshooting common issues

**Length**: ~400 lines
**Best for**: First-time submission, detailed walkthrough

---

### 2. [Android Google Play Checklist](./android-google-play-checklist.md)
**Interactive checklist** to track progress through the Android submission process.

**Includes:**
- Prerequisites checklist
- Google Play Console setup checklist
- Service account configuration checklist
- Step-by-step checkboxes
- Fields for recording IDs and dates
- Issues tracking section
- Verification testing checklist
- Sign-off section

**Length**: ~200 lines
**Best for**: Tracking progress, ensuring nothing is missed

---

### 3. [Android Build Quick Reference](./android-build-quick-reference.md)
**Quick command reference** for common Android build and submission tasks.

**Contains:**
- Essential commands (build, submit, monitor)
- Build profiles (development, preview, production)
- Submission tracks (internal, closed, open, production)
- Configuration file examples
- Environment variables
- Troubleshooting commands
- Time estimates
- Resource classes
- Build artifacts (AAB vs APK)

**Length**: ~300 lines
**Best for**: Quick lookup during build process

---

### 4. [Android Build Preparation Script](../scripts/prepare-android-build.sh)
**Automated preparation script** that verifies everything is ready for Android building.

**Features:**
- Checks prerequisites (Node.js, EAS CLI, Expo login)
- Validates project files (app.json, eas.json, assets)
- Validates package name (com.sattva.streamer)
- Checks for Google Play service account key
- Runs TypeScript type checking
- Verifies dependencies
- Checks git status
- Prompts to start build when ready

**Usage:**
```bash
cd mobile
./scripts/prepare-android-build.sh
```

**Length**: ~300 lines
**Best for**: Pre-build verification, catching issues early

---

## Shared Documentation

### 1. [App Store Listing](./app-store-listing.md)
**App store metadata** in all supported languages.

**Contains:**
- App names (EN, RU, UK, DE, ES, JA, ZH)
- Short descriptions (80 characters)
- Full descriptions (4000 characters)
- Keywords for SEO
- Platform-specific notes

**Length**: ~400 lines
**Best for**: Copy-pasting into App Store Connect and Google Play Console

---

### 2. [Privacy Policy](./privacy-policy.md)
**Comprehensive privacy policy** for both app stores.

**Covers:**
- Information collected (credentials, device info, push tokens)
- Data usage (authentication, notifications, offline mode)
- Security measures (encryption, HTTPS, biometric storage)
- Third-party services (Expo, Sentry, APNs, FCM)
- User rights (access, delete, modify, opt-out)
- GDPR/CCPA compliance for EU/California residents
- International data transfers
- Contact information

**Length**: ~300 lines
**Best for**: Uploading to App Store Connect and Google Play Console

---

### 3. [Assets Guide](./ASSETS_GUIDE.md)
**Guidelines for creating app store assets**.

**Includes:**
- Icon requirements (iOS and Android)
- Splash screen requirements
- Screenshot specifications (phone and tablet)
- Design guidelines and best practices
- Tools and workflows
- Asset optimization tips

**Length**: ~150 lines
**Best for**: Creating production-quality assets

---

## Quick Start

### For First-Time iOS Submission

1. **Read the iOS guide** (20 minutes)
   ```bash
   cat docs/ios-testflight-submission-guide.md
   ```

2. **Set up Apple Developer account** (if needed)
   - Enroll at: https://developer.apple.com/programs/enroll/
   - Cost: $99/year
   - Wait for account approval (1-2 days)

3. **Create app in App Store Connect**
   - Follow steps in submission guide, Section 2
   - Note down your Apple ID, ASC App ID, and Team ID

4. **Run iOS preparation script**
   ```bash
   cd mobile
   ./scripts/prepare-ios-build.sh
   ```

5. **Build the iOS app**
   ```bash
   eas build --platform ios --profile production
   ```

6. **Submit to TestFlight**
   - If configured correctly, submission is automatic
   - Otherwise, submit manually via App Store Connect

---

### For First-Time Android Submission

1. **Read the Android guide** (20 minutes)
   ```bash
   cat docs/android-google-play-submission-guide.md
   ```

2. **Set up Google Play Developer account** (if needed)
   - Enroll at: https://play.google.com/console/signup
   - Cost: $25 USD (one-time)
   - Account usually approved immediately

3. **Create app in Google Play Console**
   - Follow steps in submission guide, Section 2
   - Package name: com.sattva.streamer

4. **Configure Google Play service account**
   - Link Google Cloud project
   - Create service account with Release Manager role
   - Generate JSON key
   - Place in: `mobile/google-service-account-key.json`

5. **Run Android preparation script**
   ```bash
   cd mobile
   ./scripts/prepare-android-build.sh
   ```

6. **Build the Android app**
   ```bash
   eas build --platform android --profile production
   ```

7. **Submit to internal testing**
   - If service account key is configured: automatic
   - Otherwise: upload AAB manually to Google Play Console

---

### For Experienced Users

If you've submitted before, you can skip the guides and use the quick references:

**iOS:**
```bash
# Run prep script
./scripts/prepare-ios-build.sh

# Build
eas build --platform ios --profile production

# Monitor
eas build:list --platform ios
```

**Android:**
```bash
# Run prep script
./scripts/prepare-android-build.sh

# Build
eas build --platform android --profile production

# Monitor
eas build:list --platform android
```

---

## Time Estimates

### iOS (TestFlight)

| Task | Time | Notes |
|------|------|-------|
| Read documentation | 20-30 min | First time only |
| Apple Developer enrollment | 1-2 days | One-time, wait for approval |
| Create app in App Store Connect | 10 min | One-time |
| Configure EAS Build | 5 min | Each build |
| Run preparation script | 2 min | Each build |
| Build iOS app | 20-30 min | First build slower |
| Submit to TestFlight | Automatic | If configured |
| Configure internal testing | 10 min | Each submission |
| Install and verify | 10 min | Each submission |
| **Total (first time)** | **~2-3 hours** | Excluding enrollment wait |
| **Total (subsequent)** | **~45-60 min** | Mostly build time |

### Android (Google Play)

| Task | Time | Notes |
|------|------|-------|
| Read documentation | 20-30 min | First time only |
| Google Play Developer registration | Immediate | One-time $25 fee |
| Create app in Google Play Console | 10 min | One-time |
| Configure service account | 15 min | One-time |
| Run preparation script | 2 min | Each build |
| Build Android app | 20-30 min | First build slower |
| Submit to internal testing | Automatic | If service account configured |
| Configure testers | 5 min | Each submission |
| Install and verify | 10 min | Each submission |
| **Total (first time)** | **~1-2 hours** | All setup included |
| **Total (subsequent)** | **~30-45 min** | Mostly build time |

---

## Common Tasks

### Check build status
```bash
# iOS
eas build:list --platform ios --profile production

# Android
eas build:list --platform android --profile production
```

### View specific build
```bash
eas build:view [BUILD_ID]
```

### Cancel a build
```bash
eas build:cancel [BUILD_ID]
```

### Submit existing build
```bash
# iOS
eas submit --platform ios --profile production --build-id [BUILD_ID]

# Android
eas submit --platform android --profile production --build-id [BUILD_ID]
```

---

## Troubleshooting

### Common iOS Issues

**Build fails with certificate errors**
- **Cause**: Bundle ID mismatch or incorrect team ID
- **Solution**: Verify bundle ID in `app.json` matches App Store Connect
- **Solution**: Check team ID in `eas.json` is correct

**Build not appearing in TestFlight**
- **Cause**: ASC App ID incorrect or build failed
- **Solution**: Verify ASC App ID in `eas.json`
- **Solution**: Check build status: `eas build:list`

**Testers can't install**
- **Cause**: Invitation expired or device incompatible
- **Solution**: Resend invitation from App Store Connect
- **Solution**: Check device meets minimum iOS version (13.0+)

### Common Android Issues

**Build fails with "Package name mismatch"**
- **Cause**: Package name in `app.json` doesn't match Google Play Console
- **Solution**: Verify `android.package` is `com.sattva.streamer` in both places

**Submission fails with "Service account authentication failed"**
- **Cause**: Service account key is invalid or missing
- **Solution**: Verify `google-service-account-key.json` exists and is valid JSON
- **Solution**: Check service account has Release Manager role

**App not appearing in internal testing**
- **Cause**: Release not properly created or configured
- **Solution**: Navigate to: Release → Testing → Internal testing
- **Solution**: Verify there's an active release

---

## Related Resources

### Official Documentation
- [EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [EAS Submit Documentation](https://docs.expo.dev/submit/introduction/)
- [TestFlight Documentation](https://developer.apple.com/testflight/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Google Play Console Help](https://support.google.com/googleplay/android-developer)
- [Google Play Best Practices](https://developer.android.com/distribute/best-practices)

### Project Files
- `eas.json` - EAS build configuration
- `app.json` - Expo app configuration
- `package.json` - Dependencies and scripts
- `google-service-account-key.json` - Google Play service account key (never commit)

### Previous Subtasks
- **Subtask 6-1**: Configure EAS Build for iOS and Android
- **Subtask 6-2**: Create app store assets (icons, splash screens, screenshots)
- **Subtask 6-3**: Create app store listings (descriptions, privacy policy)
- **Subtask 6-4**: Build and submit iOS app to TestFlight
- **Subtask 6-5**: Build and submit Android app to Google Play

---

## Support

### Getting Help
1. Check the troubleshooting section in the relevant submission guide
2. Search Expo forums: https://forums.expo.dev/
3. Check EAS Build status: https://status.expo.dev/
4. Review build logs in EAS dashboard
5. For iOS: Check Apple Developer forums
6. For Android: Check Google Play Developer Community

### Reporting Issues
When reporting issues, include:
- EAS CLI version: `eas --version`
- Build ID: From build URL
- Platform: iOS or Android
- Error message: Full error text
- Build logs: From EAS dashboard

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-01-23 | Added Android Google Play submission documentation |
| 1.0 | 2026-01-23 | Initial documentation for TestFlight submission |

---

## Checklist Status

### iOS
- [ ] Read iOS documentation
- [ ] Apple Developer account active
- [ ] App created in App Store Connect
- [ ] EAS Build configured for iOS
- [ ] iOS preparation script passed
- [ ] iOS app built successfully
- [ ] Submitted to TestFlight
- [ ] Internal testing configured
- [ ] App installed and verified on iOS device
- [ ] iOS checklist completed

### Android
- [ ] Read Android documentation
- [ ] Google Play Developer account active
- [ ] App created in Google Play Console
- [ ] Service account configured
- [ ] EAS Build configured for Android
- [ ] Android preparation script passed
- [ ] Android app built successfully
- [ ] Submitted to internal testing
- [ ] Testers added and opt-in link shared
- [ ] App installed and verified on Android device
- [ ] Android checklist completed

---

**Last Updated**: 2026-01-23
**Status**: Ready for Implementation
