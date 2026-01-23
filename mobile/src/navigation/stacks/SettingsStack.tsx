/**
 * Settings Stack Navigator
 *
 * Nested stack navigator for Settings tab.
 * Screens: SettingsHome, Profile, Language, AdminSettings, Users, Incidents, StreamQuality
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { SettingsStackParamList, UserRole } from '../types';
import { ProtectedRoute } from '../components/ProtectedRoute';

const Stack = createNativeStackNavigator<SettingsStackParamList>();

interface SettingsStackProps {
  userRole?: UserRole;
}

const ADMIN_AND_ABOVE: UserRole[] = ['superadmin' as UserRole, 'admin' as UserRole];
const MODERATOR_AND_ABOVE: UserRole[] = [
  'superadmin' as UserRole,
  'admin' as UserRole,
  'moderator' as UserRole,
];

export const SettingsStackNavigator: React.FC<SettingsStackProps> = ({ userRole }) => {
  const { t } = useTranslation();

  // Temporary placeholder component until screens are implemented
  const PlaceholderScreen: React.FC = () => {
    const { View } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff' }}>
        {/* Placeholder - will be replaced with actual screens in subtask-5-2 */}
      </View>
    );
  };

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: true,
        headerStyle: {
          backgroundColor: '#06b6d4',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: '600',
        },
      }}
    >
      <Stack.Screen
        name="SettingsHome"
        component={PlaceholderScreen}
        options={{ title: t('navigation.settings', 'Settings') }}
      />
      <Stack.Screen
        name="Profile"
        component={PlaceholderScreen}
        options={{ title: t('navigation.profile', 'Profile') }}
      />
      <Stack.Screen
        name="Language"
        component={PlaceholderScreen}
        options={{ title: t('navigation.language', 'Language') }}
      />

      {/* Admin Settings - Available to ADMIN and above */}
      <Stack.Screen name="AdminSettings">
        {(props) => (
          <ProtectedRoute
            allowedRoles={ADMIN_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen}
            {...props}
          />
        )}
      </Stack.Screen>

      {/* Users - Available to ADMIN and above */}
      <Stack.Screen name="Users">
        {(props) => (
          <ProtectedRoute
            allowedRoles={ADMIN_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen}
            {...props}
          />
        )}
      </Stack.Screen>

      {/* Incidents - Available to MODERATOR and above */}
      <Stack.Screen name="Incidents">
        {(props) => (
          <ProtectedRoute
            allowedRoles={MODERATOR_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen}
            {...props}
          />
        )}
      </Stack.Screen>

      {/* Stream Quality - Available to ADMIN and above */}
      <Stack.Screen name="StreamQuality">
        {(props) => (
          <ProtectedRoute
            allowedRoles={ADMIN_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen}
            {...props}
          />
        )}
      </Stack.Screen>
    </Stack.Navigator>
  );
};
