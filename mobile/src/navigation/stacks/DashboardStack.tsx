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

// Placeholder screens (will be implemented in later subtasks)
const DashboardHomeScreen = React.lazy(() =>
  import('../../screens/dashboard/DashboardScreen').then((m) => ({
    default: m.DashboardScreen,
  }))
);

const AnalyticsScreen = React.lazy(() =>
  import('../../screens/analytics/AnalyticsScreen').then((m) => ({
    default: m.AnalyticsScreen,
  }))
);

const MonitoringScreen = React.lazy(() =>
  import('../../screens/monitoring/MonitoringScreen').then((m) => ({
    default: m.MonitoringScreen,
  }))
);

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

  // Temporary placeholder component until screens are implemented
  const PlaceholderScreen: React.FC = () => {
    const { View } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff' }}>
        {/* Placeholder - will be replaced with actual screens in subtask-3-3 */}
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
        component={PlaceholderScreen as any}
        options={{ title: t('navigation.dashboard', 'Dashboard') }}
      />

      {/* Analytics - Available to MODERATOR and above */}
      <Stack.Screen
        name="Analytics"
        options={{ title: t('navigation.analytics', 'Analytics') }}
      >
        {(props) => (
          <ProtectedRoute
            allowedRoles={MODERATOR_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen as any}
            {...props}
          />
        )}
      </Stack.Screen>

      {/* Monitoring - Available to MODERATOR and above */}
      <Stack.Screen
        name="Monitoring"
        options={{ title: t('navigation.monitoring', 'Monitoring') }}
      >
        {(props) => (
          <ProtectedRoute
            allowedRoles={MODERATOR_AND_ABOVE}
            userRole={userRole}
            component={PlaceholderScreen as any}
            {...props}
          />
        )}
      </Stack.Screen>
    </Stack.Navigator>
  );
};
