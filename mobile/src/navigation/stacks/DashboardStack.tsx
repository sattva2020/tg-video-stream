/**
 * Dashboard Stack Navigator
 *
 * Nested stack navigator for Dashboard tab.
 * Screens: DashboardHome, Analytics, Monitoring
 * Follows role-based access patterns from frontend
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { DashboardStackParamList, UserRole } from '../types';
import { ProtectedRoute } from '../components/ProtectedRoute';

// Screens
import DashboardScreen from '../../screens/DashboardScreen';

const Stack = createNativeStackNavigator<DashboardStackParamList>();

interface DashboardStackProps {
  userRole?: UserRole;
}

const MODERATOR_AND_ABOVE: UserRole[] = [
  'superadmin' as UserRole,
  'admin' as UserRole,
  'moderator' as UserRole,
];

export const DashboardStackNavigator: React.FC<DashboardStackProps> = ({ userRole }) => {
  const { t } = useTranslation();

  // Placeholder component for Analytics and Monitoring (to be implemented in later subtasks)
  const PlaceholderScreen: React.FC<{ title: string }> = ({ title }) => {
    const { View, Text } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff', justifyContent: 'center', alignItems: 'center' }}>
        <Text style={{ fontSize: 16, color: '#6b7280' }}>{title}</Text>
        <Text style={{ fontSize: 14, color: '#9ca3af', marginTop: 8 }}>
          {t('common.comingSoon', 'Coming soon')}
        </Text>
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
        name="DashboardHome"
        component={DashboardScreen}
        options={{ title: t('nav.dashboard', 'Dashboard') }}
      />

      {/* Analytics - Available to MODERATOR and above */}
      <Stack.Screen
        name="Analytics"
        options={{ title: t('nav.analytics', 'Analytics') }}
      >
        {(props) => (
          <ProtectedRoute
            allowedRoles={MODERATOR_AND_ABOVE}
            userRole={userRole}
            component={() => <PlaceholderScreen title={t('nav.analytics', 'Analytics')} />}
            {...props}
          />
        )}
      </Stack.Screen>

      {/* Monitoring - Available to MODERATOR and above */}
      <Stack.Screen
        name="Monitoring"
        options={{ title: t('nav.monitoring', 'Monitoring') }}
      >
        {(props) => (
          <ProtectedRoute
            allowedRoles={MODERATOR_AND_ABOVE}
            userRole={userRole}
            component={() => <PlaceholderScreen title={t('nav.monitoring', 'Monitoring')} />}
            {...props}
          />
        )}
      </Stack.Screen>
    </Stack.Navigator>
  );
};
