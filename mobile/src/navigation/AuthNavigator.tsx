/**
 * Authentication Navigator
 *
 * Stack navigator for authentication flow.
 * Screens: Login, AuthCallback, PendingApproval
 * Follows patterns from frontend/src/App.tsx routing structure
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { AuthStackParamList } from './types';
import { SplashLoadingScreen } from '../components/SplashLoadingScreen';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { BiometricPromptScreen } from '../screens/auth/BiometricPrompt';

const Stack = createNativeStackNavigator<AuthStackParamList>();

/**
 * Placeholder screens (will be implemented in later subtasks)
 * TODO: Replace with actual screen imports when implemented
 */
const PlaceholderScreen: React.FC = () => {
  return null;
};

export const AuthNavigator: React.FC = () => {
  return (
    <Stack.Navigator
      initialRouteName="Login"
      screenOptions={{
        headerShown: false,
        fullScreenGestureEnabled: true,
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen
        name="Login"
        component={LoginScreen}
        options={{ gestureEnabled: false }}
      />
      <Stack.Screen
        name="AuthCallback"
        component={PlaceholderScreen}
        options={{ gestureEnabled: false }}
      />
      <Stack.Screen
        name="PendingApproval"
        component={PlaceholderScreen}
        options={{ gestureEnabled: false }}
      />
      <Stack.Screen
        name="BiometricPrompt"
        component={BiometricPromptScreen}
        options={{ gestureEnabled: false }}
      />
    </Stack.Navigator>
  );
};

/**
 * Workaround for lazy loading screens in React Navigation
 * We need to create wrapper components that properly handle lazy loading
 */
export const AuthNavigatorWrapper: React.FC = () => {
  // Use the simpler AuthNavigator for now
  // TODO: Implement proper lazy loading when screens are available
  return <AuthNavigator />;
};
