/**
 * API resource classes for interacting with different endpoints
 */

import { SattvaClient } from './client';
import type {
  Stream,
  Channel,
  Playlist,
  Webhook,
  WebhookEvent,
  APIKey,
} from './types';

/**
 * Streams resource
 */
export class StreamsResource extends SattvaClient {
  async list(params?: { limit?: number; offset?: number }): Promise<Stream[]> {
    return this.get<Stream[]>('/streams');
  }

  async get(streamId: string): Promise<Stream> {
    return this.get<Stream>(`/streams/${streamId}`);
  }

  async start(channelId: string): Promise<Stream> {
    return this.post<Stream>(`/streams/start`, { channel_id: channelId });
  }

  async stop(streamId: string): Promise<Stream> {
    return this.post<Stream>(`/streams/${streamId}/stop`);
  }

  async restart(streamId: string): Promise<Stream> {
    return this.post<Stream>(`/streams/${streamId}/restart`);
  }
}

/**
 * Channels resource
 */
export class ChannelsResource extends SattvaClient {
  async list(): Promise<Channel[]> {
    return this.get<Channel[]>('/channels');
  }

  async get(channelId: string): Promise<Channel> {
    return this.get<Channel>(`/channels/${channelId}`);
  }

  async create(data: {
    name: string;
    description?: string;
  }): Promise<Channel> {
    return this.post<Channel>('/channels', data);
  }

  async update(
    channelId: string,
    data: { name?: string; description?: string }
  ): Promise<Channel> {
    return this.patch<Channel>(`/channels/${channelId}`, data);
  }

  async delete(channelId: string): Promise<void> {
    return this.delete<void>(`/channels/${channelId}`);
  }
}

/**
 * Playlists resource
 */
export class PlaylistsResource extends SattvaClient {
  async list(): Promise<Playlist[]> {
    return this.get<Playlist[]>('/playlists');
  }

  async get(playlistId: string): Promise<Playlist> {
    return this.get<Playlist>(`/playlists/${playlistId}`);
  }

  async create(data: {
    name: string;
    description?: string;
    track_ids: string[];
  }): Promise<Playlist> {
    return this.post<Playlist>('/playlists', data);
  }

  async update(
    playlistId: string,
    data: { name?: string; description?: string }
  ): Promise<Playlist> {
    return this.patch<Playlist>(`/playlists/${playlistId}`, data);
  }

  async reorder(playlistId: string, data: { track_ids: string[] }): Promise<Playlist> {
    return this.patch<Playlist>(`/playlists/${playlistId}/reorder`, data);
  }

  async delete(playlistId: string): Promise<void> {
    return this.delete<void>(`/playlists/${playlistId}`);
  }
}

/**
 * Webhooks resource
 */
export class WebhooksResource extends SattvaClient {
  async list(): Promise<Webhook[]> {
    return this.get<Webhook[]>('/webhooks');
  }

  async get(webhookId: string): Promise<Webhook> {
    return this.get<Webhook>(`/webhooks/${webhookId}`);
  }

  async create(data: {
    url: string;
    event_types: string[];
  }): Promise<Webhook> {
    return this.post<Webhook>('/webhooks', data);
  }

  async update(
    webhookId: string,
    data: { url?: string; event_types?: string[]; is_active?: boolean }
  ): Promise<Webhook> {
    return this.patch<Webhook>(`/webhooks/${webhookId}`, data);
  }

  async delete(webhookId: string): Promise<void> {
    return this.delete<void>(`/webhooks/${webhookId}`);
  }

  async test(webhookId: string): Promise<{ success: boolean; message: string }> {
    return this.post<{ success: boolean; message: string }>(
      `/webhooks/${webhookId}/test`
    );
  }

  async rotateSecret(webhookId: string): Promise<{ secret: string }> {
    return this.post<{ secret: string }>(
      `/webhooks/${webhookId}/rotate-secret`
    );
  }

  async listEvents(webhookId: string): Promise<WebhookEvent[]> {
    return this.get<WebhookEvent[]>(`/webhooks/${webhookId}/events`);
  }
}

/**
 * API Keys resource
 */
export class APIKeysResource extends SattvaClient {
  async list(): Promise<APIKey[]> {
    return this.get<APIKey[]>('/keys');
  }

  async get(keyId: string): Promise<APIKey> {
    return this.get<APIKey>(`/keys/${keyId}`);
  }

  async create(data: {
    name: string;
    scopes: string[];
    rate_limit?: number;
    expires_at?: string;
  }): Promise<APIKey & { key: string }> {
    return this.post<APIKey & { key: string }>('/keys', data);
  }

  async update(
    keyId: string,
    data: { name?: string; is_active?: boolean }
  ): Promise<APIKey> {
    return this.patch<APIKey>(`/keys/${keyId}`, data);
  }

  async delete(keyId: string): Promise<void> {
    return this.delete<void>(`/keys/${keyId}`);
  }

  async revoke(keyId: string): Promise<void> {
    return this.post<void>(`/keys/${keyId}/revoke`);
  }
}
