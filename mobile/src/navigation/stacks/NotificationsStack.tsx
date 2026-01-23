/**
 * Notifications Stack Navigator
 *
 * Nested stack navigator for Notifications tab.
 * Screens: NotificationsHome, NotificationChannels, NotificationRules, etc.
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { NotificationsStackParamList } from '../types';

const Stack = createNativeStackNavigator<NotificationsStackParamList>();

export const NotificationsStackNavigator: React.FC = () => {
  const { t } = useTranslation();

  // Temporary placeholder component until screens are implemented
  const PlaceholderScreen: React.FC = () => {
    const { View } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff' }}>
        {/* Placeholder - will be replaced with actual screens in subtask-4-2 */}
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
        name="NotificationsHome"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notifications', 'Notifications') }}
      />
      <Stack.Screen
        name="NotificationChannels"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationChannels', 'Channels') }}
      />
      <Stack.Screen
        name="NotificationRules"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationRules', 'Rules') }}
      />
      <Stack.Screen
        name="NotificationLogs"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationLogs', 'Logs') }}
      />
      <Stack.Screen
        name="NotificationTemplates"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationTemplates', 'Templates') }}
      />
      <Stack.Screen
        name="NotificationRecipients"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationRecipients', 'Recipients') }}
      />
    </Stack.Navigator>
  );
};
