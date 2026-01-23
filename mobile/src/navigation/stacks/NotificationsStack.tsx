/**
 * Notifications Stack Navigator
 *
 * Nested stack navigator for Notifications tab.
 * Screens: NotificationsHome (delivery logs), NotificationRules, etc.
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { NotificationsStackParamList } from '../types';

// Screens
import NotificationsScreen from '../../screens/NotificationsScreen';
import NotificationRulesScreen from '../../screens/NotificationRulesScreen';

const Stack = createNativeStackNavigator<NotificationsStackParamList>();

// Temporary placeholder component for unimplemented screens
const PlaceholderScreen: React.FC = () => {
  const { View, Text } = require('react-native');
  return (
    <View style={{ flex: 1, backgroundColor: '#fff', justifyContent: 'center', alignItems: 'center' }}>
      <Text style={{ fontSize: 16, color: '#6b7280' }}>
        Coming soon
      </Text>
    </View>
  );
};

export const NotificationsStackNavigator: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false, // Use custom headers in screens
      }}
    >
      <Stack.Screen
        name="NotificationsHome"
        component={NotificationsScreen}
        options={{ title: t('navigation.notifications', 'Notifications') }}
      />
      <Stack.Screen
        name="NotificationChannels"
        component={PlaceholderScreen}
        options={{ title: t('navigation.notificationChannels', 'Channels') }}
      />
      <Stack.Screen
        name="NotificationRules"
        component={NotificationRulesScreen}
        options={{ title: t('navigation.notificationRules', 'Rules') }}
      />
      <Stack.Screen
        name="NotificationLogs"
        component={NotificationsScreen}
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
