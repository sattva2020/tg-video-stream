# Sattva Streamer Mobile

Native iOS and Android mobile application for managing streaming broadcasts.

## Tech Stack

- **Framework**: React Native with Expo SDK 50
- **Language**: TypeScript
- **Navigation**: React Navigation (Stack + Tab)
- **State Management**: React Context + React Query + Zustand
- **Localization**: i18next (EN, RU, UK, DE, ES, JA, ZH)
- **Push Notifications**: Expo Notifications (FCM for Android, APNs for iOS)
- **Biometric Auth**: expo-local-authentication
- **Offline Storage**: AsyncStorage + SQLite
- **Build Tools**: EAS Build

## Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0
- iOS: Xcode (for iOS builds)
- Android: Android Studio (for Android builds)

## Installation

```bash
npm install
```

## Development

```bash
# Start Expo development server
npm start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Run in web browser
npm run web
```

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

## Type Checking

```bash
npm run type-check
```

## Building

```bash
# Build for iOS (TestFlight)
npm run build:ios

# Build for Android (Google Play)
npm run build:android

# Local builds
npm run build:ios:local
npm run build:android:local
```

## Deployment

```bash
# Submit to App Store
npm run submit:ios

# Submit to Google Play
npm run submit:android

# OTA update (instant, no review)
npm run update
```

## Project Structure

```
src/
├── api/           # API clients and endpoints
├── components/    # Reusable UI components
├── contexts/      # React Context providers
├── hooks/         # Custom React hooks
├── i18n/          # Localization files
├── navigation/    # Navigation configuration
├── screens/       # Screen components
└── utils/         # Utility functions
```

## Features

- ✅ Email/password and OAuth authentication
- ✅ Biometric authentication (Face ID, Touch ID, fingerprint)
- ✅ Mobile-optimized dashboard
- ✅ Channel management
- ✅ Playlist management
- ✅ Push notifications for alerts
- ✅ Offline mode with sync
- ✅ Multi-language support (7 languages)
- ✅ Dark/Light theme

## Environment Variables

See `.env.example` for required environment variables.

## License

Proprietary - All rights reserved
