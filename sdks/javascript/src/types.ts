/**
 * TypeScript types and interfaces for the Sattva API
 */

export interface SattvaClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

export interface Stream {
  id: string;
  channel_id: string;
  status: 'starting' | 'live' | 'stopping' | 'stopped' | 'error';
  started_at?: string;
  stopped_at?: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

export interface Channel {
  id: string;
  name: string;
  description?: string;
  thumbnail_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Playlist {
  id: string;
  name: string;
  description?: string;
  track_ids: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Webhook {
  id: string;
  url: string;
  event_types: string[];
  secret?: string;
  is_active: boolean;
  last_success_at?: string;
  last_failure_at?: string;
  failure_count: number;
  created_at: string;
  updated_at: string;
}

export interface WebhookEvent {
  id: string;
  webhook_id: string;
  event_type: string;
  event_id: string;
  status: 'pending' | 'success' | 'failed' | 'retrying';
  attempt_number: number;
  attempted_at: string;
  response_status_code?: number;
  response_body?: string;
  should_retry: boolean;
  next_retry_at?: string;
  duration_ms?: number;
}

export interface APIKey {
  id: string;
  name: string;
  scopes: string[];
  rate_limit?: number;
  is_active: boolean;
  expires_at?: string;
  last_used?: string;
  created_at: string;
}

export type WebhookEventType =
  | 'stream.started'
  | 'stream.stopped'
  | 'stream.paused'
  | 'stream.resumed'
  | 'stream.error'
  | 'viewer.milestone'
  | 'track.started'
  | 'track.completed'
  | 'track.failed';

export interface WebhookPayload {
  event_type: WebhookEventType;
  event_id: string;
  timestamp: string;
  data: Record<string, any>;
}
