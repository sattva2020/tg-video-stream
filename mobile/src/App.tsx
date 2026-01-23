/**
 * Sattva Streamer Mobile App
 *
 * Основной компонент приложения для управления стримами на мобильных устройствах.
 * Main app component for managing streams on mobile devices.
 *
 * Follows patterns from frontend/src/main.tsx
 */

import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { View, Text, StyleSheet } from 'react-native';
import './i18n'; // Initialize i18n before anything else
import { AuthProvider } from './contexts/AuthContext';
import { AppNavigator } from './navigation/AppNavigator';

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
 * Root component with providers
 */
const Root: React.FC = () => (
  <AuthProvider>
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
