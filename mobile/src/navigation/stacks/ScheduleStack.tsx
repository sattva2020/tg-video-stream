/**
 * Schedule Stack Navigator
 *
 * Nested stack navigator for Schedule tab.
 * Screens: ScheduleList, ScheduleDetail
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { ScheduleStackParamList } from '../types';

const Stack = createNativeStackNavigator<ScheduleStackParamList>();

export const ScheduleStackNavigator: React.FC = () => {
  const { t } = useTranslation();

  // Temporary placeholder component until screens are implemented
  const PlaceholderScreen: React.FC = () => {
    const { View } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff' }}>
        {/* Placeholder - will be replaced with actual screens */}
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
        name="ScheduleList"
        component={PlaceholderScreen}
        options={{ title: t('navigation.schedule', 'Schedule') }}
      />
      <Stack.Screen
        name="ScheduleDetail"
        component={PlaceholderScreen}
        options={{ title: t('navigation.scheduleDetail', 'Schedule Details') }}
      />
    </Stack.Navigator>
  );
};
