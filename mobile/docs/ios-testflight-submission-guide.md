# iOS TestFlight Submission Guide

This guide walks you through building and submitting the Sattva Streamer mobile app to TestFlight for internal testing.

## Prerequisites

Before you begin, ensure you have:

1. **Apple Developer Account** ($99/year)
   - Enroll at [https://developer.apple.com/programs/enroll/](https://developer.apple.com/programs/enroll/)
   - Account must be in "Team" status (not individual)

2. **App Store Connect Access**
   - Log in to [https://appstoreconnect.apple.com/](https://appstoreconnect.apple.com/)
   - Verify you have Admin or App Manager role

3. **EAS CLI Installed**
   ```bash
   npm install -g eas-cli
   ```

4. **Expo Account**
   - Create account at [https://expo.dev/](https://expo.dev/)
   - Link your Expo project: `eas login`

## Step 1: Configure App Store Connect

### 1.1 Create App in App Store Connect

1. Go to [App Store Connect](https://appstoreconnect.apple.com/)
2. Click **"My Apps"** → **"Plus (+)"** → **"New App"**
3. Fill in the app information:
   - **Platform**: iOS
   - **Name**: Sattva Streamer
   - **Primary Language**: English
   - **Bundle ID**: com.sattva.streamer
   - **SKU**: SATTVA-STREAMER-001
4. Click **"Create"**

### 1.2 Configure App Information

In App Store Connect, navigate to:

1. **App Information** tab:
   - Add app name in all supported languages (EN, RU, UK, DE, ES, JA, ZH)
   - See `docs/app-store-listing.md` for translated content
   - Category: **Business** or **Productivity**
   - Content Rights: **Contains third-party content**

2. **Pricing and Availability**:
   - Price: **Free**
   - Availability: **All territories**

3. **App Privacy**:
   - Complete the privacy questionnaire
   - See `docs/privacy-policy.md` for details

### 1.3 Note Your App IDs

After creating the app, note down:
- **Apple ID**: Your Apple ID email
- **ASC App ID**: Found in App Store Connect URL (e.g., `https://appstoreconnect.apple.com/apps/XXXXXXXXX`)
- **Apple Team ID**: Found in [Membership Details](https://developer.apple.com/account/)

## Step 2: Configure EAS Build

### 2.1 Update eas.json with Your Credentials

Edit `mobile/eas.json` and replace the placeholder values:

```json
{
  "submit": {
    "production": {
      "ios": {
        "appleId": "your-apple-id@example.com",      // YOUR Apple ID
        "ascAppId": "YOUR_APP_STORE_CONNECT_APP_ID", // From App Store Connect URL
        "appleTeamId": "YOUR_APPLE_TEAM_ID"          // From developer.apple.com/account
      }
    }
  }
}
```

### 2.2 Verify Build Configuration

Check that `mobile/eas.json` has the correct iOS build profile:

```json
{
  "build": {
    "production": {
      "distribution": "store",
      "ios": {
        "autoIncrement": true,
        "resourceClass": "m-medium"
      }
    }
  }
}
```

### 2.3 Verify app.json Configuration

Ensure `mobile/app.json` has:

- ✅ Bundle identifier: `com.sattva.streamer`
- ✅ iOS version: `buildNumber: "1"`
- ✅ App version: `version: "0.1.0"`
- ✅ Permissions configured (NOTIFICATIONS, Face ID)
- ✅ App icons and splash screens

## Step 3: Build iOS App for App Store

### 3.1 Build for Production

Run the EAS build command:

```bash
cd mobile
eas build --platform ios --profile production
```

**What happens:**
- EAS will upload your project to Expo's build servers
- Build typically takes 20-30 minutes
- You'll receive an email when build completes
- Build URL will be provided (e.g., `https://expo.dev/artifacts/...`)

**Build output:**
- `.ipa` file (iOS app binary)
- Automatically uploaded to App Store Connect if credentials are correct

### 3.2 Monitor Build Progress

Watch the build in real-time:
- Visit the build URL provided
- Check build logs for errors
- Common issues:
  - Missing certificates (EAS creates automatically)
  - Bundle ID mismatch (verify in app.json)
  - Provisioning profile issues (check team permissions)

## Step 4: Submit to TestFlight

### 4.1 Automatic Submission (Recommended)

If `eas.json` is configured correctly, the build will automatically submit to TestFlight.

Check submission status:
```bash
eas submit --platform ios --profile production --non-interactive
```

### 4.2 Manual Submission (Alternative)

If automatic submission fails, submit manually:

1. Go to [App Store Connect](https://appstoreconnect.apple.com/)
2. Select **Sattva Streamer** app
3. Click **"TestFlight"** tab
4. Click **"Plus (+)"** → **"New Build"**
5. Select your build from the list
6. Click **"Add"** to upload to TestFlight

## Step 5: Configure TestFlight Testing

### 5.1 Add Internal Testers

1. In TestFlight tab, click **"Internal Testing"**
2. Click **"Plus (+)"** → **"Add Testers"**
3. Add testers by:
   - Email address (must be in your Apple Developer team)
   - Or import from CSV

### 5.2 Configure Test Information

1. Click **"Test Information"**
2. Add:
   - **What to Test**: Key features to test (streaming, push notifications, biometric auth)
   - **Feedback**: How to provide feedback (email, GitHub issues)
   - **Login Credentials**: Test account credentials if needed

3. Add release notes:
   ```markdown
   ## Version 0.1.0 - Internal Testing

   ### Features
   - Complete stream management (start, stop, restart channels)
   - Real-time dashboard with stream status
   - Push notifications for stream alerts
   - Biometric authentication (Face ID, Touch ID)
   - Offline mode with automatic sync
   - Multilingual support (EN, RU, UK, DE, ES, JA, ZH)

   ### Testing Focus
   - Authentication flows (login, biometric, logout)
   - Stream management operations
   - Push notification delivery
   - Offline mode sync
   - Localization across all languages

   ### Known Issues
   - None (please report any issues found)
   ```

## Step 6: Install and Test

### 6.1 Install TestFlight App

1. Testers install **TestFlight** from App Store
2. Open TestFlight app
3. Accept invitation to test Sattva Streamer

### 6.2 Install Test Build

1. In TestFlight, tap **Sattva Streamer**
2. Tap **"Install"** button
3. Wait for installation to complete
4. Launch app from home screen

### 6.3 Verify Installation

Test basic functionality:
- ✅ App launches successfully
- ✅ Login screen displays
- ✅ Can log in with test credentials
- ✅ Dashboard loads
- ✅ Push notification permissions requested

## Step 7: Verify Build in TestFlight

### 7.1 Check Build Status

In App Store Connect:
1. Go to **TestFlight** tab
2. Verify build status is **"Processing"** → **"Ready to Test"**
3. Check build number and version

### 7.2 Test Build Quality

Before expanding testing:
1. Install on at least 2 iOS devices
2. Test all core features
3. Verify no crashes on launch
4. Check push notifications work
5. Test biometric authentication

### 7.3 Monitor Crashes and Analytics

1. Enable TestFlight analytics
2. Monitor crash reports in Xcode Organizer
3. Review tester feedback
4. Fix critical issues before public beta

## Troubleshooting

### Build Fails

**Issue**: Build fails with certificate errors
- **Solution**: Ensure bundle ID matches App Store Connect
- **Solution**: Verify Apple Team ID is correct

**Issue**: Build fails with provisioning profile errors
- **Solution**: Check team permissions in Apple Developer portal
- **Solution**: Ensure user has "Admin" or "App Manager" role

### Submission Fails

**Issue**: Build not appearing in TestFlight
- **Solution**: Check ASC App ID is correct in eas.json
- **Solution**: Verify build completed successfully
- **Solution**: Try manual submission via App Store Connect

**Issue**: "Invalid Bundle" error
- **Solution**: Verify info.plist permissions are correct
- **Solution**: Check app icons meet Apple guidelines (1024x1024)
- **Solution**: Ensure all screenshots are provided

### Testers Can't Install

**Issue**: "TestFlight invitation expired"
- **Solution**: Resend invitation from App Store Connect
- **Solution**: Verify tester's email is correct

**Issue**: "Build not compatible with device"
- **Solution**: Check minimum iOS version (iOS 13.0+)
- **Solution**: Ensure tester's device is supported

## Verification Checklist

Before marking this subtask complete, verify:

- [ ] App created in App Store Connect
- [ ] Bundle ID matches (com.sattva.streamer)
- [ ] EAS build completed successfully
- [ ] Build appears in TestFlight
- [ ] Build status is "Ready to Test"
- [ ] Internal testers added
- [ ] Test information configured
- [ ] App installs on test device via TestFlight
- [ ] Basic functionality verified (login, dashboard, streams)

## Next Steps

After successful TestFlight submission:

1. **Subtask 6-5**: Build and submit Android app to Google Play
2. **Phase 7**: Integration & End-to-End Testing
3. **Public Beta**: Expand testing to external testers
4. **App Store Submission**: Submit for public review

## Additional Resources

- [EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [TestFlight Documentation](https://developer.apple.com/testflight/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)

## Support

If you encounter issues:

1. Check Expo forums: [https://forums.expo.dev/](https://forums.expo.dev/)
2. Check EAS Build status: [https://status.expo.dev/](https://status.expo.dev/)
3. Review build logs in EAS dashboard
4. Contact Apple Developer Support

## Quick Reference Commands

```bash
# Build iOS app for production
eas build --platform ios --profile production

# Build and submit in one command
eas build --platform ios --profile production --auto-submit

# Submit existing build
eas submit --platform ios --profile production --non-interactive

# Check build status
eas build:list

# View build details
eas build:view [BUILD_ID]

# Cancel a build
eas build:cancel [BUILD_ID]
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-23
**Status**: Ready for Implementation
