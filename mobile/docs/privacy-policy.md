# Privacy Policy - Stream Manager Mobile App

**Last Updated:** January 23, 2026
**App Version:** 1.0.0
**Effective Date:** January 23, 2026

---

## Introduction

Welcome to Stream Manager. This Privacy Policy explains how we handle your information when you use the Stream Manager mobile application ("App"). We are committed to protecting your privacy and ensuring the security of your personal information.

**Important Note:** Stream Manager is a client application that connects to your own self-hosted Stream Manager server. We do not host your data or provide backend services. This privacy policy covers only the mobile app itself.

---

## Information We Collect

### 1. Information You Provide

**Account Credentials**
- Email address and password used to log in to your Stream Manager server
- These credentials are stored securely on your device using iOS Keychain/Android Keystore
- Credentials are never transmitted to any third-party service
- Credentials are only sent to your own Stream Manager server via encrypted HTTPS connection

**Biometric Data**
- If you enable biometric authentication (Face ID, Touch ID, fingerprint), the App uses your device's native biometric APIs
- Biometric data is never accessed, stored, or transmitted by the App
- Biometric authentication is handled entirely by your device's operating system

**Configuration Settings**
- App preferences such as language selection, theme choice, notification settings
- These are stored locally on your device using AsyncStorage
- Settings are not transmitted to any service other than your Stream Manager server

### 2. Information Collected Automatically

**Device Information**
- Device type (iPhone/iPad, Android phone/tablet)
- Operating system version
- Unique device identifier (for push notification registration only)
- This information is sent to your Stream Manager server for push notification delivery

**Push Notification Token**
- The App registers for push notifications on your behalf
- Your device's push token (APNs for iOS, FCM for Android) is sent to your Stream Manager server
- This token is only used to send you notifications about your streams
- Tokens are stored securely on your server and are never shared with third parties

**Usage Data (Optional)**
- If you enable error reporting (Sentry), crash reports and error logs may be collected
- This helps us improve app stability and fix bugs
- Error reports contain device type, OS version, and error details only
- No personal information or stream content is included in error reports

**Network Information**
- Connection status (online/offline) for offline mode functionality
- This is only used locally to determine when to sync pending changes

### 3. Information We Do NOT Collect

**We DO NOT collect:**
- Your streaming content (audio, video, or any media)
- Your stream configuration or channel details
- Your listener data or analytics
- Your playlist content or track information
- Your personal files or documents
- Your location data
- Your contacts
- Your camera or microphone (unless you explicitly use these features in other apps)
- Any data from third-party services (social media, email accounts, etc.)

---

## How We Use Your Information

The App uses your information as follows:

1. **Authentication**
   - To securely log you in to your Stream Manager server
   - To enable biometric quick login (Face ID, Touch ID, fingerprint)

2. **Push Notifications**
   - To send you alerts about stream failures
   - To notify you of important events from your Stream Manager server
   - To provide delivery status for your streams

3. **Offline Mode**
   - To store configuration changes locally when offline
   - To sync changes to your server when you reconnect to the internet

4. **App Functionality**
   - To display your stream status and statistics
   - To manage your channels and playlists
   - To provide you with control over your streams

5. **Error Reporting (Optional)**
   - To diagnose and fix technical issues
   - To improve app stability and performance

---

## Data Storage and Security

### Local Storage on Your Device

**What is stored locally:**
- Your authentication token (JWT) stored securely in iOS Keychain or Android Keystore
- Your preference settings stored in AsyncStorage
- Pending configuration changes when offline (cached in AsyncStorage)
- Some stream data cached for faster loading

**Security Measures:**
- Authentication tokens are stored using platform secure storage APIs
- All data is encrypted at rest on supported devices
- Biometric authentication adds an extra layer of security
- The App does not store sensitive data in plain text

### Data on Your Stream Manager Server

**What is stored on your server:**
- Your account information and credentials (hashed passwords)
- Your stream configuration, channels, and playlists
- Your streaming content and media files
- Your push notification tokens
- Your analytics and usage data

**Important:** Your Stream Manager server is entirely under your control. We do not have access to your server, and we cannot see the data stored on it. This privacy policy only covers the mobile App itself, not your server.

### Data Transmission

- All data transmitted between the App and your server uses HTTPS/TLS encryption
- The App only communicates with your designated Stream Manager server
- No data is transmitted to third-party services

---

## Data Sharing and Disclosure

We do not sell, rent, or share your personal information with third parties for their marketing purposes.

**We may share information in the following limited circumstances:**

1. **Service Providers**
   - We use third-party services to operate the App:
   - **Expo/React Native**: For app framework and development tools
   - **Sentry (if enabled)**: For error reporting and crash analytics
   - **Apple/Google**: For push notification delivery (APNs/FCM)
   - These service providers have access to only the information necessary to perform their functions
   - They are contractually obligated to protect your information

2. **Legal Requirements**
   - If required by law, court order, or government regulation
   - To protect our rights, property, or safety
   - To prevent fraud or illegal activity

3. **Business Transfers**
   - In the event of a merger, acquisition, or sale of assets
   - You will be notified if your information is transferred to a new owner

---

## Third-Party Services and SDKs

The App integrates with the following third-party services:

### 1. Expo / React Native
- **Purpose:** App framework and development platform
- **Data:** May collect anonymous usage statistics and crash reports
- **Privacy Policy:** https://expo.dev/privacy

### 2. Sentry (Optional)
- **Purpose:** Error tracking and crash reporting
- **Data:** Crash reports, error logs, device type, OS version
- **Control:** Can be disabled in app settings
- **Privacy Policy:** https://sentry.io/privacy/

### 3. Apple Push Notification Service (APNs)
- **Purpose:** Deliver push notifications on iOS devices
- **Data:** Device push token, notifications sent by your server
- **Privacy Policy:** https://www.apple.com/privacy/

### 4. Firebase Cloud Messaging (FCM)
- **Purpose:** Deliver push notifications on Android devices
- **Data:** Device push token, notifications sent by your server
- **Privacy Policy:** https://policies.google.com/privacy

### 5. expo-local-authentication
- **Purpose:** Enable Face ID, Touch ID, and fingerprint authentication
- **Data:** Does not access or store biometric data
- **Privacy Policy:** https://docs.expo.dev/versions/latest/sdk/local-authentication/

### 6. expo-secure-store
- **Purpose:** Securely store sensitive data like authentication tokens
- **Data:** Encrypted storage only on device
- **Privacy Policy:** https://docs.expo.dev/versions/latest/sdk/secure-store/

### 7. @react-native-community/netinfo
- **Purpose:** Detect network connection status (online/offline)
- **Data:** Connection type, WiFi/cellular status
- **Privacy Policy:** https://github.com/react-native-netinfo/react-native-netinfo

**Note:** These third-party services have their own privacy policies. We encourage you to review them. We are not responsible for the privacy practices of these third parties.

---

## Data Retention

### Data on Your Device

- Authentication tokens: Retained until you log out
- App settings: Retained until you uninstall the App or change settings
- Cached data: Automatically cleared when no longer needed or when you log out
- Offline changes: Automatically synced to your server and then cleared

You can delete all local app data by:
1. Logging out of the App (clears authentication token)
2. Clearing app data through device settings
3. Uninstalling the App

### Data on Your Stream Manager Server

- Your server is under your complete control
- Data retention on your server is determined by your server configuration
- We have no access to or control over data stored on your server

---

## Your Rights and Choices

You have the following rights regarding your information:

### 1. Access and Review
- You can view all information stored on your Stream Manager server by logging into your web interface
- Local app data can be viewed through the App's settings screen

### 2. Delete Your Data
- **Local app data:** Log out, clear app data in device settings, or uninstall the App
- **Server data:** Delete through your Stream Manager web interface or server administration tools
- Note: Deleting app data does not delete data stored on your server

### 3. Modify Your Data
- You can update your account information through your Stream Manager server
- You can change app settings anytime through the App's settings screen

### 4. Disable Features
- **Push notifications:** Disable in device settings or App settings
- **Biometric authentication:** Disable in App settings
- **Error reporting:** Disable in App settings
- **Offline mode:** Cannot be disabled (core feature), but you can choose not to use it

### 5. Opt-Out of Data Collection
- You can opt out of error reporting by disabling it in App settings
- You can revoke push notification permissions in device settings
- You can revoke biometric authentication in App settings or device settings

### 6. Data Portability
- You can export your data from your Stream Manager server using the web interface
- The App does not provide export functionality as all data resides on your server

### 7. Account Deletion
- To delete your account, use your Stream Manager server's web interface
- Deleting your account on the server will prevent the App from functioning

---

## Children's Privacy

The App is not intended for children under the age of 13. We do not knowingly collect personal information from children under 13. If you are a parent or guardian and believe your child has provided us with personal information, please contact us.

---

## International Data Transfers

The App is designed to connect to your own Stream Manager server, which you host. Data transfer between the App and your server is subject to your server's location and your own data governance policies.

If you enable error reporting (Sentry), error data may be transferred to and processed in the United States or other countries where Sentry's servers are located. By using error reporting, you consent to such transfers.

---

## Changes to This Privacy Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by:

- Posting the new Privacy Policy in the App
- Updating the "Last Updated" date at the top of this policy
- Sending you a notification through the App (if significant changes)

We encourage you to review this Privacy Policy periodically. Your continued use of the App after any changes indicates your acceptance of the updated policy.

---

## California Residents (CCPA)

If you are a resident of California, you have specific rights regarding your personal information:

**The California Consumer Privacy Act (CCPA) provides you with the right to:**
- Know what personal information is collected, used, and shared
- Delete your personal information (subject to certain exceptions)
- Opt-out of the sale of personal information
- Non-discrimination for exercising your privacy rights

**How to Exercise Your CCPA Rights:**
- Contact us using the information below
- Allow up to 45 days for a response

**We Do Not Sell Personal Information**
We do not sell your personal information. However, the App may use third-party services that may collect and use data as described in this policy.

---

## European Residents (GDPR)

If you are a resident of the European Economic Area (EEA) or United Kingdom, you have enhanced rights under the General Data Protection Regulation (GDPR):

**Legal Basis for Processing**
- We process your data based on your consent (when you enable features like push notifications or biometric authentication)
- We process data to perform our contract with you (providing the App functionality)
- We process data for our legitimate interests (improving the App, preventing fraud)

**Your GDPR Rights**
- Right to access your personal data
- Right to rectification of inaccurate data
- Right to erasure ("right to be forgotten")
- Right to restrict processing
- Right to data portability
- Right to object to processing
- Right to withdraw consent
- Right to lodge a complaint with a supervisory authority

**Data Controller**
The controller of your personal data is:
- For the mobile App: The developer of Stream Manager
- For your streaming data: You, as the operator of your Stream Manager server

**Cross-Border Data Transfers**
Data may be transferred to countries outside the EEA. We ensure appropriate safeguards are in place to protect your data.

---

## Security Measures

We implement reasonable and appropriate security measures to protect your information, including:

- Encryption of data in transit using HTTPS/TLS
- Secure storage of authentication tokens using platform secure storage APIs
- Biometric authentication for quick, secure access
- Regular security reviews and updates

However, no method of transmission or storage is completely secure. While we strive to protect your data, we cannot guarantee absolute security.

---

## Contact Us

If you have questions, concerns, or complaints about this Privacy Policy or our data practices, please contact us:

**Email:** privacy@example.com
**Website:** https://example.com/privacy
**GitHub Issues:** https://github.com/example/stream-manager/issues

**Data Protection Officer (EU Residents):**
If you are an EU resident and have GDPR-related concerns, you may also contact our Data Protection Officer at:
- Email: dpo@example.com
- Address: [Your Address]

---

## Complaints

If you believe we have not complied with this Privacy Policy or applicable data protection laws, you have the right to lodge a complaint with:

**Your Local Data Protection Authority:**
- EU: https://edpb.europa.eu/about-edpb/about-edpb/members_en
- UK: ICO (Information Commissioner's Office)
- USA: FTC (Federal Trade Commission)
- Other: Contact your local authority

---

## Consent

By downloading, installing, and using the Stream Manager mobile App, you acknowledge that you have read, understood, and agree to this Privacy Policy. If you do not agree with this policy, please do not use the App.

---

## Additional Information

### Open Source Disclosure

Stream Manager is built using open-source software. The App's source code is available at:
https://github.com/example/stream-manager

### Third-Party Licenses

The App uses the following open-source libraries and components:
- React Native: https://github.com/facebook/react-native (MIT License)
- Expo: https://github.com/expo/expo (MIT License)
- React Navigation: https://github.com/react-navigation/react-navigation (MIT License)
- axios: https://github.com/axios/axios (MIT License)
- i18next: https://github.com/i18next/i18next (MIT License)

Full license information is available in the App's settings screen.

### App Permissions

The App may request the following permissions:

**Required Permissions:**
- **Internet Access:** To communicate with your Stream Manager server
- **Network State:** To detect online/offline status for offline mode
- **Push Notifications:** To receive alerts about your streams

**Optional Permissions:**
- **Biometric Authentication (Face ID, Touch ID, Fingerprint):** For quick, secure login
- **Notification Access:** To receive push notifications about your streams

The App does NOT require access to:
- Your camera
- Your microphone
- Your contacts
- Your location
- Your photos or media files
- Your phone or SMS

---

**Thank you for using Stream Manager!**
