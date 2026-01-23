/**
 * usePushNotifications Hook
 *
 * Custom hook for managing push notifications.
 * Handles permission requests, token registration, and notification listeners.
 * Supports background operation and notification tap handling.
 *
 * Usage:
 * ```tsx
 * const { expoPushToken, notification } = usePushNotifications();
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import * as Notifications from 'expo-notifications';
import type { Subscription } from 'expo-notifications';
import type { NavigationProp } from '@react-navigation/native';
import {
  configureNotifications,
  registerForPushNotifications,
  addNotificationReceivedListener,
  addNotificationResponseReceivedListener,
  getPushToken,
} from '../utils/notificationHandlers';

// Configure notification behavior on module load
configureNotifications();

export interface NotificationData {
  type?: string;
  channelId?: number;
  streamId?: number;
  userId?: string;
  screen?: string;
  [key: string]: unknown;
}

interface UsePushNotificationsReturn {
  expoPushToken: string | null;
  notification: Notifications.Notification | null;
  isRegistered: boolean;
  error: string | null;
  appState: AppStateStatus;
  lastNotificationData: NotificationData | null;
  register: () => Promise<void>;
  handleNotificationTap: (data: NotificationData) => void;
  setNavigation: (navigation: NavigationProp<any>) => void;
}

export const usePushNotifications = (): UsePushNotificationsReturn => {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notifications.Notification | null>(null);
  const [isRegistered, setIsRegistered] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [appState, setAppState] = useState<AppStateStatus>(AppState.currentState);
  const [lastNotificationData, setLastNotificationData] = useState<NotificationData | null>(null);

  const navigationRef = useRef<NavigationProp<any> | null>(null);
  const notificationListener = useRef<Subscription>();
  const responseListener = useRef<Subscription>();
  const initialNotificationHandled = useRef(false);

  /**
   * Register for push notifications
   */
  const register = useCallback(async (): Promise<void> => {
    try {
      setError(null);

      // Request permissions and register with backend
      const result = await registerForPushNotifications();

      if (result.success && result.token) {
        setExpoPushToken(result.token);
        setIsRegistered(true);
      } else {
        setError(result.error || 'Failed to register for push notifications');
        setIsRegistered(false);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to register for push notifications';
      setError(errorMessage);
      setIsRegistered(false);
      console.error('Push notification registration error:', err);
    }
  }, []);

  /**
   * Set navigation reference for handling notification taps
   */
  const setNavigation = useCallback((navigation: NavigationProp<any>) => {
    navigationRef.current = navigation;
  }, []);

  /**
   * Handle notification tap - navigate to appropriate screen
   */
  const handleNotificationTap = useCallback((data: NotificationData) => {
    if (!navigationRef.current) {
      // Store notification data if navigation is not ready yet
      setLastNotificationData(data);
      return;
    }

    const navigation = navigationRef.current;
    const type = data.type || data.screen;

    // Navigate based on notification type
    switch (type) {
      case 'channel':
      case 'stream':
        if (data.channelId) {
          navigation.navigate('Main', {
            screen: 'Channels',
            params: {
              screen: 'ChannelDetail',
              params: { channelId: String(data.channelId) },
            },
          });
        } else {
          // Navigate to channels list if no specific channel
          navigation.navigate('Main', { screen: 'Channels' });
        }
        break;

      case 'playlist':
        if (data.channelId) {
          navigation.navigate('Main', {
            screen: 'Channels',
            params: {
              screen: 'Playlist',
              params: { channelId: String(data.channelId) },
            },
          });
        }
        break;

      case 'schedule':
        navigation.navigate('Main', { screen: 'Schedule' });
        break;

      case 'notification':
      case 'alert':
        navigation.navigate('Main', { screen: 'Notifications' });
        break;

      case 'settings':
        navigation.navigate('Main', { screen: 'Settings' });
        break;

      default:
        // Navigate to dashboard by default
        navigation.navigate('Main', { screen: 'Dashboard' });
        break;
    }

    // Clear stored notification data after handling
    setLastNotificationData(null);
  }, []);

  useEffect(() => {
    // Register for push notifications on mount
    void register();

    // Listen for app state changes
    const subscription = AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
      setAppState(nextAppState);

      // When app comes to foreground, check if there's a pending notification to handle
      if (nextAppState === 'active' && lastNotificationData && navigationRef.current) {
        handleNotificationTap(lastNotificationData);
      }
    });

    // Listen for incoming notifications (foreground)
    notificationListener.current = addNotificationReceivedListener((receivedNotification) => {
      setNotification(receivedNotification);
    });

    // Listen for notification taps (foreground, background, and quit state)
    responseListener.current = addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as NotificationData;

      // Update the last notification
      setNotification(response.notification);
      setLastNotificationData(data);

      // Handle navigation if app is active and navigation is ready
      if (appState === 'active' && navigationRef.current) {
        handleNotificationTap(data);
      }
      // If app is in background or killed, the notification will be handled when app becomes active
    });

    // Check if app was opened from a notification tap (when launched from quit state)
    void (async () => {
      if (!initialNotificationHandled.current) {
        const initialNotification = await Notifications.getLastNotificationResponseAsync();
        if (initialNotification) {
          const data = initialNotification.notification.request.content.data as NotificationData;
          setLastNotificationData(data);

          // Handle navigation if navigation is ready
          if (navigationRef.current) {
            handleNotificationTap(data);
          }
        }
        initialNotificationHandled.current = true;
      }
    })();

    // Cleanup listeners on unmount
    return () => {
      subscription.remove();
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, [register, appState, handleNotificationTap, lastNotificationData]);

  return {
    expoPushToken,
    notification,
    isRegistered,
    error,
    appState,
    lastNotificationData,
    register,
    handleNotificationTap,
    setNavigation,
  };
};
