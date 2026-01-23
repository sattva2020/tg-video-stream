# iOS Build Commands - Quick Reference

Quick reference for iOS TestFlight build and submission commands.

## Essential Commands

### Preparation
```bash
# Navigate to mobile directory
cd mobile

# Install dependencies (if needed)
npm install

# Prepare and verify everything is ready
./scripts/prepare-ios-build.sh

# Login to Expo
eas login

# Check current user
eas whoami
```

### Building

```bash
# Build for iOS (production)
eas build --platform ios --profile production

# Build and auto-submit in one command
eas build --platform ios --profile production --auto-submit

# Build locally (requires macOS and Xcode)
eas build --platform ios --profile production --local

# Build with specific message
eas build --platform ios --profile production --message "Initial TestFlight build"
```

### Submitting

```bash
# Submit existing build to TestFlight
eas submit --platform ios --profile production

# Submit with non-interactive mode
eas submit --platform ios --profile production --non-interactive

# Submit specific build
eas submit --platform ios --profile production --build-id [BUILD_ID]
```

### Monitoring

```bash
# List all builds
eas build:list

# List only iOS builds
eas build:list --platform ios

# List only production builds
eas build:list --platform ios --profile production

# View build details
eas build:view [BUILD_ID]

# View build logs
eas build:view [BUILD_ID] --logs
```

### Managing Builds

```bash
# Cancel a build
eas build:cancel [BUILD_ID]

# Delete a build
eas build:delete [BUILD_ID]
```

## Configuration Files

### app.json
```json
{
  "expo": {
    "ios": {
      "bundleIdentifier": "com.sattva.streamer",
      "buildNumber": "1",
      "version": "0.1.0"
    }
  }
}
```

### eas.json
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
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your-apple-id@example.com",
        "ascAppId": "YOUR_APP_STORE_CONNECT_APP_ID",
        "appleTeamId": "YOUR_APPLE_TEAM_ID"
      }
    }
  }
}
```

## Environment Variables

```bash
# Set API base URL
EXPO_PUBLIC_API_URL=https://your-api.com/api

# Set Sentry environment
SENTRY_ENVIRONMENT=production

# Build with environment variables
eas build --platform ios --profile production --env EXPO_PUBLIC_API_URL=https://your-api.com/api
```

## Troubleshooting Commands

```bash
# Check EAS CLI version
eas --version

# Update EAS CLI
npm update -g eas-cli

# Clear EAS cache
eas build --platform ios --profile production --clear-cache

# Check project configuration
eas build:inspect --platform ios --profile production

# Validate project
eas build --platform ios --profile production --skip-native-build
```

## TestFlight Web Interface URLs

- **App Store Connect**: https://appstoreconnect.apple.com/
- **TestFlight Tab**: https://appstoreconnect.apple.com/testflight/
- **My Apps**: https://appstoreconnect.apple.com/apps
- **Apple Developer**: https://developer.apple.com/account/

## Build States

- **new**: Build is queued
- **in-progress**: Build is running
- **errored**: Build failed
- **finished**: Build succeeded
- **canceled**: Build was cancelled

## TestFlight Build States

- **Processing**: Build is being processed by Apple
- **Waiting for Review**: Build is waiting for Apple review
- **Approved for Testing**: Build is ready for testers
- **Ready to Test**: Build is available to testers
- **Expired**: Build is no longer available

## Version Numbers

### app.json
```json
{
  "expo": {
    "version": "0.1.0",        // User-facing version
    "ios": {
      "buildNumber": "1"       // Build-specific number
    }
  }
}
```

### Version Update Strategy

**For feature updates:**
```bash
# Update version in app.json
# 0.1.0 → 0.2.0
```

**For bug fixes:**
```bash
# Update version in app.json
# 0.1.0 → 0.1.1
```

**For production builds:**
```bash
# Use autoIncrement in eas.json
# Build numbers will auto-increment
```

## Time Estimates

- **EAS Build Time**: 20-30 minutes (first build), 10-15 minutes (subsequent)
- **App Store Connect Processing**: 5-10 minutes
- **TestFlight Review**: 1-2 hours (internal), 24-48 hours (external)
- **App Store Review**: 1-3 days (typical), up to 7 days (complex apps)

## Quick Checklist

Before building:
- [ ] Logged into Expo (`eas whoami`)
- [ ] Bundle ID registered in Apple Developer portal
- [ ] App created in App Store Connect
- [ ] eas.json configured with Apple credentials
- [ ] app.json has correct version numbers
- [ ] All assets (icons, splash screens) are in place
- [ ] TypeScript compilation passes (`npm run type-check`)
- [ ] No console.log statements in production code

After building:
- [ ] Build completed successfully
- [ ] .ipa file uploaded to App Store Connect
- [ ] Build appears in TestFlight tab
- [ ] Build status is "Ready to Test"
- [ ] Internal testers added
- [ ] Test information configured

## Common Build Parameters

```bash
# Build with specific Node version
eas build --platform ios --profile production --node 18.18.0

# Build with custom environment
eas build --platform ios --profile production --env production

# Build with timeout (default: 120 minutes)
eas build --platform ios --profile production --timeout 180

# Build with non-interactive mode (CI/CD)
eas build --platform ios --profile production --non-interactive

# Build with specific project ID
eas build --platform ios --profile production --project-id [PROJECT_ID]
```

## Resource Classes

- **m-medium**: Medium resources (iOS) - 2 CPU, 4GB RAM
- **m-large**: Large resources (iOS) - 4 CPU, 8GB RAM
- **medium**: Medium resources (Android) - 2 CPU, 4GB RAM
- **large**: Large resources (Android) - 4 CPU, 8GB RAM

## Related Scripts

```bash
# Prepare for build
./scripts/prepare-ios-build.sh

# Type check
npm run type-check

# Run tests
npm test

# Lint code
npm run lint
```

## Documentation

- [Full Submission Guide](./ios-testflight-submission-guide.md)
- [Checklist](./ios-testflight-checklist.md)
- [App Store Listing](./app-store-listing.md)
- [Privacy Policy](./privacy-policy.md)
- [Assets Guide](./ASSETS_GUIDE.md)

## Support

- **Expo Forums**: https://forums.expo.dev/
- **EAS Build Status**: https://status.expo.dev/
- **EAS Documentation**: https://docs.expo.dev/build/
- **TestFlight Documentation**: https://developer.apple.com/testflight/

---

**Tip**: Bookmark this page for quick reference during the build process!
