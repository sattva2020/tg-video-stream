/**
 * Hooks Index
 *
 * Centralized exports for all custom React hooks.
 */

export { useMonitoringWebSocket } from './useMonitoringWebSocket';
export { useInteractionWebSocket } from './useInteractionWebSocket';
export { default as useMonitoringWebSocket } from './useMonitoringWebSocket';
export { default as useInteractionWebSocket } from './useInteractionWebSocket';

// Re-export other hooks
export { useActivityEvents } from './useActivityEvents';
export { useChannelsQuery } from './useChannelsQuery';
export { useLogCollector } from './useLogCollector';
export { useMediaQuery } from './useMediaQuery';
export { useNotifications } from './useNotifications';
export { usePlaylistQuery } from './usePlaylistQuery';
export { usePlaylistWebSocket } from './usePlaylistWebSocket';
export { useScheduleQuery } from './useScheduleQuery';
export { useSystemMetrics } from './useSystemMetrics';
export { useTelegramAuth } from './useTelegramAuth';
export { useThemePreference } from './useThemePreference';
export { useToast } from './useToast';
export { useUsersQuery } from './useUsersQuery';
