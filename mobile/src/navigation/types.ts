/**
 * Navigation Types
 *
 * Type definitions for React Navigation in the mobile app.
 * Follows patterns from frontend routing structure.
 */

import type { NavigatorScreenParams } from '@react-navigation/native';

/**
 * User roles matching the backend and frontend
 */
export enum UserRole {
  SUPERADMIN = 'superadmin',
  ADMIN = 'admin',
  MODERATOR = 'moderator',
  OPERATOR = 'operator',
  USER = 'user',
}

/**
 * Root stack param list
 */
export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
  Splash: undefined;
};

/**
 * Authentication stack param list
 */
export type AuthStackParamList = {
  Login: undefined;
  AuthCallback: { token?: string };
  PendingApproval: undefined;
  BiometricPrompt: { email: string };
};

/**
 * Main tab navigator param list
 */
export type MainTabParamList = {
  Dashboard: undefined;
  Channels: undefined;
  Schedule: undefined;
  Notifications: undefined;
  Settings: undefined;
};

/**
 * Dashboard stack param list (nested in Dashboard tab)
 */
export type DashboardStackParamList = {
  DashboardHome: undefined;
  Analytics: undefined;
  Monitoring: undefined;
};

/**
 * Channels stack param list (nested in Channels tab)
 */
export type ChannelsStackParamList = {
  ChannelsList: undefined;
  ChannelDetail: { channelId: string };
  Playlist: { channelId: string };
};

/**
 * Schedule stack param list (nested in Schedule tab)
 */
export type ScheduleStackParamList = {
  ScheduleList: undefined;
  ScheduleDetail: { scheduleId: string };
};

/**
 * Notifications stack param list (nested in Notifications tab)
 */
export type NotificationsStackParamList = {
  NotificationsHome: undefined;
  NotificationChannels: undefined;
  NotificationRules: undefined;
  NotificationLogs: undefined;
  NotificationTemplates: undefined;
  NotificationRecipients: undefined;
};

/**
 * Settings stack param list (nested in Settings tab)
 */
export type SettingsStackParamList = {
  SettingsHome: undefined;
  Profile: undefined;
  Language: undefined;
  AdminSettings: { userId?: string };
  Users: undefined;
  Incidents: undefined;
  StreamQuality: undefined;
};

/**
 * Navigation type utilities
 */
export type NavigationProp<T extends keyof RootStackParamList> = import('@react-navigation/native').NavigationProp<
  RootStackParamList,
  T
>;

export type RouteProp<T extends keyof RootStackParamList> = import('@react-navigation/native').RouteProp<
  RootStackParamList,
  T
>;
