# App Store Screenshots

This directory should contain screenshots for App Store and Google Play submissions.

## Required Screenshots

### iOS (App Store)
Place screenshots in these subdirectories:

```
screenshots/
├── ios/
│   ├── iPhone-6.7/        # 1290x2796px (iPhone 14 Pro Max, 15 Pro Max)
│   ├── iPhone-6.5/        # 1242x2688px (iPhone 11 Pro Max, 12, 13, 14)
│   ├── iPhone-5.5/        # 1242x2208px (iPhone 8 Plus, legacy)
│   └── iPad-Pro/          # 2048x2732px (iPad Pro 12.9")
└── android/
    ├── phone/             # 1080x1920px minimum
    └── tablet/            # 2024x2732px minimum
```

### Screenshot Requirements
- **Quantity**: 3-10 screenshots per platform/device type
- **Format**: PNG or JPEG
- **Content**: Show key features of Sattva Streamer app
- **No device frames**: App Store and Google Play add frames automatically

### Screenshot Ideas

1. **Dashboard** (Main screen)
   - Show stream status overview
   - Display active/inactive streams
   - Highlight real-time monitoring

2. **Stream Configuration**
   - Stream settings screen
   - Show RTMP/RTSP configuration
   - Display key setup options

3. **Push Notifications**
   - Mockup of push notification
   - Show alert message example
   - Demonstrate alert types (online, offline, error)

4. **Biometric Authentication**
   - Face ID / Touch ID prompt
   - Show security feature
   - Emphasize privacy

5. **Offline Mode**
   - Show "No Connection" indicator
   - Demonstrate offline configuration
   - Highlight sync capability

6. **Multi-language Support**
   - Show language selection
   - Display localized content
   - Include multiple language examples

7. **Stream Analytics**
   - Show viewer count graph
   - Display bandwidth usage
   - Present uptime statistics

### Tools for Creating Screenshots

1. **Expo Go** - Take screenshots directly from development build
2. **Simulator/Emulator** - Use iOS Simulator or Android Emulator
3. **Device Frames** - [MockupPhone](https://mockupphone.com/) for presentation
4. **Design Tools** - Figma, Sketch for polished screenshots

### Creation Workflow

1. Build and run the app:
   ```bash
   cd mobile
   npx expo start
   ```

2. Take screenshots on device/simulator:
   - iOS: Cmd+Shift+4 (Simulator) or Power+Volume Up (device)
   - Android: Cmd+Shift+4 (emulator) or Power+Volume Down (device)

3. Organize by platform and device type

4. Optional: Add captions/markup to highlight features

### Validation

Before submission, verify:
- [ ] Correct resolution for each device type
- [ ] All screenshots match current app version
- [ ] No sensitive or test data visible
- [ ] Consistent visual style across screenshots
- [ ] App UI is current and functional
- [ ] At least 3 screenshots per platform
- [ ] File size under 5MB per screenshot

## References

- [App Store Connect Help - Screenshots](https://help.apple.com/app-store-connect/#/devd274dd912)
- [Google Play Console - Graphic Assets](https://support.google.com/googleplay/android-developer/answer/10788770)
- [Expo Screenshots Guide](https://docs.expo.dev/eas/screenshots/)
