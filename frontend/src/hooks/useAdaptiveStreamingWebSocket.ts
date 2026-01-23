/**
 * useAdaptiveStreamingWebSocket Hook
 *
 * React hook for real-time adaptive streaming quality updates via WebSocket.
 * Listens for quality change events from the backend and updates component state.
 *
 * @example
 * ```tsx
 * const { qualityChange, isConnected, error } = useAdaptiveStreamingWebSocket({
 *   streamId: 'stream-url',
 *   onQualityChange: (event) => console.log('Quality changed:', event)
 * });
 *
 * if (qualityChange) {
 *   return <div>Quality: {qualityChange.new_quality}</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { QualityChangeEvent } from '../types/adaptive-streaming';

// === Types ===

export interface AdaptiveStreamingWebSocketMessage {
  type: 'quality_change' | 'adaptive_status' | 'bandwidth_update' | 'ping' | 'pong';
  data?: QualityChangeEvent | AdaptiveStreamingStatusData | BandwidthUpdateData;
  timestamp?: string;
}

export interface AdaptiveStreamingStatusData {
  stream_id: string;
  current_quality: string;
  current_bandwidth_kbps?: number;
  smoothed_bandwidth_kbps?: number;
  is_adapting: boolean;
  timestamp: string;
}

export interface BandwidthUpdateData {
  stream_id: string;
  bandwidth_kbps: number;
  device_type: string;
  timestamp: string;
}

export interface UseAdaptiveStreamingWebSocketOptions {
  /** Stream ID to filter events (encoded stream URL) */
  streamId?: string;
  /** Callback when quality changes */
  onQualityChange?: (event: QualityChangeEvent) => void;
  /** Callback when adaptive status updates */
  onStatusUpdate?: (status: AdaptiveStreamingStatusData) => void;
  /** Callback when bandwidth updates */
  onBandwidthUpdate?: (update: BandwidthUpdateData) => void;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** WebSocket URL (default: auto-detected) */
  url?: string;
  /** Enable WebSocket connection (default: true) */
  enabled?: boolean;
}

export interface UseAdaptiveStreamingWebSocketResult {
  /** Last quality change event */
  qualityChange: QualityChangeEvent | null;
  /** Current adaptive streaming status */
  status: AdaptiveStreamingStatusData | null;
  /** Last bandwidth update */
  bandwidthUpdate: BandwidthUpdateData | null;
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
}

// === Default WebSocket URL ===

function getDefaultWebSocketUrl(streamId?: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const base = `${protocol}//${host}/api/ws/adaptive-streaming`;
  return streamId ? `${base}?stream_id=${encodeURIComponent(streamId)}` : base;
}

// === Hook Implementation ===

export function useAdaptiveStreamingWebSocket(
  options: UseAdaptiveStreamingWebSocketOptions = {}
): UseAdaptiveStreamingWebSocketResult {
  const {
    streamId,
    onQualityChange,
    onStatusUpdate,
    onBandwidthUpdate,
    autoReconnect = true,
    reconnectDelay = 3000,
    url = getDefaultWebSocketUrl(streamId),
    enabled = true,
  } = options;

  // State
  const [qualityChange, setQualityChange] = useState<QualityChangeEvent | null>(null);
  const [status, setStatus] = useState<AdaptiveStreamingStatusData | null>(null);
  const [bandwidthUpdate, setBandwidthUpdate] = useState<BandwidthUpdateData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  // === Message Handler ===

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as AdaptiveStreamingWebSocketMessage;
      setLastUpdate(new Date());

      switch (message.type) {
        case 'quality_change':
          if (message.data) {
            const qcEvent = message.data as QualityChangeEvent;
            setQualityChange(qcEvent);
            onQualityChange?.(qcEvent);
          }
          break;

        case 'adaptive_status':
          if (message.data) {
            const statusData = message.data as AdaptiveStreamingStatusData;
            setStatus(statusData);
            onStatusUpdate?.(statusData);
          }
          break;

        case 'bandwidth_update':
          if (message.data) {
            const bwData = message.data as BandwidthUpdateData;
            setBandwidthUpdate(bwData);
            onBandwidthUpdate?.(bwData);
          }
          break;

        case 'pong':
          // Server responded to ping
          break;

        default:
          // Unknown message type - log for debugging
          break;
      }
    } catch (e) {
      // Silently handle parse errors
    }
  }, [onQualityChange, onStatusUpdate, onBandwidthUpdate]);

  // === Connection Management ===

  const connect = useCallback(() => {
    if (!enabled) return;

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

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect
        if (autoReconnect && enabled && event.code !== 1000) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, reconnectDelay);
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
  }, [url, autoReconnect, reconnectDelay, handleMessage, enabled]);

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

  // === Effects ===

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => disconnect();
  }, [enabled, connect, disconnect]);

  return {
    qualityChange,
    status,
    bandwidthUpdate,
    isConnected,
    error,
    lastUpdate,
    reconnect: connect,
    disconnect,
  };
}

export default useAdaptiveStreamingWebSocket;
