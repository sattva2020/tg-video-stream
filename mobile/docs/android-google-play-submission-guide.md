# Android Google Play Submission Guide

This guide walks you through the complete process of building and submitting the Sattva Streamer Android app to Google Play Console for internal testing.

**Time Estimate:**
- First-time setup: 1-2 hours
- Subsequent submissions: 30-45 minutes

**Prerequisites:**
- Google Play Developer account ($25 one-time fee)
- EAS CLI installed
- Expo account

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Google Play Console Setup](#2-google-play-console-setup)
3. [Configure EAS Build](#3-configure-eas-build)
4. [Build Android App](#4-build-android-app)
5. [Submit to Google Play](#5-submit-to-google-play)
6. [Configure Internal Testing](#6-configure-internal-testing)
7. [Install and Verify](#7-install-and-verify)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### 1.1 Google Play Developer Account

**Required:** A Google Play Developer account to publish apps.

**Enrollment:**
1. Visit: https://play.google.com/console/signup
2. Pay the $25 USD one-time registration fee
3. Wait for account approval (usually immediate, sometimes 1-2 days)

**Account Details Needed:**
- Developer name: Displayed in Play Store
- Email address: For notifications
- Phone number: For verification

**Cost:** $25 USD (one-time, lifetime access)

---

### 1.2 Install EAS CLI

If you haven't already installed EAS CLI:

```bash
npm install -g eas-cli
```

**Verify installation:**
```bash
eas --version
```

Expected output: `eas-cli/X.Y.Z`

---

### 1.3 Login to Expo

You must be logged into Expo to build.

```bash
eas login
```

Follow the prompts to login or create an Expo account.

**Verify login:**
```bash
eas whoami
```

Expected output: Your username/email

---

## 2. Google Play Console Setup

### 2.1 Create New App

1. Visit: https://play.google.com/console
2. Click **"Create App"**
3. Fill in app details:
   - **App name**: Sattva Streamer
   - **Package name**: com.sattva.streamer (must match `app.json`)
   - **App language**: English (or your primary language)
   - **Free or Paid**: Free
   - **Is this an app or a game?**: App

4. Click **"Create app"**

**Note:** The package name MUST match `android.package` in `app.json`. If they don't match, the build will fail.

---

### 2.2 Configure App Details

Navigate to: **Setup → App details**

**Required Information:**

1. **App name**: Sattva Streamer
2. **Short description**: 80 characters max
3. **Full description**: 4000 characters max
   - Copy from: `docs/app-store-listing.md`
4. **App icon**: 512x512 PNG (use `assets/icon.png`)
5. **Feature graphic**: 1024x500 PNG (create from splash or use solid color with logo)
6. **Phone screenshots**: At least 2 screenshots, minimum 320px w/h
   - Place in: `screenshots/android/phone/`
   - Sizes: 320px - 3840px width or height
7. **Tablet screenshots** (optional but recommended): Same as phone

**Copy Translations:**
The app store listing in `docs/app-store-listing.md` includes translations for:
- EN (English)
- RU (Russian)
- UK (Ukrainian)
- DE (German)
- ES (Spanish)
- JA (Japanese)
- ZH (Chinese)

Add each language in Google Play Console:

1. Navigate to: **Setup → Store presence → Store listing**
2. Click **"Add translation"**
3. Select language
4. Paste title, short description, full description
5. Save

---

### 2.3 Content Rating

Navigate to: **Setup → Content rating**

1. Complete the content rating questionnaire
2. Select appropriate rating for your app
3. **Typical rating for streaming app:** Everyone (or Teen if social features)

**Questionnaire Tips:**
- **Violence**: None
- **Sexual content**: None
- **Profanity**: None
- **Drug use**: None
- **User-generated content**: Yes (if users can create playlists)
- **Social interaction**: Yes (if app has sharing features)

---

### 2.4 Privacy Policy

Navigate to: **Setup → Privacy**

**Required:** A privacy policy URL.

**Options:**
1. Host on your website (recommended)
2. Use a free privacy policy hosting service
3. Copy from: `docs/privacy-policy.md`

**Steps:**
1. Host the privacy policy file somewhere accessible
2. Paste the URL in the **Privacy Policy URL** field
3. Save

---

### 2.5 App Access

Navigate to: **Setup → App access**

**For Internal Testing:**
- No special access requirements
- Anyone with the opt-in link can install

**For Closed/Open Testing (later):**
- You may need to complete additional verification
- Follow Google's prompts

---

## 3. Configure EAS Build

### 3.1 Update `eas.json`

The `eas.json` file should have Android build configuration. Update the `submit.production.android` section with your credentials.

**Edit:** `mobile/eas.json`

```json
{
  "submit": {
    "production": {
      "android": {
        "serviceAccountKeyPath": "./google-service-account-key.json",
        "track": "internal"
      }
    }
  }
}
```

---

### 3.2 Create Google Play Service Account Key

**Required for automatic submission:** A service account key that allows EAS to upload builds to Google Play.

**Steps:**

1. Visit: https://play.google.com/console
2. Select your app
3. Navigate to: **Setup → API access**
4. Click **"Link a Google Cloud Project"**
5. Create a new Cloud project or link existing one
6. Grant the required permissions:
   - **Release Manager** role (recommended)
7. Click **"Done"**

**Create Service Account Key:**

1. In Google Cloud Console (https://console.cloud.google.com/)
2. Navigate to: **IAM & Admin → Service Accounts**
3. Click **"Create Service Account"**
4. Service account name: `eas-submit`
5. Click **"Create and Continue"**
6. Grant roles:
   - **Release Manager** (or appropriate role)
7. Click **"Done"**

**Generate JSON Key:**

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **"Add Key" → "Create new key"**
4. Select **JSON** key type
5. Click **"Create"**
6. The JSON key file will download automatically

**Place Key File:**

```bash
# Move the key file to your mobile directory
mv ~/Downloads/*.json mobile/google-service-account-key.json

# IMPORTANT: Never commit this file to git!
echo "google-service-account-key.json" >> .gitignore
```

---

### 3.3 Verify Configuration

Run the preparation script to verify everything is configured:

```bash
cd mobile
./scripts/prepare-android-build.sh
```

This will check:
- Node.js version
- EAS CLI installation
- Expo login status
- Project files (app.json, eas.json, assets)
- TypeScript compilation
- Dependencies
- Google Play service account key (basic check)

---

## 4. Build Android App

### 4.1 Start Build

**From the mobile directory:**

```bash
cd mobile
eas build --platform android --profile production
```

**What happens:**
1. EAS uploads your project to Expo's build servers
2. Build servers compile the Android app
3. App is signed with your upload key
4. Build artifact (AAB file) is created
5. If submission is configured, EAS automatically uploads to Google Play

**Build Time:**
- First build: ~20-30 minutes
- Subsequent builds: ~10-15 minutes (with caching)

---

### 4.2 Monitor Build Progress

EAS will provide a build URL:

```
Build started, view progress at:
https://expo.dev/accounts/YOUR_USERNAME/projects/sattva-streamer-mobile/builds/BUILD_ID
```

**Monitor with CLI:**
```bash
eas build:list --platform android
```

**View specific build:**
```bash
eas build:view BUILD_ID
```

**Cancel a build (if needed):**
```bash
eas build:cancel BUILD_ID
```

---

### 4.3 Build Success

When the build completes successfully, you'll see:

```
✅ Build finished
📦 Artifact: /path/to/app.aab
🔗 Download: https://expo.dev/artifacts/...
```

**If submission is configured:**
- Build automatically uploads to Google Play Console
- Appears in: **Release → Testing → Internal testing**

**If submission is NOT configured:**
- Manually upload the AAB file to Google Play Console
- Download from the build URL
- Navigate to: **Release → Testing → Internal testing → Create new release**

---

## 5. Submit to Google Play

### 5.1 Automatic Submission (Recommended)

If `eas.json` is configured with `serviceAccountKeyPath`, submission is automatic:

```bash
eas submit --platform android --profile production
```

**Or build + submit in one command:**
```bash
eas build --platform android --profile production --auto-submit
```

---

### 5.2 Manual Submission

If automatic submission fails or you prefer manual:

1. Download the AAB file from the build URL
2. Visit: https://play.google.com/console
3. Select your app
4. Navigate to: **Release → Testing → Internal testing**
5. Click **"Create new release"**
6. Upload the AAB file
7. Fill in release details:
   - **Release name**: v1.0.0 (or your version)
   - **Release notes**: Copy from release notes or describe changes
8. Click **"Next"**
9. Confirm and click **"Save"**

---

## 6. Configure Internal Testing

### 6.1 Add Testers

Navigate to: **Release → Testing → Internal testing**

**Add Testers:**
1. Click **"Add testers"**
2. Enter email addresses (up to 100 testers)
3. Click **"Add"**

**Testers receive:**
- Email invitation with opt-in link
- Instructions to join testing program
- Link to download the app

---

### 6.2 Set Release Notes

In the internal testing track, provide release notes:

**Example:**
```
Sattva Streamer v1.0.0 - Internal Testing

Welcome to the internal testing program! This release includes:

✨ Features:
- Complete stream management from your phone
- Push notifications for stream alerts
- Biometric authentication
- Offline mode for configuration changes
- Support for 7 languages

🐛 Known Issues:
- None reported yet

📣 Feedback:
Please report issues to: your-email@example.com
```

---

### 6.3 Opt-In Link

The opt-in link allows testers to join the internal testing program.

**Get the link:**
1. Navigate to: **Release → Testing → Internal testing**
2. Copy the **"Testing link"** or **"Opt-in link"**
3. Share this link with your testers

**Tester Experience:**
1. Click the opt-in link
2. Sign in to Google Play
3. Accept testing invitation
4. Download app from Play Store
5. Install and test

---

## 7. Install and Verify

### 7.1 Install on Test Device

**From Opt-In Link:**
1. Open the opt-in link on your test device
2. Accept the testing invitation
3. Google Play will open to the app page
4. Click **"Install"**
5. Wait for download and installation

**From Google Play Console (Developer):**
1. Navigate to: **Release → Testing → Internal testing**
2. Click **"Test app"** button
3. Install on any device linked to your Google account

---

### 7.2 Verification Checklist

**Basic Functionality:**
- [ ] App launches successfully
- [ ] Login screen appears
- [ ] Can login with email/password
- [ ] Dashboard loads and displays stream status
- [ ] Navigation works (bottom tabs)

**Stream Management:**
- [ ] Channel list loads
- [ ] Can start a stream
- [ ] Can stop a stream
- [ ] Status updates correctly

**Push Notifications:**
- [ ] Grant notification permissions
- [ ] Receive test notification
- [ ] Tap notification opens app
- [ ] Notification navigates to correct screen

**Offline Mode:**
- [ ] Enable airplane mode
- [ ] Make a configuration change
- [ ] Disable airplane mode
- [ ] Changes sync to backend

**Localization:**
- [ ] Change device language
- [ ] App updates to new language
- [ ] No missing translation keys

**Biometric Authentication:**
- [ ] Login with email/password
- [ ] Biometric prompt appears
- [ ] Can enable biometric
- [ ] Biometric login works on subsequent launches

---

### 7.3 Report Issues

**If issues are found:**

1. **Document the issue:**
   - Device model and Android version
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/screen recordings

2. **Fix the issue:**
   - Create a fix in your codebase
   - Test locally with development build

3. **Create new build:**
   ```bash
   cd mobile
   # Update version in app.json if needed
   eas build --platform android --profile production
   ```

4. **Submit to internal testing:**
   - New build will replace previous one
   - Testers will receive update notification

---

## 8. Troubleshooting

### 8.1 Common Build Issues

#### Build fails with "Package name mismatch"

**Cause:** Package name in `app.json` doesn't match Google Play Console

**Solution:**
1. Check `mobile/app.json`:
   ```json
   "android": {
     "package": "com.sattva.streamer"
   }
   ```
2. Verify in Google Play Console:
   - Setup → App details
   - Package name must match exactly

---

#### Build fails with "Service account authentication failed"

**Cause:** Service account key is invalid or missing

**Solution:**
1. Verify `google-service-account-key.json` exists in mobile directory
2. Check key file is valid JSON
3. Verify service account has **Release Manager** role
4. Re-generate service account key if needed
5. Update `eas.json` with correct path

---

#### Build fails with "Gradle build error"

**Cause:** Compilation errors in code or dependencies

**Solution:**
1. Run TypeScript check:
   ```bash
   cd mobile
   npx tsc --noEmit
   ```
2. Fix any TypeScript errors
3. Check build logs for specific error messages
4. Review recent code changes

---

#### Build fails with "Keystore error"

**Cause:** Android keystore configuration issue

**Solution:**
1. EAS typically manages keystore automatically
2. If using custom keystore, verify configuration in `eas.json`
3. Contact Expo support if issue persists

---

### 8.2 Common Submission Issues

#### Submission fails with "Invalid AAB"

**Cause:** AAB file is corrupted or invalid

**Solution:**
1. Re-download AAB from build URL
2. Verify file size (should be >10 MB)
3. Try manual upload instead of automatic submission

---

#### App not appearing in internal testing

**Cause:** Release not properly created or configured

**Solution:**
1. Navigate to: **Release → Testing → Internal testing**
2. Verify there's an active release
3. Check release status (should be "Active")
4. Try creating a new release if needed

---

#### Testers can't install app

**Cause:** Opt-in link not working or tester not eligible

**Solution:**
1. Verify tester is in the internal testing list
2. Check opt-in link is correct and active
3. Tester must:
   - Be signed in to Google Play with same email
   - Have accepted testing invitation
   - Have device running Android 5.0+ (API level 21+)

---

#### "App not available" error in Play Store

**Cause:** Device or country restrictions

**Solution:**
1. Check device compatibility:
   - Android version: 5.0+ (API level 21+)
   - Architecture: ARM, ARM64, x86 (EAS builds all three)
2. Verify app is available in tester's country
3. Check if any device exclusions are configured

---

### 8.3 Getting Help

**Expo Documentation:**
- [EAS Build Docs](https://docs.expo.dev/build/introduction/)
- [EAS Submit Docs](https://docs.expo.dev/submit/introduction/)
- [Android Builds](https://docs.expo.dev/build/building-on-a-ci/)

**Google Play Resources:**
- [Google Play Console Help](https://support.google.com/googleplay/android-developer)
- [Play Console Best Practices](https://developer.android.com/distribute/best-practices)

**Community Support:**
- [Expo Forums](https://forums.expo.dev/)
- [Stack Overflow (expo tag)](https://stackoverflow.com/questions/tagged/expo)
- [Google Play Developer Community](https://support.google.com/googleplay/android-developer/community)

---

## Quick Reference

### Essential Commands

```bash
# Build
eas build --platform android --profile production

# Build and submit in one command
eas build --platform android --profile production --auto-submit

# Submit existing build
eas submit --platform android --profile production --build-id BUILD_ID

# List builds
eas build:list --platform android

# View build details
eas build:view BUILD_ID

# Cancel build
eas build:cancel BUILD_ID

# Check login
eas whoami

# Update EAS CLI
npm update -g eas-cli
```

### Configuration Files

- **app.json**: Expo app configuration (package name, version, permissions)
- **eas.json**: EAS build configuration (build profiles, submission settings)
- **google-service-account-key.json**: Service account key for automatic submission

### Important Links

- Google Play Console: https://play.google.com/console
- Create app: https://play.google.com/console/signup
- API access: https://play.google.com/console → Setup → API access
- EAS dashboard: https://expo.dev

---

## Next Steps

After successful internal testing:

1. **Collect feedback** from internal testers
2. **Fix bugs and issues**
3. **Move to closed testing** (optional):
   - Larger group of testers (up to 2000)
   - Still requires opt-in link
4. **Move to open testing** (optional):
   - Anyone can join testing
   - No opt-in link required
5. **Production release**:
   - Submit to production track
   - App review by Google (1-3 days)
   - Publish to Play Store

---

## Checklist Summary

- [ ] Google Play Developer account created
- [ ] App created in Google Play Console
- [ ] App details configured (name, descriptions, screenshots)
- [ ] Content rating completed
- [ ] Privacy policy uploaded
- [ ] Service account created and key downloaded
- [ ] `eas.json` configured with service account key
- [ ] Preparation script passed
- [ ] Android app built successfully
- [ ] Build submitted to internal testing
- [ ] Testers added and opt-in link shared
- [ ] App installed on test device
- [ ] Verification tests passed

---

**Last Updated:** 2026-01-23
**Version:** 1.0
**Status:** Ready for Implementation
