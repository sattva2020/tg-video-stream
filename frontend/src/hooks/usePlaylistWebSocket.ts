import { useEffect, useRef, useState, useCallback } from 'react';
import type { PlaylistItem } from '../services/playlist';

export interface WebSocketMessage {
  type: 'playlist' | 'item_added' | 'item_removed' | 'item_updated' | 'stream_status' | 'stream_started' | 'stream_stopped' | 'track_playing' | 'ping' | 'pong';
  data?: PlaylistItem | PlaylistItem[];
  item?: PlaylistItem;
  item_id?: string;
  status?: string;
}

// Event type for toast notifications
export interface PlaylistEvent {
  type: WebSocketMessage['type'];
  item?: PlaylistItem;
  timestamp: number;
}

interface UsePlaylistWebSocketOptions {
  channelId?: string;
  onPlaylistUpdate?: (items: PlaylistItem[]) => void;
  onStreamStatus?: (status: string) => void;
  enabled?: boolean;
}

const WS_RECONNECT_DELAY = 3000;
const WS_PING_INTERVAL = 25000;

export function usePlaylistWebSocket({
  channelId,
  onPlaylistUpdate,
  onStreamStatus,
  enabled = true,
}: UsePlaylistWebSocketOptions) {
  const [items, setItems] = useState<PlaylistItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string>('unknown');
  const [lastEvent, setLastEvent] = useState<PlaylistEvent | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const pingIntervalRef = useRef<NodeJS.Timeout>();

  const getWebSocketUrl = useCallback(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = baseUrl.replace(/^https?:\/\//, '');
    const params = channelId ? `?channel_id=${channelId}` : '';
    return `${wsProtocol}://${wsHost}/api/ws/playlist${params}`;
  }, [channelId]);

  const emitEvent = useCallback((type: WebSocketMessage['type'], item?: PlaylistItem) => {
    setLastEvent({
      type,
      item,
      timestamp: Date.now(),
    });
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    
    // Cleanup existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(getWebSocketUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected to playlist WebSocket');
      setIsConnected(true);
      
      // Setup ping interval
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, WS_PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        switch (message.type) {
          case 'playlist':
            // Full playlist received
            if (Array.isArray(message.data)) {
              setItems(message.data);
              onPlaylistUpdate?.(message.data);
            }
            break;
            
          case 'item_added':
            // New item added
            if (message.data && !Array.isArray(message.data)) {
              const newItem = message.data as PlaylistItem;
              setItems(prev => [...prev, newItem]);
              emitEvent('item_added', newItem);
            }
            break;
            
          case 'item_removed':
            // Item removed
            if (message.item_id) {
              setItems(prev => prev.filter(item => item.id !== message.item_id));
              emitEvent('item_removed');
            }
            break;
            
          case 'item_updated':
            // Item status updated
            if (message.data && !Array.isArray(message.data)) {
              const updatedItem = message.data as PlaylistItem;
              setItems(prev => prev.map(item => 
                item.id === updatedItem.id ? updatedItem : item
              ));
            }
            break;
          
          case 'track_playing':
            // Currently playing track changed
            if (message.item) {
              emitEvent('track_playing', message.item);
            }
            break;
            
          case 'stream_status':
            if (message.status) {
              setStreamStatus(message.status);
              onStreamStatus?.(message.status);
            }
            break;
          
          case 'stream_started':
            emitEvent('stream_started');
            break;
            
          case 'stream_stopped':
            emitEvent('stream_stopped');
            break;
            
          case 'pong':
            // Keepalive response, ignore
            break;
            
          default:
            console.log('[WS] Unknown message type:', message.type);
        }
      } catch (e) {
        console.error('[WS] Failed to parse message:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('[WS] Connection closed:', event.code, event.reason);
      setIsConnected(false);
      
      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      
      // Reconnect after delay
      if (enabled) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WS] Attempting to reconnect...');
          connect();
        }, WS_RECONNECT_DELAY);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] WebSocket error:', error);
    };
  }, [enabled, getWebSocketUrl, onPlaylistUpdate, onStreamStatus, emitEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const refresh = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'refresh' }));
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    items,
    isConnected,
    streamStatus,
    lastEvent,
    refresh,
    disconnect,
  };
}

export default usePlaylistWebSocket;
