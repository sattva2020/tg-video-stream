/**
 * useMonitoringWebSocket Hook
 * 
 * React hook для real-time мониторинга через WebSocket.
 * Подключается к бэкенду и получает обновления метрик каждые 5 секунд.
 * 
 * @example
 * ```tsx
 * const { metrics, isConnected, error } = useMonitoringWebSocket();
 * 
 * if (!isConnected) return <div>Connecting...</div>;
 * return <div>Active streams: {metrics?.streams?.active ?? 0}</div>;
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// === Типы ===

export interface StreamMetrics {
  active: number;
  total_listeners: number;
}

export interface QueueMetrics {
  total_items: number;
}

export interface HttpMetrics {
  requests_in_progress: number;
}

export interface WebSocketMetrics {
  connections: number;
}

export interface MonitoringMetrics {
  streams: StreamMetrics;
  queue: QueueMetrics;
  http: HttpMetrics;
  websocket: WebSocketMetrics;
  timestamp?: string;
}

export interface StreamState {
  channel_id: number;
  status: 'playing' | 'paused' | 'stopped' | 'placeholder';
  current_item_id: string | null;
  listeners_count: number;
  is_placeholder: boolean;
  current_position: number;
  timestamp: string;
}

export interface QueueUpdate {
  channel_id: number;
  operation: 'add' | 'remove' | 'move' | 'clear' | 'skip' | 'priority_add';
  item_id?: string;
  position?: number;
  item?: Record<string, unknown>;
  timestamp: string;
}

export interface AutoEndWarning {
  channel_id: number;
  remaining_seconds: number;
  timeout_at: string;
  timestamp: string;
}

export interface ListenersUpdate {
  channel_id: number;
  listeners_count: number;
  timestamp: string;
}

export type WebSocketMessage = 
  | { type: 'metrics_update'; data: MonitoringMetrics; timestamp: string }
  | { type: 'stream_state'; } & StreamState
  | { type: 'queue_update' } & QueueUpdate
  | { type: 'auto_end_warning' } & AutoEndWarning
  | { type: 'auto_end_cancelled'; channel_id: number; timestamp: string }
  | { type: 'auto_end_triggered'; channel_id: number; reason: string; timestamp: string }
  | { type: 'listeners_update' } & ListenersUpdate
  | { type: 'pong' }
  | { type: 'ping' };

export interface UseMonitoringWebSocketOptions {
  /** Channel ID to filter events (optional) */
  channelId?: string;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** WebSocket URL (default: auto-detected) */
  url?: string;
}

export interface UseMonitoringWebSocketResult {
  /** Current metrics data */
  metrics: MonitoringMetrics | null;
  /** Active streams by channel_id */
  streams: Map<number, StreamState>;
  /** WebSocket connection status */
  isConnected: boolean;
  /** Connection error (if any) */
  error: string | null;
  /** Last update timestamp */
  lastUpdate: Date | null;
  /** Active auto-end warnings */
  autoEndWarnings: Map<number, AutoEndWarning>;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect */
  disconnect: () => void;
  /** Send message to server */
  send: (message: object) => void;
}

// === Default WebSocket URL ===

function getDefaultWebSocketUrl(channelId?: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const base = `${protocol}//${host}/api/ws/playlist`;
  return channelId ? `${base}?channel_id=${channelId}` : base;
}

// === Hook Implementation ===

export function useMonitoringWebSocket(
  options: UseMonitoringWebSocketOptions = {}
): UseMonitoringWebSocketResult {
  const {
    channelId,
    autoReconnect = true,
    reconnectDelay = 3000,
    url = getDefaultWebSocketUrl(channelId),
  } = options;

  // State
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null);
  const [streams, setStreams] = useState<Map<number, StreamState>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [autoEndWarnings, setAutoEndWarnings] = useState<Map<number, AutoEndWarning>>(new Map());

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  // === Message Handler ===
  
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as WebSocketMessage;
      setLastUpdate(new Date());

      switch (message.type) {
        case 'metrics_update':
          setMetrics(message.data);
          break;

        case 'stream_state':
          setStreams(prev => {
            const newMap = new Map(prev);
            newMap.set(message.channel_id, message as StreamState);
            return newMap;
          });
          break;

        case 'queue_update':
          // Можно добавить обработку очереди если нужно
          break;

        case 'auto_end_warning':
          setAutoEndWarnings(prev => {
            const newMap = new Map(prev);
            newMap.set(message.channel_id, message as AutoEndWarning);
            return newMap;
          });
          break;

        case 'auto_end_cancelled':
          setAutoEndWarnings(prev => {
            const newMap = new Map(prev);
            newMap.delete(message.channel_id);
            return newMap;
          });
          break;

        case 'auto_end_triggered':
          setAutoEndWarnings(prev => {
            const newMap = new Map(prev);
            newMap.delete(message.channel_id);
            return newMap;
          });
          // Также обновляем состояние стрима
          setStreams(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(message.channel_id);
            if (existing) {
              newMap.set(message.channel_id, {
                ...existing,
                status: 'stopped',
                timestamp: message.timestamp,
              });
            }
            return newMap;
          });
          break;

        case 'listeners_update':
          setStreams(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(message.channel_id);
            if (existing) {
              newMap.set(message.channel_id, {
                ...existing,
                listeners_count: message.listeners_count,
                timestamp: message.timestamp,
              });
            }
            return newMap;
          });
          break;

        case 'pong':
          // Server responded to ping
          break;

        default:
          // Unknown message type
          break;
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  }, []);

  // === Connection Management ===

  const connect = useCallback(() => {
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
        console.log('WebSocket connected');

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        console.log('WebSocket closed:', event.code, event.reason);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect
        if (autoReconnect && event.code !== 1000) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('Reconnecting WebSocket...');
            connect();
          }, reconnectDelay);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setError('Failed to connect');
    }
  }, [url, autoReconnect, reconnectDelay, handleMessage]);

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
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    metrics,
    streams,
    isConnected,
    error,
    lastUpdate,
    autoEndWarnings,
    reconnect: connect,
    disconnect,
    send,
  };
}

export default useMonitoringWebSocket;
