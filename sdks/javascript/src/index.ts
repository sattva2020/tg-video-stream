/**
 * @sattva/api-client
 * Official JavaScript/TypeScript SDK for Sattva Streaming Platform API
 */

// Export main client
export { SattvaClient } from './client';

// Export resources
export {
  StreamsResource,
  ChannelsResource,
  PlaylistsResource,
  WebhooksResource,
  APIKeysResource,
} from './resources';

// Export types
export type {
  SattvaClientConfig,
  Stream,
  Channel,
  Playlist,
  Webhook,
  WebhookEvent,
  APIKey,
  WebhookEventType,
  WebhookPayload,
} from './types';

// Export exceptions
export {
  SattvaAPIError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ValidationError,
} from './exceptions';
