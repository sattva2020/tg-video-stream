/**
 * Tests for Sattva API JavaScript/TypeScript SDK Client
 */

import { SattvaClient } from '../src/client';
import {
  SattvaAPIError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ValidationError,
} from '../src/exceptions';
import type {
  Stream,
  Channel,
  Playlist,
  Webhook,
  WebhookEvent,
  APIKey,
} from '../src/types';

// Mock fetch
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('SattvaClient', () => {
  let client: SattvaClient;

  beforeEach(() => {
    client = new SattvaClient({
      apiKey: 'test_api_key_12345',
      baseUrl: 'https://api.test.com/api/v1',
      timeout: 10000,
      maxRetries: 2,
      retryDelay: 1000,
    });

    // Reset fetch mock
    mockFetch.mockReset();
  });

  describe('Initialization', () => {
    test('should initialize with default values', () => {
      const defaultClient = new SattvaClient({
        apiKey: 'test_key',
      });

      expect(defaultClient).toBeInstanceOf(SattvaClient);
      expect(defaultClient['config'].apiKey).toBe('test_key');
      expect(defaultClient['config'].baseUrl).toBe('https://api.sattva-streamer.top/api/v1');
      expect(defaultClient['config'].timeout).toBe(30000);
      expect(defaultClient['config'].maxRetries).toBe(3);
      expect(defaultClient['config'].retryDelay).toBe(1000);
    });

    test('should initialize with custom configuration', () => {
      const customClient = new SattvaClient({
        apiKey: 'custom_key',
        baseUrl: 'https://custom.api.com/v2',
        timeout: 60000,
        maxRetries: 5,
        retryDelay: 2000,
      });

      expect(customClient['config'].apiKey).toBe('custom_key');
      expect(customClient['config'].baseUrl).toBe('https://custom.api.com/v2');
      expect(customClient['config'].timeout).toBe(60000);
      expect(customClient['config'].maxRetries).toBe(5);
      expect(customClient['config'].retryDelay).toBe(2000);
    });

    test('should initialize all resource managers', () => {
      expect(client.streams).toBeDefined();
      expect(client.channels).toBeDefined();
      expect(client.playlists).toBeDefined();
      expect(client.webhooks).toBeDefined();
      expect(client.apiKeys).toBeDefined();
    });
  });

  describe('HTTP Methods', () => {
    test('should make GET request successfully', async () => {
      const mockData = { id: 'test-1', name: 'Test Stream' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await client['get'<Stream>>('/streams/test-1');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/streams/test-1',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'X-API-Key': 'test_api_key_12345',
            'Content-Type': 'application/json',
            Accept: 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockData);
    });

    test('should make POST request successfully', async () => {
      const mockData = { id: 'test-1', name: 'New Stream' };
      const requestBody = { name: 'New Stream' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await client['post'<Stream>>('/streams', requestBody);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/streams',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(requestBody),
        })
      );
      expect(result).toEqual(mockData);
    });

    test('should make PATCH request successfully', async () => {
      const mockData = { id: 'test-1', name: 'Updated Stream' };
      const requestBody = { name: 'Updated Stream' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await client['patch'<Stream>>('/streams/test-1', requestBody);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/streams/test-1',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(requestBody),
        })
      );
      expect(result).toEqual(mockData);
    });

    test('should make DELETE request successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client['delete']('/streams/test-1');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/streams/test-1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    test('should make PUT request successfully', async () => {
      const mockData = { id: 'test-1', name: 'Replaced Stream' };
      const requestBody = { name: 'Replaced Stream' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await client['put'<Stream>>('/streams/test-1', requestBody);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/streams/test-1',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(requestBody),
        })
      );
      expect(result).toEqual(mockData);
    });
  });

  describe('Error Handling', () => {
    test('should throw AuthenticationError on 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Invalid API key' }),
      } as Response);

      await expect(client['get']('/streams')).rejects.toThrow(AuthenticationError);
      await expect(client['get']('/streams')).rejects.toThrow('Invalid API key');
    });

    test('should throw AuthenticationError on 403', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ message: 'Access denied' }),
      } as Response);

      await expect(client['get']('/streams')).rejects.toThrow(AuthenticationError);
    });

    test('should throw NotFoundError on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Stream not found' }),
      } as Response);

      await expect(client['get']('/streams/nonexistent')).rejects.toThrow(NotFoundError);
      await expect(client['get']('/streams/nonexistent')).rejects.toThrow('Stream not found');
    });

    test('should throw ValidationError on 400', async () => {
      const errors = {
        name: ['This field is required'],
        channel_id: ['Invalid channel ID'],
      };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Validation failed', errors }),
      } as Response);

      try {
        await client['post']('/streams', {});
        fail('Should have thrown ValidationError');
      } catch (error) {
        expect(error).toBeInstanceOf(ValidationError);
        if (error instanceof ValidationError) {
          expect(error.message).toBe('Validation failed');
          expect(error.errors).toEqual(errors);
        }
      }
    });

    test('should throw ValidationError on 422', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: async () => ({ message: 'Invalid data' }),
      } as Response);

      await expect(client['post']('/streams', {})).rejects.toThrow(ValidationError);
    });

    test('should throw RateLimitError on 429', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({
          'Retry-After': '60',
        }),
        json: async () => ({ message: 'Rate limit exceeded' }),
      } as Response);

      try {
        await client['get']('/streams');
        fail('Should have thrown RateLimitError');
      } catch (error) {
        expect(error).toBeInstanceOf(RateLimitError);
        if (error instanceof RateLimitError) {
          expect(error.retryAfter).toBe(60);
        }
      }
    });

    test('should throw SattvaAPIError on other errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error' }),
      } as Response);

      try {
        await client['get']('/streams');
        fail('Should have thrown SattvaAPIError');
      } catch (error) {
        expect(error).toBeInstanceOf(SattvaAPIError);
        if (error instanceof SattvaAPIError) {
          expect(error.statusCode).toBe(500);
        }
      }
    });

    test('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(client['get']('/streams')).rejects.toThrow(SattvaAPIError);
    });
  });

  describe('Rate Limiting and Retry Logic', () => {
    test('should retry on 429 status code', async () => {
      // First call fails with 429
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers(),
        json: async () => ({ message: 'Rate limit exceeded' }),
      } as Response);

      // Second call succeeds
      const mockData = { id: 'test-1', name: 'Test Stream' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await client['get'<Stream>>('/streams');

      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(result).toEqual(mockData);
    });

    test('should respect Retry-After header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({
          'Retry-After': '2',
        }),
        json: async () => ({ message: 'Rate limit exceeded' }),
      } as Response);

      const mockData = { id: 'test-1' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const startTime = Date.now();
      await client['get']('/streams');
      const endTime = Date.now();

      // Should wait at least 2 seconds (2000ms)
      expect(endTime - startTime).toBeGreaterThanOrEqual(1900);
    });

    test('should use exponential backoff when Retry-After not provided', async () => {
      const clientWithRetry = new SattvaClient({
        apiKey: 'test',
        maxRetries: 3,
        retryDelay: 100,
      });

      // First call fails
      mockFetch.mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers(),
        json: async () => ({ message: 'Rate limit' }),
      } as Response);

      const startTime = Date.now();
      await clientWithRetry['get']('/streams').catch(() => {
        // Expected to fail after max retries
      });
      const endTime = Date.now();

      // Should have tried 4 times (1 initial + 3 retries)
      expect(mockFetch).toHaveBeenCalledTimes(4);
    });

    test('should stop retrying after max retries', async () => {
      const clientWithLimitedRetries = new SattvaClient({
        apiKey: 'test',
        maxRetries: 1,
        retryDelay: 100,
      });

      mockFetch.mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers(),
        json: async () => ({ message: 'Rate limit' }),
      } as Response);

      await expect(clientWithLimitedRetries['get']('/streams')).rejects.toThrow(RateLimitError);
      expect(mockFetch).toHaveBeenCalledTimes(2); // 1 initial + 1 retry
    });
  });

  describe('Timeout Handling', () => {
    test('should timeout request after configured time', async () => {
      const shortTimeoutClient = new SattvaClient({
        apiKey: 'test',
        timeout: 100,
      });

      // Simulate slow response
      mockFetch.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({ id: 'test' }),
                } as Response),
              200
            );
          })
      );

      await expect(shortTimeoutClient['get']('/streams')).rejects.toThrow();
    });
  });

  describe('Streams Resource', () => {
    test('should list streams', async () => {
      const mockStreams: Stream[] = [
        {
          id: 'stream-1',
          channel_id: 'channel-1',
          status: 'live',
          started_at: '2024-01-23T10:00:00Z',
        },
        {
          id: 'stream-2',
          channel_id: 'channel-2',
          status: 'stopped',
          stopped_at: '2024-01-23T11:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStreams,
      } as Response);

      const result = await client.streams.list();

      expect(result).toEqual(mockStreams);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/streams'),
        expect.any(Object)
      );
    });

    test('should get stream by ID', async () => {
      const mockStream: Stream = {
        id: 'stream-1',
        channel_id: 'channel-1',
        status: 'live',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStream,
      } as Response);

      const result = await client.streams.getStream('stream-1');

      expect(result).toEqual(mockStream);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/streams/stream-1'),
        expect.any(Object)
      );
    });

    test('should start stream', async () => {
      const mockStream: Stream = {
        id: 'stream-1',
        channel_id: 'channel-1',
        status: 'starting',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStream,
      } as Response);

      const result = await client.streams.start('channel-1');

      expect(result).toEqual(mockStream);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/streams/start'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ channel_id: 'channel-1' }),
        })
      );
    });

    test('should stop stream', async () => {
      const mockStream: Stream = {
        id: 'stream-1',
        channel_id: 'channel-1',
        status: 'stopped',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStream,
      } as Response);

      const result = await client.streams.stop('stream-1');

      expect(result).toEqual(mockStream);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/streams/stream-1/stop'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    test('should restart stream', async () => {
      const mockStream: Stream = {
        id: 'stream-1',
        channel_id: 'channel-1',
        status: 'starting',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStream,
      } as Response);

      const result = await client.streams.restart('stream-1');

      expect(result).toEqual(mockStream);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/streams/stream-1/restart'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('Channels Resource', () => {
    test('should list channels', async () => {
      const mockChannels: Channel[] = [
        {
          id: 'channel-1',
          name: 'Channel 1',
          is_active: true,
          created_at: '2024-01-23T10:00:00Z',
          updated_at: '2024-01-23T10:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockChannels,
      } as Response);

      const result = await client.channels.list();

      expect(result).toEqual(mockChannels);
    });

    test('should get channel by ID', async () => {
      const mockChannel: Channel = {
        id: 'channel-1',
        name: 'Test Channel',
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockChannel,
      } as Response);

      const result = await client.channels.getChannel('channel-1');

      expect(result).toEqual(mockChannel);
    });

    test('should create channel', async () => {
      const mockChannel: Channel = {
        id: 'channel-1',
        name: 'New Channel',
        description: 'Test description',
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockChannel,
      } as Response);

      const result = await client.channels.create({
        name: 'New Channel',
        description: 'Test description',
      });

      expect(result).toEqual(mockChannel);
    });

    test('should update channel', async () => {
      const mockChannel: Channel = {
        id: 'channel-1',
        name: 'Updated Channel',
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T11:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockChannel,
      } as Response);

      const result = await client.channels.update('channel-1', {
        name: 'Updated Channel',
      });

      expect(result).toEqual(mockChannel);
    });

    test('should delete channel', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client.channels.delete('channel-1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/channels/channel-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('Playlists Resource', () => {
    test('should list playlists', async () => {
      const mockPlaylists: Playlist[] = [
        {
          id: 'playlist-1',
          name: 'Playlist 1',
          track_ids: ['track-1', 'track-2'],
          is_active: true,
          created_at: '2024-01-23T10:00:00Z',
          updated_at: '2024-01-23T10:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlaylists,
      } as Response);

      const result = await client.playlists.list();

      expect(result).toEqual(mockPlaylists);
    });

    test('should get playlist by ID', async () => {
      const mockPlaylist: Playlist = {
        id: 'playlist-1',
        name: 'Test Playlist',
        track_ids: ['track-1'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlaylist,
      } as Response);

      const result = await client.playlists.getPlaylist('playlist-1');

      expect(result).toEqual(mockPlaylist);
    });

    test('should create playlist', async () => {
      const mockPlaylist: Playlist = {
        id: 'playlist-1',
        name: 'New Playlist',
        track_ids: ['track-1', 'track-2'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlaylist,
      } as Response);

      const result = await client.playlists.create({
        name: 'New Playlist',
        track_ids: ['track-1', 'track-2'],
      });

      expect(result).toEqual(mockPlaylist);
    });

    test('should update playlist', async () => {
      const mockPlaylist: Playlist = {
        id: 'playlist-1',
        name: 'Updated Playlist',
        track_ids: ['track-1'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T11:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlaylist,
      } as Response);

      const result = await client.playlists.update('playlist-1', {
        name: 'Updated Playlist',
      });

      expect(result).toEqual(mockPlaylist);
    });

    test('should reorder playlist', async () => {
      const mockPlaylist: Playlist = {
        id: 'playlist-1',
        name: 'Playlist',
        track_ids: ['track-2', 'track-1'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T11:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlaylist,
      } as Response);

      const result = await client.playlists.reorder('playlist-1', {
        track_ids: ['track-2', 'track-1'],
      });

      expect(result).toEqual(mockPlaylist);
    });

    test('should delete playlist', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client.playlists.delete('playlist-1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/playlists/playlist-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('Webhooks Resource', () => {
    test('should list webhooks', async () => {
      const mockWebhooks: Webhook[] = [
        {
          id: 'webhook-1',
          url: 'https://example.com/webhook',
          event_types: ['stream.started'],
          is_active: true,
          failure_count: 0,
          created_at: '2024-01-23T10:00:00Z',
          updated_at: '2024-01-23T10:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockWebhooks,
      } as Response);

      const result = await client.webhooks.list();

      expect(result).toEqual(mockWebhooks);
    });

    test('should get webhook by ID', async () => {
      const mockWebhook: Webhook = {
        id: 'webhook-1',
        url: 'https://example.com/webhook',
        event_types: ['stream.started'],
        is_active: true,
        failure_count: 0,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockWebhook,
      } as Response);

      const result = await client.webhooks.getWebhook('webhook-1');

      expect(result).toEqual(mockWebhook);
    });

    test('should create webhook', async () => {
      const mockWebhook: Webhook = {
        id: 'webhook-1',
        url: 'https://example.com/webhook',
        event_types: ['stream.started', 'stream.stopped'],
        secret: 'test_secret',
        is_active: true,
        failure_count: 0,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockWebhook,
      } as Response);

      const result = await client.webhooks.create({
        url: 'https://example.com/webhook',
        event_types: ['stream.started', 'stream.stopped'],
      });

      expect(result).toEqual(mockWebhook);
    });

    test('should update webhook', async () => {
      const mockWebhook: Webhook = {
        id: 'webhook-1',
        url: 'https://example.com/webhook-updated',
        event_types: ['stream.started'],
        is_active: true,
        failure_count: 0,
        created_at: '2024-01-23T10:00:00Z',
        updated_at: '2024-01-23T11:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockWebhook,
      } as Response);

      const result = await client.webhooks.update('webhook-1', {
        url: 'https://example.com/webhook-updated',
      });

      expect(result).toEqual(mockWebhook);
    });

    test('should delete webhook', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client.webhooks.delete('webhook-1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/webhooks/webhook-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    test('should test webhook', async () => {
      const mockResponse = {
        success: true,
        message: 'Webhook test successful',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.webhooks.test('webhook-1');

      expect(result).toEqual(mockResponse);
    });

    test('should rotate webhook secret', async () => {
      const mockResponse = {
        secret: 'new_secret_value',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.webhooks.rotateSecret('webhook-1');

      expect(result).toEqual(mockResponse);
    });

    test('should list webhook events', async () => {
      const mockEvents: WebhookEvent[] = [
        {
          id: 'event-1',
          webhook_id: 'webhook-1',
          event_type: 'stream.started',
          event_id: 'stream-event-1',
          status: 'success',
          attempt_number: 1,
          attempted_at: '2024-01-23T10:00:00Z',
          should_retry: false,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEvents,
      } as Response);

      const result = await client.webhooks.listEvents('webhook-1');

      expect(result).toEqual(mockEvents);
    });
  });

  describe('API Keys Resource', () => {
    test('should list API keys', async () => {
      const mockKeys: APIKey[] = [
        {
          id: 'key-1',
          name: 'Test Key',
          scopes: ['read:streams'],
          is_active: true,
          created_at: '2024-01-23T10:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockKeys,
      } as Response);

      const result = await client.apiKeys.list();

      expect(result).toEqual(mockKeys);
    });

    test('should get API key by ID', async () => {
      const mockKey: APIKey = {
        id: 'key-1',
        name: 'Test Key',
        scopes: ['read:streams', 'write:streams'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockKey,
      } as Response);

      const result = await client.apiKeys.getAPIKey('key-1');

      expect(result).toEqual(mockKey);
    });

    test('should create API key', async () => {
      const mockKey: APIKey & { key: string } = {
        id: 'key-1',
        key: 'sk_test_12345',
        name: 'New Key',
        scopes: ['read:streams'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockKey,
      } as Response);

      const result = await client.apiKeys.create({
        name: 'New Key',
        scopes: ['read:streams'],
      });

      expect(result).toEqual(mockKey);
      expect(result.key).toBe('sk_test_12345');
    });

    test('should update API key', async () => {
      const mockKey: APIKey = {
        id: 'key-1',
        name: 'Updated Key',
        scopes: ['read:streams'],
        is_active: true,
        created_at: '2024-01-23T10:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockKey,
      } as Response);

      const result = await client.apiKeys.update('key-1', {
        name: 'Updated Key',
      });

      expect(result).toEqual(mockKey);
    });

    test('should delete API key', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client.apiKeys.delete('key-1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/keys/key-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    test('should revoke API key', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await client.apiKeys.revoke('key-1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/keys/key-1/revoke'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('Request Headers', () => {
    test('should include correct headers in request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 'test' }),
      } as Response);

      await client['get']('/streams');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'test_api_key_12345',
            'Content-Type': 'application/json',
            Accept: 'application/json',
          }),
        })
      );
    });
  });
});
