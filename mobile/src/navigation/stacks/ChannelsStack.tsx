/**
 * Channels Stack Navigator
 *
 * Nested stack navigator for Channels tab.
 * Screens: ChannelsList, ChannelDetail, Playlist
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import type { ChannelsStackParamList } from '../types';

const Stack = createNativeStackNavigator<ChannelsStackParamList>();

export const ChannelsStackNavigator: React.FC = () => {
  const { t } = useTranslation();

  // Temporary placeholder component until screens are implemented
  const PlaceholderScreen: React.FC = () => {
    const { View } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff' }}>
        {/* Placeholder - will be replaced with actual screens in subtask-3-4 */}
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
        name="ChannelsList"
        component={PlaceholderScreen as any}
        options={{ title: t('navigation.channels', 'Channels') }}
        initialParams={{ title: t('navigation.channels', 'Channels') }}
      />
      <Stack.Screen
        name="ChannelDetail"
        component={PlaceholderScreen as any}
        options={{ title: t('navigation.channelDetail', 'Channel Details') }}
      />
      <Stack.Screen
        name="Playlist"
        component={PlaceholderScreen as any}
        options={{ title: t('navigation.playlist', 'Playlist') }}
      />
    </Stack.Navigator>
  );
};
