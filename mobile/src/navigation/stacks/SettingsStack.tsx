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
import SettingsScreen from '../../screens/SettingsScreen';

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

// Placeholder component for screens not yet implemented
const PlaceholderScreen: React.FC = () => {
  const { View, Text } = require('react-native');
  return (
    <View style={{ flex: 1, backgroundColor: '#f9fafb', justifyContent: 'center', alignItems: 'center' }}>
      <Text style={{ color: '#6b7280', fontSize: 16 }}>Coming soon</Text>
    </View>
  );
};

export const SettingsStackNavigator: React.FC<SettingsStackProps> = ({ userRole }) => {
  const { t } = useTranslation();

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
        component={SettingsScreen}
        options={{ title: t('settings.title', 'Settings') }}
      />
      <Stack.Screen
        name="Profile"
        component={PlaceholderScreen}
        options={{ title: t('settings.profile', 'Profile') }}
      />
      <Stack.Screen
        name="Language"
        component={PlaceholderScreen}
        options={{ title: t('settings.language', 'Language') }}
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
