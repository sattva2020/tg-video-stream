/**
 * usePushNotifications Hook
 *
 * Custom hook for managing push notifications.
 * Handles permission requests, token registration, and notification listeners.
 *
 * Usage:
 * ```tsx
 * const { expoPushToken, notification } = usePushNotifications();
 * ```
 */

import { useState, useEffect, useRef } from 'react';
import * as Notifications from 'expo-notifications';
import type { Subscription } from 'expo-notifications';
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
  [key: string]: unknown;
}

interface UsePushNotificationsReturn {
  expoPushToken: string | null;
  notification: Notifications.Notification | null;
  isRegistered: boolean;
  error: string | null;
  register: () => Promise<void>;
}

export const usePushNotifications = (): UsePushNotificationsReturn => {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notifications.Notification | null>(null);
  const [isRegistered, setIsRegistered] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const notificationListener = useRef<Subscription>();
  const responseListener = useRef<Subscription>();

  /**
   * Register for push notifications
   */
  const register = async (): Promise<void> => {
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
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to register for push notifications';
      setError(errorMessage);
      setIsRegistered(false);
      console.error('Push notification registration error:', err);
    }
  };

  useEffect(() => {
    // Register for push notifications on mount
    void register();

    // Listen for incoming notifications
    notificationListener.current = addNotificationReceivedListener((notification) => {
      setNotification(notification);
    });

    // Listen for notification taps
    responseListener.current = addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as NotificationData;

      // Handle navigation based on notification data
      // Example: navigate to specific screen based on data.type
      console.log('Notification tapped:', data);

      setNotification(response.notification);
    });

    // Cleanup listeners on unmount
    return () => {
      notificationListener.current?.remove();
      responseListener.current?.remove();
    };
  }, []);

  return {
    expoPushToken,
    notification,
    isRegistered,
    error,
    register,
  };
};
