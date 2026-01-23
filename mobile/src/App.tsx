/**
 * Sattva Streamer Mobile App
 *
 * Основной компонент приложения для управления стримами на мобильных устройствах.
 * Main app component for managing streams on mobile devices.
 *
 * Follows patterns from frontend/src/main.tsx
 */

import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { View, Text, StyleSheet } from 'react-native';
import './i18n'; // Initialize i18n before anything else
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OfflineProvider } from './contexts/OfflineContext';
import { AppNavigator } from './navigation/AppNavigator';
import { usePushNotifications } from './hooks/usePushNotifications';
import { useNetworkStatus } from './hooks/useNetworkStatus';
import { OfflineBanner } from './components/OfflineBanner';

/**
 * Error boundary fallback component
 */
const ErrorFallback: React.FC<{ error: Error }> = ({ error }) => {
  return (
    <View style={styles.errorContainer}>
      <Text style={styles.errorTitle}>Something went wrong</Text>
      <Text style={styles.errorMessage}>{error.message}</Text>
    </View>
  );
};

/**
 * Push notification initializer component
 * Handles push notification registration when user is authenticated
 */
const PushNotificationInitializer: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { isRegistered } = usePushNotifications();

  // Push notification registration is handled automatically by the hook
  // This component ensures registration when user is authenticated
  useEffect(() => {
    if (isAuthenticated && isRegistered) {
      // Successfully registered for push notifications
      // Token is available in the hook and can be sent to backend
    }
  }, [isAuthenticated, isRegistered]);

  return null; // This component doesn't render anything
};

/**
 * Network status wrapper component
 * Monitors network status and displays offline banner
 */
const NetworkStatusWrapper: React.FC = () => {
  const { isOnline, connectionType } = useNetworkStatus();

  return <OfflineBanner isOnline={isOnline} connectionType={connectionType} />;
};

/**
 * Component that manages navigation ref for push notifications
 */
const NavigationManager: React.FC = () => {
  const navigationRef = React.useRef<any>(null);
  const { setNavigation } = usePushNotifications();

  useEffect(() => {
    if (navigationRef.current) {
      setNavigation(navigationRef.current);
    }
  }, [setNavigation]);

  return <AppNavigator navigationRef={navigationRef} />;
};

/**
 * Root component with providers
 */
const Root: React.FC = () => (
  <OfflineProvider>
    <AuthProvider>
      <NetworkStatusWrapper />
      <PushNotificationInitializer />
      <NavigationManager />
    </AuthProvider>
  </OfflineProvider>
);

/**
 * Main App component
 * Sets up providers and renders the application
 */
export default function App() {
  try {
    return (
      <SafeAreaProvider>
        <Root />
        <StatusBar style="auto" />
      </SafeAreaProvider>
    );
  } catch (error) {
    console.error('App initialization error:', error);
    return <ErrorFallback error={error as Error} />;
  }
}

const styles = StyleSheet.create({
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 20,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#dc2626',
  },
  errorMessage: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
  },
});
