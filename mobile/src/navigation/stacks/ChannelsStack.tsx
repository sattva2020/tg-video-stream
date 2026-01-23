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
import ChannelManagerScreen from '../../screens/channels/ChannelManagerScreen';

const Stack = createNativeStackNavigator<ChannelsStackParamList>();

export const ChannelsStackNavigator: React.FC = () => {
  const { t } = useTranslation();

  // Temporary placeholder component for screens not yet implemented
  const PlaceholderScreen: React.FC = () => {
    const { View, Text } = require('react-native');
    return (
      <View style={{ flex: 1, backgroundColor: '#fff', justifyContent: 'center', alignItems: 'center' }}>
        <Text>Screen not yet implemented</Text>
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
        component={ChannelManagerScreen}
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
