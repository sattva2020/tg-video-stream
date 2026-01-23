/**
 * Tab Navigator
 *
 * Bottom tab navigator for main app sections.
 * Tabs: Dashboard, Channels, Schedule, Notifications, Settings
 * Follows patterns from frontend/src/App.tsx with role-based access control
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import type { MainTabParamList, UserRole } from './types';

// Import tab screens (using stack navigators for each tab)
import { DashboardStackNavigator } from './stacks/DashboardStack';
import { ChannelsStackNavigator } from './stacks/ChannelsStack';
import { ScheduleStackNavigator } from './stacks/ScheduleStack';
import { NotificationsStackNavigator } from './stacks/NotificationsStack';
import { SettingsStackNavigator } from './stacks/SettingsStack';

const Tab = createBottomTabNavigator<MainTabParamList>();

interface TabNavigatorProps {
  userRole?: UserRole;
}

/**
 * Role groups for RBAC (matching frontend pattern)
 */
const OPERATOR_AND_ABOVE: UserRole[] = [
  UserRole.SUPERADMIN,
  UserRole.ADMIN,
  UserRole.MODERATOR,
  UserRole.OPERATOR,
];

const ADMIN_AND_ABOVE: UserRole[] = [UserRole.SUPERADMIN, UserRole.ADMIN];
const MODERATOR_AND_ABOVE: UserRole[] = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR];

/**
 * Check if user's role is in the allowed roles list
 */
const hasRoleAccess = (userRole: UserRole | undefined, allowedRoles: UserRole[]): boolean => {
  if (!userRole) return false;
  return allowedRoles.includes(userRole);
};

export const TabNavigator: React.FC<TabNavigatorProps> = ({ userRole }) => {
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#06b6d4',
        tabBarInactiveTintColor: '#6b7280',
        tabBarStyle: {
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      }}
    >
      {/* Dashboard - Available to all authenticated users */}
      <Tab.Screen
        name="Dashboard"
        component={DashboardStackNavigator}
        options={{
          tabBarLabel: t('navigation.dashboard', 'Dashboard'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="grid-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Channels - Available to OPERATOR and above */}
      {hasRoleAccess(userRole, OPERATOR_AND_ABOVE) && (
        <Tab.Screen
          name="Channels"
          component={ChannelsStackNavigator}
          options={{
            tabBarLabel: t('navigation.channels', 'Channels'),
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="radio-outline" size={size} color={color} />
            ),
          }}
        />
      )}

      {/* Schedule - Available to OPERATOR and above */}
      {hasRoleAccess(userRole, OPERATOR_AND_ABOVE) && (
        <Tab.Screen
          name="Schedule"
          component={ScheduleStackNavigator}
          options={{
            tabBarLabel: t('navigation.schedule', 'Schedule'),
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="calendar-outline" size={size} color={color} />
            ),
          }}
        />
      )}

      {/* Notifications - Available to OPERATOR and above */}
      {hasRoleAccess(userRole, OPERATOR_AND_ABOVE) && (
        <Tab.Screen
          name="Notifications"
          component={NotificationsStackNavigator}
          options={{
            tabBarLabel: t('navigation.notifications', 'Notifications'),
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="notifications-outline" size={size} color={color} />
            ),
            tabBarBadge: undefined, // TODO: Add unread notification count
          }}
        />
      )}

      {/* Settings - Available to all authenticated users */}
      <Tab.Screen
        name="Settings"
        component={SettingsStackNavigator}
        options={{
          tabBarLabel: t('navigation.settings', 'Settings'),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};
