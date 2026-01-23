/**
 * Notification Handlers
 *
 * Utilities for handling push notifications and notification-related operations.
 * Uses expo-notifications for cross-platform push notification support.
 *
 * Features:
 * - Handle incoming notifications
 * - Handle notification taps
 * - Register device for push notifications
 * - Get notification permission status
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { mobileApi } from '../api/mobile';
import * as Application from 'expo-application';
import * as Device from 'expo-device';

/**
 * Configure notification behavior
 */
export const configureNotifications = (): void => {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });
};

/**
 * Request push notification permissions
 */
export const requestNotificationPermissions = async (): Promise<boolean> => {
  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    return finalStatus === 'granted';
  } catch (error) {
    console.error('Failed to request notification permissions:', error);
    return false;
  }
};

/**
 * Get push notification token
 */
export const getPushToken = async (): Promise<string | null> => {
  try {
    const projectId = Process.env.EXPO_PROJECT_ID;

    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#FF231F7C',
      });
    }

    const { data: token } = await Notifications.getExpoPushTokenAsync({
      projectId,
    });

    return token;
  } catch (error) {
    console.error('Failed to get push token:', error);
    return null;
  }
};

/**
 * Get device ID
 */
export const getDeviceId = async (): Promise<string> => {
  try {
    return Application.getAndroidId() || Application.androidId || Application.applicationId;
  } catch (error) {
    // Fallback to a random ID if device ID is not available
    return `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
};

/**
 * Get platform name
 */
export const getPlatformName = (): 'ios' | 'android' => {
  return Platform.OS === 'ios' ? 'ios' : 'android';
};

/**
 * Get app version
 */
export const getAppVersion = (): string => {
  const appVersion = Application.nativeApplicationVersion;
  return appVersion || '0.0.0';
};

/**
 * Get OS version
 */
export const getOsVersion = (): string => {
  return `${Device.osVersion} ${Platform.OS}`;
};

/**
 * Register device for push notifications with backend
 */
export const registerForPushNotifications = async (): Promise<{
  success: boolean;
  token?: string;
  error?: string;
}> => {
  try {
    // Request permissions
    const hasPermission = await requestNotificationPermissions();
    if (!hasPermission) {
      return {
        success: false,
        error: 'Notification permissions not granted',
      };
    }

    // Get push token
    const token = await getPushToken();
    if (!token) {
      return {
        success: false,
        error: 'Failed to get push token',
      };
    }

    // Get device info
    const deviceId = await getDeviceId();
    const platform = getPlatformName();
    const appVersion = getAppVersion();
    const osVersion = getOsVersion();

    // Register with backend
    await mobileApi.registerDevice({
      device_id: deviceId,
      platform,
      push_token: token,
      app_version: appVersion,
      os_version: osVersion,
    });

    return {
      success: true,
      token,
    };
  } catch (error: any) {
    console.error('Failed to register for push notifications:', error);
    return {
      success: false,
      error: error.message || 'Failed to register for push notifications',
    };
  }
};

/**
 * Add notification received listener
 */
export const addNotificationReceivedListener = (
  callback: (notification: Notifications.Notification) => void
): Notifications.Subscription => {
  return Notifications.addNotificationReceivedListener(callback);
};

/**
 * Add notification response received listener (tap handler)
 */
export const addNotificationResponseReceivedListener = (
  callback: (response: Notifications.NotificationResponse) => void
): Notifications.Subscription => {
  return Notifications.addNotificationResponseReceivedListener(callback);
};

/**
 * Get badge count
 */
export const getBadgeCount = async (): Promise<number> => {
  try {
    return await Notifications.getBadgeCountAsync();
  } catch (error) {
    return 0;
  }
};

/**
 * Set badge count
 */
export const setBadgeCount = async (count: number): Promise<void> => {
  try {
    await Notifications.setBadgeCountAsync(count);
  } catch (error) {
    console.error('Failed to set badge count:', error);
  }
};

/**
 * Dismiss all notifications
 */
export const dismissAllNotifications = async (): Promise<void> => {
  try {
    await Notifications.dismissAllNotificationsAsync();
  } catch (error) {
    console.error('Failed to dismiss notifications:', error);
  }
};

/**
 * Cancel all scheduled notifications
 */
export const cancelAllScheduledNotifications = async (): Promise<void> => {
  try {
    await Notifications.cancelAllScheduledNotificationsAsync();
  } catch (error) {
    console.error('Failed to cancel scheduled notifications:', error);
  }
};

/**
 * Schedule local notification
 */
export const scheduleLocalNotification = async (
  title: string,
  body: string,
  data?: Record<string, unknown>
): Promise<string> => {
  try {
    const { identifier } = await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data: data || {},
        sound: true,
      },
      trigger: null, // Show immediately
    });

    return identifier;
  } catch (error) {
    console.error('Failed to schedule notification:', error);
    throw error;
  }
};
