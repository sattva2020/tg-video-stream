# @sattva/api-client

Official JavaScript/TypeScript SDK for the Sattva Streaming Platform API.

## Installation

```bash
npm install @sattva/api-client
# or
yarn add @sattva/api-client
# or
pnpm add @sattva/api-client
```

## Features

- 🚀 Full TypeScript support with comprehensive types
- 🔑 API key authentication
- 📡 Webhook signature verification
- 🔄 Automatic retry logic for rate-limited requests
- 🎯 All API resources supported (streams, channels, playlists, webhooks)
- 📦 Works in Node.js, browsers, and edge runtimes
- 🌐 ESM and CommonJS support

## Quick Start

```typescript
import { SattvaClient } from '@sattva/api-client';

// Initialize client
const client = new SattvaClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.sattva-streamer.top/api/v1'
});

// List streams
const streams = await client.streams.list();
console.log(streams);

// Start a stream
const stream = await client.streams.start('channel-id');
console.log('Stream started:', stream);

// Create a webhook subscription
const webhook = await client.webhooks.create({
  url: 'https://example.com/webhook',
  event_types: ['stream.started', 'stream.stopped']
});
console.log('Webhook created:', webhook);
```

## Authentication

The SDK uses API keys for authentication. You can create API keys through the Sattva dashboard or API.

```typescript
const client = new SattvaClient({
  apiKey: 'sk_live_xxxxxxxxxxxx',  // Your API key
  baseUrl: 'https://api.sattva-streamer.top/api/v1'
});
```

### API Key Security

- Never commit API keys to version control
- Use environment variables for API keys in production
- Rotate API keys regularly
- Use different keys for development and production

```typescript
// Using environment variables (recommended)
const client = new SattvaClient({
  apiKey: process.env.SATTVA_API_KEY!,
  baseUrl: process.env.SATTVA_API_URL || 'https://api.sattva-streamer.top/api/v1'
});
```

## Usage Examples

### Managing Channels

```typescript
// List all channels
const channels = await client.channels.list();

// Get specific channel
const channel = await client.channels.get('channel-id');

// Create a new channel
const newChannel = await client.channels.create({
  name: 'My Channel',
  description: 'Channel description'
});

// Update channel
await client.channels.update('channel-id', {
  name: 'Updated Channel Name'
});

// Delete channel
await client.channels.delete('channel-id');
```

### Managing Streams

```typescript
// Start stream
const stream = await client.streams.start('channel-id');

// Stop stream
await client.streams.stop('channel-id');

// Restart stream
const restarted = await client.streams.restart('channel-id');

// Get stream status
const status = await client.streams.get('stream-id');
```

### Managing Playlists

```typescript
// List playlists
const playlists = await client.playlists.list();

// Create playlist
const playlist = await client.playlists.create({
  name: 'My Playlist',
  track_ids: ['track-1', 'track-2']
});

// Update playlist
await client.playlists.update('playlist-id', {
  name: 'Updated Playlist'
});

// Reorder tracks
await client.playlists.reorder('playlist-id', {
  track_ids: ['track-2', 'track-1']
});

// Delete playlist
await client.playlists.delete('playlist-id');
```

### Managing Webhooks

```typescript
// List webhooks
const webhooks = await client.webhooks.list();

// Create webhook
const webhook = await client.webhooks.create({
  url: 'https://example.com/webhook',
  event_types: ['stream.started', 'stream.stopped']
});
console.log('Webhook secret:', webhook.secret); // Only available on creation

// Test webhook
await client.webhooks.test('webhook-id');

// Rotate secret
const newSecret = await client.webhooks.rotateSecret('webhook-id');

// List webhook events
const events = await client.webhooks.listEvents('webhook-id');

// Delete webhook
await client.webhooks.delete('webhook-id');
```

### Verifying Webhook Signatures

```typescript
import { verifyWebhookSignature } from '@sattva/api-client/webhook';

// Express.js example
app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const payload = req.body;

  if (verifyWebhookSignature(payload, signature, webhookSecret)) {
    // Signature is valid, process webhook
    console.log('Event type:', payload.event_type);
    console.log('Event data:', payload.data);
    res.sendStatus(200);
  } else {
    // Invalid signature
    res.sendStatus(401);
  }
});
```

## Configuration

```typescript
const client = new SattvaClient({
  // Required
  apiKey: 'your-api-key',

  // Optional
  baseUrl: 'https://api.sattva-streamer.top/api/v1',
  timeout: 30000,          // Request timeout in milliseconds (default: 30000)
  maxRetries: 3,           // Max retries for rate-limited requests (default: 3)
  retryDelay: 1000,        // Initial retry delay in milliseconds (default: 1000)
});
```

## Resources

### Streams

```typescript
// List all streams
const streams = await client.streams.list();

// Get a specific stream
const stream = await client.streams.get('stream-id');

// Start a stream
const response = await client.streams.start('channel-id');

// Stop a stream
await client.streams.stop('stream-id');

// Restart a stream
const restarted = await client.streams.restart('stream-id');
```

### Channels

```typescript
// List all channels
const channels = await client.channels.list();

// Get a specific channel
const channel = await client.channels.get('channel-id');

// Create a new channel
const newChannel = await client.channels.create({
  name: 'My Channel',
  description: 'Channel description',
  url: 'https://example.com/stream'
});

// Update channel
await client.channels.update('channel-id', {
  name: 'Updated Channel Name'
});

// Delete channel
await client.channels.delete('channel-id');
```

### Playlists

```typescript
// List playlists
const playlists = await client.playlists.list();

// Get a playlist
const playlist = await client.playlists.get('playlist-id');

// Create playlist
const playlist = await client.playlists.create({
  name: 'My Playlist',
  track_ids: ['track-1', 'track-2']
});

// Update playlist
await client.playlists.update('playlist-id', {
  name: 'Updated Playlist'
});

// Reorder tracks
await client.playlists.reorder('playlist-id', {
  track_ids: ['track-2', 'track-1']
});

// Delete playlist
await client.playlists.delete('playlist-id');
```

### Webhooks

```typescript
// List webhooks
const webhooks = await client.webhooks.list();

// Get a webhook
const webhook = await client.webhooks.get('webhook-id');

// Create webhook
const webhook = await client.webhooks.create({
  url: 'https://example.com/webhook',
  event_types: ['stream.started', 'stream.stopped']
});
console.log('Webhook secret:', webhook.secret); // Only available on creation

// Test webhook
await client.webhooks.test('webhook-id');

// Rotate secret
const newSecret = await client.webhooks.rotateSecret('webhook-id');

// List webhook events
const events = await client.webhooks.listEvents('webhook-id');

// Delete webhook
await client.webhooks.delete('webhook-id');
```

### API Keys

```typescript
// List API keys
const keys = await client.apiKeys.list();

// Create an API key
const key = await client.apiKeys.create({
  name: 'My Integration',
  scopes: ['read:streams', 'write:streams']
});
// Save the key value - it won't be shown again
const apiKeyValue = key.key;

// Revoke an API key
await client.apiKeys.revoke('key-id');
```

## Error Handling

The SDK throws typed errors for different scenarios:

```typescript
import {
  SattvaAPIError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ValidationError
} from '@sattva/api-client';

try {
  await client.streams.start('channel-id');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error('Rate limit exceeded, retry after:', error.retryAfter);
  } else if (error instanceof NotFoundError) {
    console.error('Channel not found');
  } else if (error instanceof ValidationError) {
    console.error('Validation error:', error.errors);
  } else {
    console.error('API error:', error.message);
  }
}
```

## API Reference

See [API Documentation](https://docs.sattva-streamer.top/api) for complete API reference.

## Webhook Events

The SDK can verify webhook signatures for these event types:

- `stream.started` - Stream has started
- `stream.stopped` - Stream has stopped
- `stream.paused` - Stream has paused
- `stream.resumed` - Stream has resumed
- `stream.error` - Stream error occurred
- `viewer.milestone` - Viewer count milestone reached
- `viewer.joined` - Viewer joined the stream
- `viewer.left` - Viewer left the stream
- `track.started` - Track started playing
- `track.completed` - Track completed
- `track.failed` - Track failed to play
- `track.skipped` - Track was skipped

## Rate Limiting

The SDK automatically handles rate limiting with exponential backoff:

```typescript
const client = new SattvaClient({
  apiKey: 'your-api-key',
  maxRetries: 3,      // Max retries for rate-limited requests (default: 3)
  retryDelay: 1000    // Initial retry delay in milliseconds (default: 1000)
});

// When rate limit is hit, SDK automatically retries with exponential backoff
// Retry delays: 1000ms, 2000ms, 4000ms, etc.
```

## Development

### Installation for Development

```bash
git clone https://github.com/sattva-streamer/sattva-js-sdk.git
cd sattva-js-sdk
npm install
```

### Building

```bash
npm run build
```

### Running Tests

```bash
npm test
```

### Code Formatting

```bash
npm run format    # Format with Prettier
npm run lint      # Lint with ESLint
npm run type-check # Type check with TypeScript
```

## TypeScript Support

The SDK is written in TypeScript and includes full type definitions:

```typescript
import { SattvaClient, Stream, Playlist, Webhook } from '@sattva/api-client';

const client: SattvaClient = new SattvaClient({
  apiKey: 'your-api-key'
});

// Types are automatically inferred
const streams: Stream[] = await client.streams.list();
const playlist: Playlist = await client.playlists.get('playlist-id');
const webhook: Webhook = await client.webhooks.create({
  url: 'https://example.com/webhook',
  event_types: ['stream.started']
});
```

## Browser Support

The SDK works in modern browsers and includes polyfills for the Web Crypto API:

```typescript
// Works in browsers that support:
// - ES2017+ (async/await)
// - fetch API
// - Web Crypto API (or polyfilled)
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: browserApiKey
});
```

## License

MIT

## Support

- Documentation: https://docs.sattva-streamer.top
- GitHub: https://github.com/sattva-streamer/sattva-js-sdk
- Issues: https://github.com/sattva-streamer/sattva-js-sdk/issues
