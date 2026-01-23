import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebRTCConnectionQuality {
  bitrate?: number;
  packet_loss?: number;
  rtt?: number;
}

export interface WebRTCMessage {
  type: 'offer' | 'answer' | 'ice_candidate' | 'user_joined' | 'user_left' | 'active_connections' | 'error' | 'ping' | 'pong';
  from_user_id?: number;
  to_user_id?: number;
  sdp?: RTCSessionDescriptionInit;
  candidate?: RTCIceCandidateInit;
  user_id?: number;
  role?: string;
  connection_id?: string;
  connections?: Array<{ user_id: number; connection_id: string }>;
  message?: string;
  bitrate?: number;
  packet_loss?: number;
  rtt?: number;
  timestamp?: number;
}

export interface WebRTCConnection {
  userId: number;
  connectionId: string;
  role: 'host' | 'guest';
  peerConnection: RTCPeerConnection;
  remoteStream?: MediaStream;
  quality: WebRTCConnectionQuality;
  createdAt: number;
}

interface UseWebRTCOptions {
  liveStreamId: string;
  userId: number;
  role?: 'host' | 'guest';
  localStream?: MediaStream;
  onRemoteStream?: (userId: number, stream: MediaStream) => void;
  onUserJoined?: (userId: number, role: 'host' | 'guest') => void;
  onUserLeft?: (userId: number) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

const WS_RECONNECT_DELAY = 3000;
const WS_MAX_RECONNECT_DELAY = 30000;
const WS_PING_INTERVAL = 25000;
const WS_MAX_RECONNECT_ATTEMPTS = 10;

const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ],
};

export function useWebRTC({
  liveStreamId,
  userId,
  role = 'guest',
  localStream,
  onRemoteStream,
  onUserJoined,
  onUserLeft,
  onError,
  enabled = true,
}: UseWebRTCOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connections, setConnections] = useState<Map<number, WebRTCConnection>>(new Map());
  const [connectionQuality, setConnectionQuality] = useState<WebRTCConnectionQuality>({});

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const pingIntervalRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptRef = useRef(0);
  const reconnectDelayRef = useRef(WS_RECONNECT_DELAY);
  const peerConnectionsRef = useRef<Map<number, RTCPeerConnection>>(new Map());

  const getWebSocketUrl = useCallback(() => {
    const envBaseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;

    let wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let wsHost = window.location.host;

    if (envBaseUrl && envBaseUrl.startsWith('http')) {
      wsProtocol = envBaseUrl.startsWith('https') ? 'wss' : 'ws';
      wsHost = envBaseUrl.replace(/^https?:\/\//, '').split('/')[0];
    }

    const params = new URLSearchParams({
      live_stream_id: liveStreamId,
      user_id: userId.toString(),
      role,
    });

    return `${wsProtocol}://${wsHost}/api/ws/webrtc?${params.toString()}`;
  }, [liveStreamId, userId, role]);

  const createPeerConnection = useCallback((targetUserId: number): RTCPeerConnection => {
    const pc = new RTCPeerConnection(ICE_SERVERS);

    // Add local stream tracks to the peer connection
    if (localStream) {
      localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
      });
    }

    // Handle incoming remote stream
    pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        const remoteStream = event.streams[0];
        onRemoteStream?.(targetUserId, remoteStream);
      }
    };

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ice_candidate',
          to_user_id: targetUserId,
          candidate: event.candidate,
        }));
      }
    };

    // Handle connection state changes
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
        // Cleanup failed connection
        peerConnectionsRef.current.delete(targetUserId);
        setConnections(prev => {
          const next = new Map(prev);
          next.delete(targetUserId);
          return next;
        });
      }
    };

    // Monitor connection quality
    pc.onstats = (event) => {
      if (pc.connectionState === 'connected') {
        // Calculate quality metrics from stats
        // This is a simplified version - real implementation would use getStats()
        setConnectionQuality(prev => ({
          ...prev,
          [targetUserId]: {
            bitrate: 0,
            packet_loss: 0,
            rtt: 0,
          },
        }));
      }
    };

    peerConnectionsRef.current.set(targetUserId, pc);
    return pc;
  }, [localStream, onRemoteStream]);

  const handleOffer = useCallback(async (message: WebRTCMessage) => {
    const { from_user_id: fromUserId, sdp } = message;
    if (!fromUserId || !sdp) return;

    let pc = peerConnectionsRef.current.get(fromUserId);
    if (!pc) {
      pc = createPeerConnection(fromUserId);
    }

    try {
      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'answer',
          to_user_id: fromUserId,
          sdp: answer,
        }));
      }
    } catch (error) {
      onError?.(`Failed to handle offer: ${error}`);
    }
  }, [createPeerConnection, onError]);

  const handleAnswer = useCallback(async (message: WebRTCMessage) => {
    const { from_user_id: fromUserId, sdp } = message;
    if (!fromUserId || !sdp) return;

    const pc = peerConnectionsRef.current.get(fromUserId);
    if (!pc) return;

    try {
      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    } catch (error) {
      onError?.(`Failed to handle answer: ${error}`);
    }
  }, [onError]);

  const handleIceCandidate = useCallback(async (message: WebRTCMessage) => {
    const { from_user_id: fromUserId, candidate } = message;
    if (!fromUserId || !candidate) return;

    const pc = peerConnectionsRef.current.get(fromUserId);
    if (!pc) return;

    try {
      await pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (error) {
      onError?.(`Failed to add ICE candidate: ${error}`);
    }
  }, [onError]);

  const handleUserJoined = useCallback((message: WebRTCMessage) => {
    const { user_id, role: userRole, connection_id } = message;
    if (!user_id) return;

    onUserJoined?.(user_id, (userRole as 'host' | 'guest') || 'guest');

    setConnections(prev => {
      const pc = peerConnectionsRef.current.get(user_id);
      if (!pc || !connection_id) return prev;

      const next = new Map(prev);
      next.set(user_id, {
        userId: user_id,
        connectionId: connection_id,
        role: (userRole as 'host' | 'guest') || 'guest',
        peerConnection: pc,
        quality: {},
        createdAt: Date.now(),
      });
      return next;
    });
  }, [onUserJoined]);

  const handleUserLeft = useCallback((message: WebRTCMessage) => {
    const { user_id } = message;
    if (!user_id) return;

    // Cleanup peer connection
    const pc = peerConnectionsRef.current.get(user_id);
    if (pc) {
      pc.close();
      peerConnectionsRef.current.delete(user_id);
    }

    setConnections(prev => {
      const next = new Map(prev);
      next.delete(user_id);
      return next;
    });

    onUserLeft?.(user_id);
  }, [onUserLeft]);

  const handleActiveConnections = useCallback((message: WebRTCMessage) => {
    const { connections: activeConnections } = message;
    if (!activeConnections) return;

    // Initialize connections for active users
    activeConnections.forEach(({ user_id, connection_id }) => {
      if (user_id && user_id !== userId && !peerConnectionsRef.current.has(user_id)) {
        const pc = createPeerConnection(user_id);
        setConnections(prev => {
          const next = new Map(prev);
          next.set(user_id, {
            userId: user_id,
            connectionId: connection_id,
            role: 'guest',
            peerConnection: pc,
            quality: {},
            createdAt: Date.now(),
          });
          return next;
        });
      }
    });
  }, [userId, createPeerConnection]);

  const connect = useCallback(() => {
    if (!enabled || isConnecting) return;

    // Stop reconnecting after too many attempts
    if (reconnectAttemptRef.current >= WS_MAX_RECONNECT_ATTEMPTS) {
      return;
    }

    setIsConnecting(true);

    // Cleanup existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(getWebSocketUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      reconnectAttemptRef.current = 0;
      reconnectDelayRef.current = WS_RECONNECT_DELAY;

      // Setup ping interval
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, WS_PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebRTCMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'offer':
            handleOffer(message);
            break;

          case 'answer':
            handleAnswer(message);
            break;

          case 'ice_candidate':
            handleIceCandidate(message);
            break;

          case 'user_joined':
            handleUserJoined(message);
            break;

          case 'user_left':
            handleUserLeft(message);
            break;

          case 'active_connections':
            handleActiveConnections(message);
            break;

          case 'error':
            onError?.(message.message || 'Unknown WebRTC error');
            break;

          case 'ping':
          case 'pong':
            // Keepalive, ignore
            break;

          default:
            break;
        }
      } catch (e) {
        onError?.(`Failed to parse WebRTC message: ${e}`);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsConnecting(false);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }

      // Reconnect with exponential backoff
      if (enabled && reconnectAttemptRef.current < WS_MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptRef.current++;

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelayRef.current);

        reconnectDelayRef.current = Math.min(
          reconnectDelayRef.current * 2,
          WS_MAX_RECONNECT_DELAY
        );
      }
    };

    ws.onerror = () => {
      onError?.('WebSocket connection error');
    };
  }, [
    enabled,
    isConnecting,
    getWebSocketUrl,
    handleOffer,
    handleAnswer,
    handleIceCandidate,
    handleUserJoined,
    handleUserLeft,
    handleActiveConnections,
    onError,
  ]);

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

    // Close all peer connections
    peerConnectionsRef.current.forEach(pc => pc.close());
    peerConnectionsRef.current.clear();

    setConnections(new Map());
    setIsConnected(false);
  }, []);

  const createOffer = useCallback(async (targetUserId: number) => {
    let pc = peerConnectionsRef.current.get(targetUserId);
    if (!pc) {
      pc = createPeerConnection(targetUserId);
    }

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'offer',
          to_user_id: targetUserId,
          sdp: offer,
        }));
      }
    } catch (error) {
      onError?.(`Failed to create offer: ${error}`);
    }
  }, [createPeerConnection, onError]);

  const updateQuality = useCallback((quality: WebRTCConnectionQuality) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'quality_update',
        ...quality,
      }));
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
    isConnected,
    isConnecting,
    connections: Array.from(connections.values()),
    connectionQuality,
    createOffer,
    disconnect,
    updateQuality,
  };
}

export default useWebRTC;
