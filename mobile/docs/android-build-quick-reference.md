# Android Build Quick Reference

Quick reference guide for building and submitting the Android app to Google Play Console.

---

## Build Commands

### Standard Build

```bash
cd mobile
eas build --platform android --profile production
```

**Time:** 10-30 minutes (first build slower)
**Output:** Android App Bundle (.aab)

---

### Build and Auto-Submit

```bash
eas build --platform android --profile production --auto-submit
```

Builds and automatically submits to Google Play (if configured).

---

### Submit Existing Build

```bash
eas submit --platform android --profile production --build-id BUILD_ID
```

Submit a previously built artifact.

**Get build ID:**
```bash
eas build:list --platform android
```

---

### Local Build (Advanced)

```bash
eas build --platform android --profile production --local
```

Build on your local machine (requires Docker, Android SDK, etc.).

**Pros:**
- Faster (no queue)
- No internet required during build
- Full control over build environment

**Cons:**
- Complex setup
- Requires significant disk space
- Slower on most machines

---

## Monitoring Commands

### List Builds

```bash
eas build:list --platform android
```

**Output:**
```
Build ID    Status    Platform    Profile    Created
----------  --------  ----------  ---------  ------------------
abc123      finished  android     production  2026-01-23 10:00
def456      in_queue  android     production  2026-01-23 11:00
```

---

### View Build Details

```bash
eas build:view BUILD_ID
```

**Shows:**
- Build status
- Build duration
- Artifact URL
- Build logs link
- Platform version
- App version

---

### Cancel Build

```bash
eas build:cancel BUILD_ID
```

Cancel an in-progress or queued build.

---

### Watch Build (Real-time)

```bash
eas build --platform android --profile production --wait
```

Waits for build to complete and shows real-time progress.

---

## Configuration

### app.json (Android Section)

```json
{
  "expo": {
    "android": {
      "package": "com.sattva.streamer",
      "versionCode": 1,
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#FFFFFF"
      },
      "permissions": [
        "INTERNET",
        "RECEIVE_BOOT_COMPLETED",
        "VIBRATE",
        "POST_NOTIFICATIONS"
      ]
    }
  }
}
```

**Key Fields:**
- `package`: Must match Google Play Console
- `versionCode`: Increment for each release
- `permissions`: Required app permissions

---

### eas.json (Android Build)

```json
{
  "build": {
    "production": {
      "android": {
        "buildType": "app-bundle"
      }
    }
  },
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

**Key Fields:**
- `buildType`: Always "app-bundle" (Google Play requirement)
- `serviceAccountKeyPath`: Path to service account JSON key
- `track`: "internal", "beta", or "production"

---

## Build Profiles

### Development

```bash
eas build --platform android --profile development
```

**Characteristics:**
- developmentClient: true
- Includes DevTools
- Faster build times
- For testing only

---

### Preview

```bash
eas build --platform android --profile preview
```

**Characteristics:**
- Internal distribution
- No DevTools
- For internal testing

---

### Production

```bash
eas build --platform android --profile production
```

**Characteristics:**
- Optimized build
- No debugging
- For app store submission

---

## Environment Variables

### Set Environment Variables

**Option 1: Command Line**
```bash
eas build --platform android --profile production \
  --env APP_ENV=production \
  --env API_URL=https://api.example.com
```

**Option 2: eas.json**
```json
{
  "build": {
    "production": {
      "env": {
        "APP_ENV": "production",
        "API_URL": "https://api.example.com"
      }
    }
  }
}
```

**Option 3: .env File**
```bash
# mobile/.env.production
APP_ENV=production
API_URL=https://api.example.com
```

---

## Submission Tracks

### Internal Testing

```bash
eas submit --platform android --track internal
```

**Characteristics:**
- Up to 100 testers
- Opt-in link required
- No review required

**Use for:**
- Initial testing
- Team testing
- QA verification

---

### Closed Testing (Beta)

```bash
eas submit --platform android --track beta
```

**Characteristics:**
- Up to 2000 testers
- Opt-in link required
- No review required

**Use for:**
- Expanded testing
- Beta testing program
- Pre-release testing

---

### Open Testing (Alpha)

```bash
eas submit --platform android --track alpha
```

**Characteristics:**
- Anyone can join
- No opt-in link
- No review required

**Use for:**
- Public beta
- Early access
- Feedback collection

---

### Production

```bash
eas submit --platform android --track production
```

**Characteristics:**
- Public release
- Review required (1-3 days)
- Strict compliance checks

**Use for:**
- Official release
- Public distribution

---

## Troubleshooting Commands

### Check EAS CLI Version

```bash
eas --version
```

**Update if needed:**
```bash
npm update -g eas-cli
```

---

### Verify Expo Login

```bash
eas whoami
```

**Re-login if needed:**
```bash
eas login
```

---

### Clear EAS Cache

```bash
eas build --platform android --profile production --clear-cache
```

Use if build fails with cache errors.

---

### Check Project Configuration

```bash
eas build:list --platform android --non-interactive
```

Shows project configuration without interactive prompts.

---

### Validate Configuration

```bash
eas build --platform android --profile production --no-wait
```

Starts build and returns immediately (useful for CI/CD).

---

## Build Time Estimates

| Build Type | First Build | Subsequent Builds | Notes |
|------------|-------------|-------------------|-------|
| Development | 15-20 min | 10-15 min | Includes DevTools |
| Preview | 15-20 min | 10-15 min | Internal distribution |
| Production | 20-30 min | 10-15 min | Optimized build |

**Factors affecting build time:**
- Cache hit/miss
- Queue position
- Project size
- Network speed

---

## Resource Classes

### Default (Medium)

```json
{
  "build": {
    "production": {
      "android": {
        "resourceClass": "medium"
      }
    }
  }
}
```

**Specs:**
- 2 CPU cores
- 4 GB RAM
- 10 GB disk

**Best for:** Most projects

---

### Large

```json
{
  "build": {
    "production": {
      "android": {
        "resourceClass": "large"
      }
    }
  }
}
```

**Specs:**
- 8 CPU cores
- 16 GB RAM
- 50 GB disk

**Best for:**
- Large projects
- Faster builds
- Complex native modules

---

## Build Artifacts

### App Bundle (.aab)

**Default output format**
- Required by Google Play
- Smaller size
- Includes multiple architectures

**Location:**
- Download from build URL
- Or from EAS dashboard

---

### APK (Legacy)

**Not recommended for new apps**
- Larger size
- Single architecture
- Manual upload required

**Generate only if needed:**
```json
{
  "build": {
    "production": {
      "android": {
        "buildType": "apk"
      }
    }
  }
}
```

---

## Versioning

### Update Version Number

**Edit:** `mobile/app.json`

```json
{
  "expo": {
    "version": "1.0.1",
    "android": {
      "versionCode": 2
    }
  }
}
```

**Rules:**
- `version`: Semantic version (x.y.z)
- `versionCode`: Incrementing integer
- Keep in sync (usually)

---

### Auto-Increment

```json
{
  "build": {
    "production": {
      "android": {
        "autoIncrement": true
      }
    }
  }
}
```

Automatically increments `versionCode` for each build.

---

## Common Parameters

### Non-Interactive Mode

```bash
eas build --platform android --profile production --non-interactive
```

Useful for scripts and CI/CD.

---

### Wait for Build

```bash
eas build --platform android --profile production --wait
```

Blocks until build completes (shows progress).

---

### Specific Build ID

```bash
eas submit --platform android --build-id abc123
```

Submit a specific build artifact.

---

### Output JSON

```bash
eas build --platform android --profile production --json
```

Outputs build information in JSON format.

---

## Build Hooks

### Pre-Build Hook

```json
{
  "build": {
    "production": {
      "hook": "bash ./scripts/pre-build.sh"
    }
  }
}
```

Runs before build starts.

---

### Post-Build Hook

```json
{
  "build": {
    "production": {
      "hook": "bash ./scripts/post-build.sh"
    }
  }
}
```

Runs after build completes.

---

## Useful Aliases

### Add to shell (~/.bashrc or ~/.zshrc)

```bash
alias eas-build-android='eas build --platform android --profile production'
alias eas-build-android-dev='eas build --platform android --profile development'
alias eas-submit-android='eas submit --platform android --profile production'
alias eas-builds-android='eas build:list --platform android'
```

**Usage:**
```bash
eas-build-android
eas-submit-android
```

---

## Dashboard Links

### EAS Dashboard
- URL: https://expo.dev
- View builds, artifacts, and configuration
- Monitor build status in real-time

### Google Play Console
- URL: https://play.google.com/console
- Manage releases and testing tracks
- View crash reports and analytics

---

## Tips and Best Practices

### 1. Always Clean Before Building

```bash
git status
eas build --platform android --profile production --clear-cache
```

### 2. Version Control

```bash
# Tag releases
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 3. Keep Service Account Key Secure

```bash
# Never commit key file
echo "google-service-account-key.json" >> .gitignore

# Encrypt in CI/CD
travis encrypt-file google-service-account-key.json
```

### 4. Monitor Build Queue

```bash
# Check queue position
eas build:list --platform android
```

### 5. Use Appropriate Track

- Internal: Team testing, QA
- Closed: Beta testing, early adopters
- Open: Public beta, feedback
- Production: Official release

---

## Quick Decision Tree

```
Need to build Android app?
  |
  ├─ For local development?
  |   └─ Use: development profile
  |
  ├─ For team testing?
  |   └─ Use: preview profile
  |
  └─ For app store submission?
      └─ Use: production profile

Testing track?
  |
  ├─ Internal team (≤100)?
  |   └─ Use: internal track
  |
  ├─ Beta testing (≤2000)?
  |   └─ Use: closed/beta track
  |
  └─ Public beta?
      └─ Use: open/alpha track
```

---

## Emergency Procedures

### Cancel Wrong Build

```bash
eas build:cancel BUILD_ID
```

### Remove Release from Testing Track

1. Visit Google Play Console
2. Navigate to: Release → Testing → [Track Name]
3. Click "..." on release
4. Select "Stop testing"

### Emergency Rollback

1. Create new build with previous code
2. Submit to same track
3. Google Play will rollback to new build

---

**Last Updated:** 2026-01-23
**Version:** 1.0

**For detailed instructions, see:**
- `docs/android-google-play-submission-guide.md`
- `docs/android-google-play-checklist.md`
