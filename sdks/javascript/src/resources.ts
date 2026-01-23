/**
 * API resource classes for interacting with different endpoints
 */

import type {
  Stream,
  Channel,
  Playlist,
  Webhook,
  WebhookEvent,
  APIKey,
} from './types';
import type { SattvaClient } from './client';

/**
 * Base resource class
 */
class BaseResource {
  constructor(protected client: SattvaClient) {}
}

/**
 * Streams resource
 */
export class StreamsResource extends BaseResource {
  private get: <T>(path: string) => Promise<T>;
  private post: <T>(path: string, body?: any) => Promise<T>;

  constructor(client: SattvaClient) {
    super(client);
    this.get = (path: string) => (client as any).get(path);
    this.post = (path: string, body?: any) => (client as any).post(path, body);
  }

  async list(): Promise<Stream[]> {
    return this.get('/streams');
  }

  async getStream(streamId: string): Promise<Stream> {
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
export class ChannelsResource extends BaseResource {
  private get: <T>(path: string) => Promise<T>;
  private post: <T>(path: string, body?: any) => Promise<T>;
  private patch: <T>(path: string, body?: any) => Promise<T>;
  private del: <T>(path: string) => Promise<T>;

  constructor(client: SattvaClient) {
    super(client);
    this.get = (path: string) => (client as any).get(path);
    this.post = (path: string, body?: any) => (client as any).post(path, body);
    this.patch = (path: string, body?: any) => (client as any).patch(path, body);
    this.del = (path: string) => (client as any).delete(path);
  }

  async list(): Promise<Channel[]> {
    return this.get('/channels');
  }

  async getChannel(channelId: string): Promise<Channel> {
    return this.get(`/channels/${channelId}`);
  }

  async create(data: {
    name: string;
    description?: string;
  }): Promise<Channel> {
    return this.post('/channels', data);
  }

  async update(
    channelId: string,
    data: { name?: string; description?: string }
  ): Promise<Channel> {
    return this.patch(`/channels/${channelId}`, data);
  }

  async delete(channelId: string): Promise<void> {
    return this.del(`/channels/${channelId}`);
  }
}

/**
 * Playlists resource
 */
export class PlaylistsResource extends BaseResource {
  private get: <T>(path: string) => Promise<T>;
  private post: <T>(path: string, body?: any) => Promise<T>;
  private patch: <T>(path: string, body?: any) => Promise<T>;
  private del: <T>(path: string) => Promise<T>;

  constructor(client: SattvaClient) {
    super(client);
    this.get = (path: string) => (client as any).get(path);
    this.post = (path: string, body?: any) => (client as any).post(path, body);
    this.patch = (path: string, body?: any) => (client as any).patch(path, body);
    this.del = (path: string) => (client as any).delete(path);
  }

  async list(): Promise<Playlist[]> {
    return this.get('/playlists');
  }

  async getPlaylist(playlistId: string): Promise<Playlist> {
    return this.get(`/playlists/${playlistId}`);
  }

  async create(data: {
    name: string;
    description?: string;
    track_ids: string[];
  }): Promise<Playlist> {
    return this.post('/playlists', data);
  }

  async update(
    playlistId: string,
    data: { name?: string; description?: string }
  ): Promise<Playlist> {
    return this.patch(`/playlists/${playlistId}`, data);
  }

  async reorder(playlistId: string, data: { track_ids: string[] }): Promise<Playlist> {
    return this.patch(`/playlists/${playlistId}/reorder`, data);
  }

  async delete(playlistId: string): Promise<void> {
    return this.del(`/playlists/${playlistId}`);
  }
}

/**
 * Webhooks resource
 */
export class WebhooksResource extends BaseResource {
  private get: <T>(path: string) => Promise<T>;
  private post: <T>(path: string, body?: any) => Promise<T>;
  private patch: <T>(path: string, body?: any) => Promise<T>;
  private del: <T>(path: string) => Promise<T>;

  constructor(client: SattvaClient) {
    super(client);
    this.get = (path: string) => (client as any).get(path);
    this.post = (path: string, body?: any) => (client as any).post(path, body);
    this.patch = (path: string, body?: any) => (client as any).patch(path, body);
    this.del = (path: string) => (client as any).delete(path);
  }

  async list(): Promise<Webhook[]> {
    return this.get('/webhooks');
  }

  async getWebhook(webhookId: string): Promise<Webhook> {
    return this.get(`/webhooks/${webhookId}`);
  }

  async create(data: {
    url: string;
    event_types: string[];
  }): Promise<Webhook> {
    return this.post('/webhooks', data);
  }

  async update(
    webhookId: string,
    data: { url?: string; event_types?: string[]; is_active?: boolean }
  ): Promise<Webhook> {
    return this.patch(`/webhooks/${webhookId}`, data);
  }

  async delete(webhookId: string): Promise<void> {
    return this.del(`/webhooks/${webhookId}`);
  }

  async test(webhookId: string): Promise<{ success: boolean; message: string }> {
    return this.post(
      `/webhooks/${webhookId}/test`
    );
  }

  async rotateSecret(webhookId: string): Promise<{ secret: string }> {
    return this.post(
      `/webhooks/${webhookId}/rotate-secret`
    );
  }

  async listEvents(webhookId: string): Promise<WebhookEvent[]> {
    return this.get(`/webhooks/${webhookId}/events`);
  }
}

/**
 * API Keys resource
 */
export class APIKeysResource extends BaseResource {
  private get: <T>(path: string) => Promise<T>;
  private post: <T>(path: string, body?: any) => Promise<T>;
  private patch: <T>(path: string, body?: any) => Promise<T>;
  private del: <T>(path: string) => Promise<T>;

  constructor(client: SattvaClient) {
    super(client);
    this.get = (path: string) => (client as any).get(path);
    this.post = (path: string, body?: any) => (client as any).post(path, body);
    this.patch = (path: string, body?: any) => (client as any).patch(path, body);
    this.del = (path: string) => (client as any).delete(path);
  }

  async list(): Promise<APIKey[]> {
    return this.get('/keys');
  }

  async getAPIKey(keyId: string): Promise<APIKey> {
    return this.get(`/keys/${keyId}`);
  }

  async create(data: {
    name: string;
    scopes: string[];
    rate_limit?: number;
    expires_at?: string;
  }): Promise<APIKey & { key: string }> {
    return this.post('/keys', data);
  }

  async update(
    keyId: string,
    data: { name?: string; is_active?: boolean }
  ): Promise<APIKey> {
    return this.patch(`/keys/${keyId}`, data);
  }

  async delete(keyId: string): Promise<void> {
    return this.del(`/keys/${keyId}`);
  }

  async revoke(keyId: string): Promise<void> {
    return this.post(`/keys/${keyId}/revoke`);
  }
}
