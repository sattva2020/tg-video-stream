/**
 * App Navigator
 *
 * Root navigator that manages authentication state and routing.
 * Switches between AuthNavigator and TabNavigator based on auth state.
 * Follows patterns from frontend/src/App.tsx with AuthProvider and protected routes
 */

import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import type { RootStackParamList, UserRole } from './types';
import { AuthNavigatorWrapper } from './AuthNavigator';
import { TabNavigator } from './TabNavigator';
import { SplashLoadingScreen } from '../components/SplashLoadingScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * Context for authentication state (simplified - will be replaced by AuthContext)
 */
interface AuthStateContextValue {
  isAuthenticated: boolean;
  userRole: UserRole | undefined;
  isLoading: boolean;
}

const AuthStateContext = React.createContext<AuthStateContextValue>({
  isAuthenticated: false,
  userRole: undefined,
  isLoading: true,
});

/**
 * Root navigation component
 * Handles authentication flow and main app navigation
 */
export const AppNavigator: React.FC = () => {
  const { i18n } = useTranslation();
  const [authState, setAuthState] = useState<AuthStateContextValue>({
    isAuthenticated: false,
    userRole: undefined,
    isLoading: true,
  });

  useEffect(() => {
    // Check authentication status on mount
    // TODO: Replace with actual AuthContext when available
    const checkAuthStatus = async () => {
      try {
        // Simulate async auth check
        await new Promise((resolve) => setTimeout(resolve, 100));

        // TODO: Check secure storage for auth token
        // const token = await SecureStore.getItemAsync('authToken');
        // const userRole = await SecureStore.getItemAsync('userRole');

        // For now, default to not authenticated
        setAuthState({
          isAuthenticated: false,
          userRole: undefined,
          isLoading: false,
        });
      } catch (error) {
        console.error('Error checking auth status:', error);
        setAuthState({
          isAuthenticated: false,
          userRole: undefined,
          isLoading: false,
        });
      }
    };

    checkAuthStatus();
  }, []);

  if (authState.isLoading) {
    return <SplashLoadingScreen />;
  }

  return (
    <AuthStateContext.Provider value={authState}>
      <NavigationContainer>
        <Stack.Navigator
          screenOptions={{
            headerShown: false,
            fullScreenGestureEnabled: true,
          }}
        >
          {authState.isAuthenticated ? (
            // Authenticated flow - Main app with tabs
            <Stack.Screen
              name="Main"
              options={{ gestureEnabled: false }}
            >
              {() => <TabNavigator userRole={authState.userRole} />}
            </Stack.Screen>
          ) : (
            // Authentication flow
            <Stack.Screen
              name="Auth"
              component={AuthNavigatorWrapper}
              options={{ gestureEnabled: false }}
            />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </AuthStateContext.Provider>
  );
};

/**
 * Loading screen component (temporary until SplashLoadingScreen is created)
 */
const TemporaryLoadingScreen: React.FC = () => {
  return (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color="#06b6d4" />
    </View>
  );
};

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
});

export default AppNavigator;
