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
import { AppNavigator } from './navigation/AppNavigator';
import { usePushNotifications } from './hooks/usePushNotifications';

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
  const { expoPushToken, isRegistered, error } = usePushNotifications();

  useEffect(() => {
    if (isAuthenticated && isRegistered && expoPushToken) {
      // Successfully registered for push notifications
      console.log('Push notifications registered:', expoPushToken);
    }

    if (error) {
      console.error('Push notification error:', error);
    }
  }, [isAuthenticated, isRegistered, expoPushToken, error]);

  return null; // This component doesn't render anything
};

/**
 * Root component with providers
 */
const Root: React.FC = () => (
  <AuthProvider>
    <PushNotificationInitializer />
    <AppNavigator />
  </AuthProvider>
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
