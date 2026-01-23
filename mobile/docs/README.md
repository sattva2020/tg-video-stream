# iOS TestFlight Submission Documentation

This directory contains comprehensive documentation for building and submitting the Sattva Streamer iOS app to TestFlight.

## Documentation Files

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

### 4. [App Store Listing](./app-store-listing.md)
**App store metadata** in all supported languages.

**Contains:**
- App names (EN, RU, UK, DE, ES, JA, ZH)
- Short descriptions
- Full descriptions
- Keywords
- SEO optimization

**Length**: ~400 lines
**Best for**: Copy-pasting into App Store Connect

---

### 5. [Privacy Policy](./privacy-policy.md)
**Comprehensive privacy policy** for App Store submission.

**Covers:**
- Information collected
- Data usage
- Security measures
- Third-party services
- User rights
- GDPR/CCPA compliance
- International data transfers

**Length**: ~300 lines
**Best for**: Uploading to App Store Connect

---

### 6. [Assets Guide](./ASSETS_GUIDE.md)
**Guidelines for creating app store assets**.

**Includes:**
- Icon requirements
- Splash screen requirements
- Screenshot specifications
- Design guidelines
- Tools and workflows

**Length**: ~150 lines
**Best for**: Creating production-quality assets

---

## Scripts

### [prepare-ios-build.sh](../scripts/prepare-ios-build.sh)
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

## Quick Start Guide

### For First-Time Submission

1. **Read the guide** (20 minutes)
   ```bash
   # Start with the comprehensive submission guide
   cat docs/ios-testflight-submission-guide.md
   ```

2. **Set up Apple Developer account** (if needed)
   - Enroll at: https://developer.apple.com/programs/enroll/
   - Cost: $99/year
   - Wait for account approval (1-2 days)

3. **Create app in App Store Connect** (10 minutes)
   - Follow steps in submission guide, Section 1
   - Note down your Apple ID, ASC App ID, and Team ID

4. **Configure EAS Build** (5 minutes)
   - Edit `eas.json` with your Apple credentials
   - Use the quick reference for configuration examples

5. **Run preparation script** (2 minutes)
   ```bash
   cd mobile
   ./scripts/prepare-ios-build.sh
   ```

6. **Build the app** (20-30 minutes)
   ```bash
   eas build --platform ios --profile production
   ```

7. **Submit to TestFlight** (automatic or manual)
   - If `eas.json` is configured correctly, submission is automatic
   - Otherwise, submit manually via App Store Connect

8. **Configure internal testing** (10 minutes)
   - Add internal testers
   - Configure test information
   - Add release notes

9. **Install and verify** (10 minutes)
   - Install via TestFlight
   - Run verification tests
   - Complete checklist

### For Experienced Users

If you've done this before, you can use the quick reference:

```bash
# 1. Update version in app.json (if needed)
# 2. Update eas.json credentials (if changed)
# 3. Run prep script
./scripts/prepare-ios-build.sh

# 4. Build
eas build --platform ios --profile production

# 5. Monitor
eas build:list --platform ios

# 6. Submit (if not automatic)
eas submit --platform ios --profile production
```

---

## Workflow Diagram

```
Start
  ↓
[Prerequisites Check]
  ↓
[Apple Developer Account] → [Enroll if needed]
  ↓
[App Store Connect Setup] → [Create App]
  ↓
[Configure EAS Build] → [Update eas.json]
  ↓
[Run Prep Script] → [Fix any issues]
  ↓
[Build iOS App] → [Wait 20-30 min]
  ↓
[Submit to TestFlight] → [Automatic or Manual]
  ↓
[Configure Testing] → [Add Testers]
  ↓
[Install & Verify] → [Test on Device]
  ↓
[Complete Checklist] → [Sign Off]
  ↓
Done ✓
```

---

## Common Tasks

### Check build status
```bash
eas build:list --platform ios --profile production
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
eas submit --platform ios --profile production --build-id [BUILD_ID]
```

---

## Time Estimates

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

---

## Troubleshooting

### Build fails with certificate errors
- **Cause**: Bundle ID mismatch or incorrect team ID
- **Solution**: Verify bundle ID in `app.json` matches App Store Connect
- **Solution**: Check team ID in `eas.json` is correct

### Build not appearing in TestFlight
- **Cause**: ASC App ID incorrect or build failed
- **Solution**: Verify ASC App ID in `eas.json`
- **Solution**: Check build status: `eas build:list`

### "Invalid Bundle" error
- **Cause**: Missing metadata or incorrect assets
- **Solution**: Verify all assets exist (icon, splash, screenshots)
- **Solution**: Check info.plist permissions are correct

### Testers can't install
- **Cause**: Invitation expired or device incompatible
- **Solution**: Resend invitation from App Store Connect
- **Solution**: Check device meets minimum iOS version (13.0+)

---

## Related Resources

### Official Documentation
- [EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [TestFlight Documentation](https://developer.apple.com/testflight/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)

### Project Files
- `eas.json` - EAS build configuration
- `app.json` - Expo app configuration
- `package.json` - Dependencies and scripts

### Previous Subtasks
- **Subtask 6-1**: Configure EAS Build for iOS and Android
- **Subtask 6-2**: Create app store assets (icons, splash screens, screenshots)
- **Subtask 6-3**: Create app store listings (descriptions, privacy policy)

---

## Support

### Getting Help
1. Check the troubleshooting section in the submission guide
2. Search Expo forums: https://forums.expo.dev/
3. Check EAS Build status: https://status.expo.dev/
4. Review build logs in EAS dashboard

### Reporting Issues
When reporting issues, include:
- EAS CLI version: `eas --version`
- Build ID: From build URL
- Error message: Full error text
- Build logs: From EAS dashboard

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-23 | Initial documentation for TestFlight submission |

---

## Checklist Status

- [ ] Read all documentation
- [ ] Apple Developer account active
- [ ] App created in App Store Connect
- [ ] EAS Build configured
- [ ] Preparation script passed
- [ ] iOS app built successfully
- [ ] Submitted to TestFlight
- [ ] Internal testing configured
- [ ] App installed and verified
- [ ] Checklist completed

**Next Subtask**: 6-5 - Build and submit Android app to Google Play (internal testing)

---

**Last Updated**: 2026-01-23
**Status**: Ready for Implementation
