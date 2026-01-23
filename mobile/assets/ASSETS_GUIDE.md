# App Store Assets Guide

## Current Status
This directory contains placeholder PNG assets. For production deployment, these should be replaced with professionally designed assets.

## Required Assets

### 1. App Icons
- **icon.png** (1024x1024px)
  - Main app icon for App Store and Google Play
  - Should be simple, recognizable at small sizes
  - Recommended: Sattva logo or "SS" monogram
  - Background: Purple gradient (#6366f1 to #8b5cf6)

### 2. Splash Screen
- **splash.png** (1284x2778px or 1920x1080px)
  - Launch screen for iOS and Android
  - Should match app branding
  - Center logo on solid/gradient background
  - Safe area: Center 60% of screen

### 3. Adaptive Icon (Android)
- **adaptive-icon.png** (1024x1024px)
  - Foreground layer for Android adaptive icons
  - Background color: #ffffff (configured in app.json)
  - Safe zone: Center 66% (icon will be masked to different shapes)

### 4. Additional Icons
- **favicon.png** (192x192px) - Web favicon
- **notification-icon.png** (96x96px) - Push notification icon (Android)
  - Should be white with transparent background for Android
  - Solid white foreground on transparent background

### 5. Notification Sound (Optional)
- **notification.wav** - Sound file for push notifications
  - Format: WAV or MP3
  - Duration: Under 30 seconds recommended
  - Size: Keep under 1MB
  - Note: Currently not included (expo-notifications will use system default sound)
  - To add: Place a WAV file in this directory and reference in app.json

## App Store Screenshots

Screenshots should be placed in `mobile/screenshots/` directory:

### iOS Screenshots (App Store)
- **iPhone 6.7" Display** (1290x2796px): 3-5 screenshots
- **iPhone 6.5" Display** (1242x2688px): 3-5 screenshots
- **iPad Pro 12.9" Display** (2048x2732px): 3-5 screenshots

### Android Screenshots (Google Play)
- **Phone** (1080x1920px minimum): At least 2 screenshots
- **Tablet** (2024x2732px minimum): At least 2 screenshots

### Screenshot Content Ideas
1. Dashboard view with stream status
2. Stream configuration screen
3. Push notification example
4. Biometric authentication
5. Offline mode indicator

## Design Guidelines

### Brand Colors
- Primary: #6366f1 (Indigo)
- Secondary: #8b5cf6 (Purple)
- Background: #ffffff (White)
- Text: #1f2937 (Gray 900)

### Icon Design Principles
- Simple and recognizable
- Works at multiple sizes (16px to 1024px)
- High contrast for accessibility
- Minimalist approach
- Avoid text in icons

### Tools for Asset Creation
- **Figma**: Recommended for UI design and icon creation
- **Sketch**: Alternative for macOS users
- **Adobe Illustrator**: For vector icons
- **Canva**: Quick templates for app store assets

## Asset Generation Tools

### Online Tools
- [AppIconGenerator](https://appicon.co/) - Generate all icon sizes from one source
- [MakeAppIcon](https://makeappicon.com/) - Another icon generator
- [Expo Asset Generation](https://docs.expo.dev/guides/assets/#using-a-tools-library) - Official Expo tool

### Command Line Tool (Expo)
```bash
npx expo-optimize
```

## Verification

Before submitting to app stores, verify:
- [ ] All icons are visible and clear
- [ ] Splash screen displays correctly on all devices
- [ ] Screenshots match current app UI
- [ ] No transparency in main app icon (iOS requirement)
- [ ] Notification icon is white/transparent (Android requirement)
- [ ] All images are optimized (file size < 1MB per image)

## References
- [App Store Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/app-store)
- [Google Play Asset Requirements](https://developer.android.com/guide/practices/ui_guidelines/icon_design)
- [Expo Assets Guide](https://docs.expo.dev/guides/assets/)
