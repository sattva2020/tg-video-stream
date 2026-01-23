/**
 * useInteractionWebSocket Hook
 *
 * React hook для real-time обновлений интерактивных функций через WebSocket.
 * Подключается к бэкенду и получает обновления для polls, Q&A, reactions, shoutouts, и CTAs.
 *
 * @example
 * ```tsx
 * const { polls, questions, reactions, shoutouts, ctas, isConnected, error } = useInteractionWebSocket({ channelId: '1' });
 *
 * if (!isConnected) return <div>Connecting...</div>;
 * return <div>Active polls: {polls.size}</div>;
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  Poll,
  PollVote,
  Question,
  Reaction,
  ReactionBatch,
  Shoutout,
  CTA,
  CTAClick,
  ModeratedItem,
  EngagementMetrics,
  InteractionWebSocketEvent,
} from '@/types/interactions';

// === Default WebSocket URL ===

function getDefaultWebSocketUrl(channelId?: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const base = `${protocol}//${host}/api/ws/interactions`;
  return channelId ? `${base}?channel_id=${channelId}` : base;
}

// === Hook Options ===

export interface UseInteractionWebSocketOptions {
  /** Channel ID to filter events (optional) */
  channelId?: string;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** WebSocket URL (default: auto-detected) */
  url?: string;
  /** Enable polls updates (default: true) */
  enablePolls?: boolean;
  /** Enable Q&A updates (default: true) */
  enableQuestions?: boolean;
  /** Enable reaction updates (default: true) */
  enableReactions?: boolean;
  /** Enable shoutout updates (default: true) */
  enableShoutouts?: boolean;
  /** Enable CTA updates (default: true) */
  enableCTAs?: boolean;
}

// === Hook Result ===

export interface UseInteractionWebSocketResult {
  /** Active polls by poll_id */
  polls: Map<string, Poll>;
  /** Active questions by question_id */
  questions: Map<string, Question>;
  /** Recent reactions by reaction_id */
  reactions: Map<string, Reaction>;
  /** Active shoutouts by shoutout_id */
  shoutouts: Map<string, Shoutout>;
  /** Active CTAs by cta_id */
  ctas: Map<string, CTA>;
  /** WebSocket connection status */
  isConnected: boolean;
  /** Connection error (if any) */
  error: string | null;
  /** Last update timestamp */
  lastUpdate: Date | null;
  /** Current engagement metrics */
  engagementMetrics: EngagementMetrics | null;
  /** Moderation flags */
  moderatedItems: ModeratedItem[];
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect */
  disconnect: () => void;
  /** Send message to server */
  send: (message: object) => void;
}

// === Hook Implementation ===

export function useInteractionWebSocket(
  options: UseInteractionWebSocketOptions = {}
): UseInteractionWebSocketResult {
  const {
    channelId,
    autoReconnect = true,
    reconnectDelay = 3000,
    url = getDefaultWebSocketUrl(channelId),
    enablePolls = true,
    enableQuestions = true,
    enableReactions = true,
    enableShoutouts = true,
    enableCTAs = true,
  } = options;

  // State
  const [polls, setPolls] = useState<Map<string, Poll>>(new Map());
  const [questions, setQuestions] = useState<Map<string, Question>>(new Map());
  const [reactions, setReactions] = useState<Map<string, Reaction>>(new Map());
  const [shoutouts, setShoutouts] = useState<Map<string, Shoutout>>(new Map());
  const [ctas, setCTAs] = useState<Map<string, CTA>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [engagementMetrics, setEngagementMetrics] = useState<EngagementMetrics | null>(null);
  const [moderatedItems, setModeratedItems] = useState<ModeratedItem[]>([]);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  // === Message Handler ===

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as InteractionWebSocketEvent;
      setLastUpdate(new Date());

      switch (message.type) {
        case 'poll_created':
          if (enablePolls) {
            setPolls(prev => {
              const newMap = new Map(prev);
              newMap.set(message.data.id, message.data);
              return newMap;
            });
          }
          break;

        case 'poll_updated':
          if (enablePolls) {
            setPolls(prev => {
              const newMap = new Map(prev);
              newMap.set(message.data.id, message.data);
              return newMap;
            });
          }
          break;

        case 'poll_ended':
          if (enablePolls) {
            setPolls(prev => {
              const newMap = new Map(prev);
              const poll = newMap.get(message.data.poll_id);
              if (poll) {
                newMap.set(message.data.poll_id, {
                  ...poll,
                  status: 'ended',
                  ended_at: new Date().toISOString(),
                });
              }
              return newMap;
            });
          }
          break;

        case 'vote_submitted':
          if (enablePolls) {
            setPolls(prev => {
              const newMap = new Map(prev);
              const poll = newMap.get(message.data.poll_id);
              if (poll) {
                // Update vote counts
                const updatedOptions = poll.options.map(opt => {
                  if (opt.id === message.data.option_id) {
                    return { ...opt, votes: opt.votes + 1 };
                  }
                  return opt;
                });
                newMap.set(message.data.poll_id, {
                  ...poll,
                  options: updatedOptions,
                  total_votes: poll.total_votes + 1,
                  updated_at: message.data.voted_at,
                });
              }
              return newMap;
            });
          }
          break;

        case 'question_submitted':
          if (enableQuestions) {
            setQuestions(prev => {
              const newMap = new Map(prev);
              newMap.set(message.data.id, message.data);
              return newMap;
            });
          }
          break;

        case 'question_upvoted':
          if (enableQuestions) {
            setQuestions(prev => {
              const newMap = new Map(prev);
              const question = newMap.get(message.data.question_id);
              if (question) {
                newMap.set(message.data.question_id, {
                  ...question,
                  upvotes: message.data.upvotes,
                  updated_at: new Date().toISOString(),
                });
              }
              return newMap;
            });
          }
          break;

        case 'question_answered':
          if (enableQuestions) {
            setQuestions(prev => {
              const newMap = new Map(prev);
              const question = newMap.get(message.data.question_id);
              if (question) {
                newMap.set(message.data.question_id, {
                  ...question,
                  is_answered: true,
                  answered_at: message.data.answered_at,
                  updated_at: message.data.answered_at,
                });
              }
              return newMap;
            });
          }
          break;

        case 'reaction_added':
          if (enableReactions) {
            setReactions(prev => {
              const newMap = new Map(prev);
              // Add or update reaction
              newMap.set(message.data.id, message.data);
              // Auto-remove reactions after duration
              setTimeout(() => {
                setReactions(current => {
                  const updated = new Map(current);
                  updated.delete(message.data.id);
                  return updated;
                });
              }, message.data.duration_seconds * 1000);
              return newMap;
            });
          }
          break;

        case 'reaction_batch':
          if (enableReactions) {
            const { reactions: batchReactions } = message.data;
            batchReactions.forEach(batchReaction => {
              setReactions(prev => {
                const newMap = new Map(prev);
                const reactionId = `batch_${Date.now()}_${Math.random()}`;
                newMap.set(reactionId, {
                  id: reactionId,
                  channel_id: message.data.channel_id,
                  type: 'reaction',
                  emoji: batchReaction.emoji,
                  count: batchReaction.count,
                  duration_seconds: 5,
                  status: 'active',
                  created_at: batchReaction.timestamp,
                });
                // Auto-remove after 5 seconds
                setTimeout(() => {
                  setReactions(current => {
                    const updated = new Map(current);
                    updated.delete(reactionId);
                    return updated;
                  });
                }, 5000);
                return newMap;
              });
            });
          }
          break;

        case 'shoutout_triggered':
          if (enableShoutouts) {
            setShoutouts(prev => {
              const newMap = new Map(prev);
              newMap.set(message.data.id, message.data);
              // Auto-remove shoutout after duration
              setTimeout(() => {
                setShoutouts(current => {
                  const updated = new Map(current);
                  updated.delete(message.data.id);
                  return updated;
                });
              }, message.data.duration_seconds * 1000);
              return newMap;
            });
          }
          break;

        case 'cta_displayed':
          if (enableCTAs) {
            setCTAs(prev => {
              const newMap = new Map(prev);
              newMap.set(message.data.id, message.data);
              // Auto-dismiss if duration is set
              if (message.data.display_duration_seconds) {
                setTimeout(() => {
                  setCTAs(current => {
                    const updated = new Map(current);
                    updated.delete(message.data.id);
                    return updated;
                  });
                }, message.data.display_duration_seconds * 1000);
              }
              return newMap;
            });
          }
          break;

        case 'cta_clicked':
          setCTAs(prev => {
            const newMap = new Map(prev);
            const cta = newMap.get(message.data.cta_id);
            if (cta) {
              newMap.set(message.data.cta_id, {
                ...cta,
                click_count: cta.click_count + 1,
                updated_at: message.data.clicked_at,
              });
            }
            return newMap;
          });
          break;

        case 'moderation_flagged':
          setModeratedItems(prev => [...prev, message.data]);
          break;

        case 'analytics_update':
          setEngagementMetrics(message.data);
          break;

        default:
          // Unknown message type - ignore
          break;
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  }, [enablePolls, enableQuestions, enableReactions, enableShoutouts, enableCTAs]);

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
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect
        if (autoReconnect && event.code !== 1000) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
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
    polls,
    questions,
    reactions,
    shoutouts,
    ctas,
    isConnected,
    error,
    lastUpdate,
    engagementMetrics,
    moderatedItems,
    reconnect: connect,
    disconnect,
    send,
  };
}

export default useInteractionWebSocket;
