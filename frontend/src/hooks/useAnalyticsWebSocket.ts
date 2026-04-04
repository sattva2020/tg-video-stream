/**
 * useAnalyticsWebSocket Hook
 *
 * React hook для real-time аналитики через WebSocket.
 * Подключается к бэкенду и получает обновления метрик в реальном времени.
 *
 * @example
 * ```tsx
 * const { listenerStats, streamPerformance, isConnected } = useAnalyticsWebSocket();
 *
 * if (!isConnected) return <div>Connecting...</div>;
 * return <div>Current listeners: {listenerStats?.current ?? 0}</div>;
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { queryClient } from '../lib/queryClient';
import type {
  ListenerStats,
  EngagementMetricsResponse,
  StreamPerformanceResponse,
  ContentInsightsResponse,
} from '../types/analytics';

// === Types ===

export interface RealtimeListenerUpdate {
  channel_id?: string;
  current: number;
  peak_today: number;
  timestamp: string;
}

export interface RealtimeEngagementUpdate {
  channel_id?: string;
  message_count: number;
  reaction_count: number;
  unique_users: number;
  timestamp: string;
}

export interface RealtimeStreamUpdate {
  channel_id?: string;
  uptime_percentage: number;
  current_quality: string;
  buffering_percentage: number;
  bandwidth_usage_mbps: number | null;
  timestamp: string;
}

export interface RealtimeContentViewUpdate {
  content_id: string;
  total_views: number;
  completion_percentage: number;
  timestamp: string;
}

export type AnalyticsWebSocketMessage =
  | { type: 'listener_update'; data: RealtimeListenerUpdate; timestamp: string }
  | { type: 'engagement_update'; data: RealtimeEngagementUpdate; timestamp: string }
  | { type: 'stream_update'; data: RealtimeStreamUpdate; timestamp: string }
  | { type: 'content_view_update'; data: RealtimeContentViewUpdate; timestamp: string }
  | { type: 'summary_update'; data: Partial<ListenerStats>; timestamp: string }
  | { type: 'ping' }
  | { type: 'pong' };

export interface UseAnalyticsWebSocketOptions {
  /** Channel ID to filter events (optional) */
  channelId?: string;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** WebSocket URL (default: auto-detected) */
  url?: string;
  /** Enable real-time updates (default: true) */
  enabled?: boolean;
}

export interface UseAnalyticsWebSocketResult {
  /** Current listener statistics */
  listenerStats: ListenerStats | null;
  /** Stream performance metrics */
  streamPerformance: Partial<StreamPerformanceResponse> | null;
  /** Engagement metrics */
  engagementMetrics: Partial<EngagementMetricsResponse> | null;
  /** Content insights */
  contentInsights: Partial<ContentInsightsResponse> | null;
  /** WebSocket connection status */
  isConnected: boolean;
  /** Connection error (if any) */
  error: string | null;
  /** Last update timestamp */
  lastUpdate: Date | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect */
  disconnect: () => void;
  /** Send message to server */
  send: (message: object) => void;
}

// === Constants ===

const WS_RECONNECT_DELAY = 3000;
const WS_MAX_RECONNECT_DELAY = 60000;
const WS_PING_INTERVAL = 25000;
const WS_MAX_RECONNECT_ATTEMPTS = 10;

// === Default WebSocket URL ===

function getDefaultWebSocketUrl(channelId?: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const base = `${protocol}//${host}/api/ws/analytics`;
  return channelId ? `${base}?channel_id=${channelId}` : base;
}

// === Hook Implementation ===

export function useAnalyticsWebSocket(
  options: UseAnalyticsWebSocketOptions = {}
): UseAnalyticsWebSocketResult {
  const {
    channelId,
    autoReconnect = true,
    reconnectDelay = WS_RECONNECT_DELAY,
    url = getDefaultWebSocketUrl(channelId),
    enabled = true,
  } = options;

  // State
  const [listenerStats, setListenerStats] = useState<ListenerStats | null>(null);
  const [streamPerformance, setStreamPerformance] = useState<Partial<StreamPerformanceResponse> | null>(null);
  const [engagementMetrics, setEngagementMetrics] = useState<Partial<EngagementMetricsResponse> | null>(null);
  const [contentInsights, setContentInsights] = useState<Partial<ContentInsightsResponse> | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectDelayRef = useRef(reconnectDelay);

  // === Message Handler ===

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as AnalyticsWebSocketMessage;
      setLastUpdate(new Date());

      switch (message.type) {
        case 'listener_update':
          setListenerStats(prev => ({
            current: message.data.current,
            peak_today: message.data.peak_today,
            peak_week: prev?.peak_week ?? message.data.peak_today,
            average_week: prev?.average_week ?? 0,
          }));

          // Invalidate related queries
          queryClient.invalidateQueries({ queryKey: ['analytics', 'listeners'] });
          break;

        case 'engagement_update':
          setEngagementMetrics(prev => ({
            ...prev,
            total_messages: message.data.message_count,
            total_reactions: message.data.reaction_count,
            unique_users: message.data.unique_users,
          }));

          // Invalidate related queries
          queryClient.invalidateQueries({ queryKey: ['analytics', 'engagement'] });
          break;

        case 'stream_update':
          setStreamPerformance(prev => ({
            ...prev,
            uptime_percentage: message.data.uptime_percentage,
            current_quality: message.data.current_quality,
            average_buffering_percentage: message.data.buffering_percentage,
            bandwidth_usage_mbps: message.data.bandwidth_usage_mbps,
          }));

          // Invalidate related queries
          queryClient.invalidateQueries({ queryKey: ['analytics', 'stream-performance'] });
          break;

        case 'content_view_update':
          setContentInsights(prev => {
            const updatedMostWatched = prev?.most_watched
              ? prev.most_watched.map(item =>
                  item.content_id === message.data.content_id
                    ? {
                        ...item,
                        total_views: message.data.total_views,
                        average_completion_percentage: message.data.completion_percentage,
                      }
                    : item
                )
              : [];

            return {
              ...prev,
              most_watched: updatedMostWatched,
            };
          });

          // Invalidate related queries
          queryClient.invalidateQueries({ queryKey: ['analytics', 'content-insights'] });
          break;

        case 'summary_update':
          setListenerStats(prev => ({
            current: message.data.current ?? prev?.current ?? 0,
            peak_today: message.data.peak_today ?? prev?.peak_today ?? 0,
            peak_week: message.data.peak_week ?? prev?.peak_week ?? 0,
            average_week: message.data.average_week ?? prev?.average_week ?? 0,
          }));

          // Invalidate related queries
          queryClient.invalidateQueries({ queryKey: ['analytics', 'summary'] });
          break;

        case 'pong':
          // Server responded to ping
          break;

        default:
          // Unknown message type - silently ignore
          break;
      }
    } catch (e) {
      // Failed to parse message - silently ignore
    }
  }, []);

  // === Connection Management ===

  const connect = useCallback(() => {
    if (!enabled) return;

    // Check max reconnect attempts
    if (reconnectAttemptRef.current >= WS_MAX_RECONNECT_ATTEMPTS) {
      setError('Maximum reconnection attempts reached');
      return;
    }

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptRef.current = 0;
        reconnectDelayRef.current = reconnectDelay;

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, WS_PING_INTERVAL);
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect
        if (autoReconnect && event.code !== 1000 && reconnectAttemptRef.current < WS_MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptRef.current++;
          const currentDelay = reconnectDelayRef.current;

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, currentDelay);

          // Exponential backoff
          reconnectDelayRef.current = Math.min(currentDelay * 2, WS_MAX_RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (e) {
      setError('Failed to connect');
    }
  }, [url, enabled, autoReconnect, reconnectDelay, handleMessage]);

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    // Close connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const send = useCallback((message: object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // === Effects ===

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => disconnect();
  }, [enabled, connect, disconnect]);

  return {
    listenerStats,
    streamPerformance,
    engagementMetrics,
    contentInsights,
    isConnected,
    error,
    lastUpdate,
    reconnect: connect,
    disconnect,
    send,
  };
}

export default useAnalyticsWebSocket;
