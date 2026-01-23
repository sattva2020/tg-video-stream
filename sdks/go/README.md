# Sattva API Go SDK

Official Go SDK for the Sattva API - a comprehensive streaming platform API.

## Installation

```bash
go get github.com/sattva/sattva-go-sdk
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    // Initialize the client with your API key
    client := sattva.NewClient(
        "your-api-key-here",
        sattva.WithBaseURL("https://api.sattva.io/api/v1"),
    )

    ctx := context.Background()

    // List streams
    streams, err := client.Streams.List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    for _, stream := range streams {
        fmt.Printf("Stream: %s - %s\n", stream.Name, stream.Status)
    }

    // Start a stream
    response, err := client.Streams.Start(ctx, "channel-123")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Stream started: %v\n", response)

    // Create a webhook subscription
    webhook, err := client.Webhooks.Create(ctx, &sattva.WebhookCreateRequest{
        URL:        "https://example.com/webhooks",
        EventTypes: []string{"stream.started", "stream.stopped"},
    })
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Webhook created: %v\n", webhook)
}
```

## Authentication

The SDK uses API keys for authentication. You can create API keys through the Sattva dashboard or API.

```go
client := sattva.NewClient(
    "sk_live_xxxxxxxxxxxx",  // Your API key
    sattva.WithBaseURL("https://api.sattva.io/api/v1"),
)
```

### API Key Security

- Never commit API keys to version control
- Use environment variables for API keys in production
- Rotate API keys regularly
- Use different keys for development and production

```go
apiKey := os.Getenv("SATTVA_API_KEY")
client := sattva.NewClient(apiKey)
```

## Features

- **Stream Management**: Start, stop, pause, and resume streams
- **Playlist Control**: Manage playlists, tracks, and playback
- **Channel Management**: Configure and control streaming channels
- **Webhook Subscriptions**: Subscribe to real-time events
- **API Key Management**: Create and manage API keys
- **Rate Limiting**: Built-in rate limit handling
- **Context Support**: Full context.Context support for cancellation and timeouts

## Usage Examples

### Managing Streams

```go
ctx := context.Background()
client := sattva.NewClient(apiKey)

// List all active streams
streams, err := client.Streams.List(ctx)
if err != nil {
    log.Fatal(err)
}

for _, stream := range streams {
    fmt.Printf("Stream %s: %s\n", stream.ID, stream.Status)
}

// Start a new stream on a channel
response, err := client.Streams.Start(ctx, "channel-123")
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Stream started with ID: %s\n", response.StreamID)

// Stop a running stream
err = client.Streams.Stop(ctx, "stream-123")
if err != nil {
    log.Fatal(err)
}

// Pause and resume streams
err = client.Streams.Pause(ctx, "stream-123")
if err != nil {
    log.Fatal(err)
}

err = client.Streams.Resume(ctx, "stream-123")
if err != nil {
    log.Fatal(err)
}
```

### Working with Playlists

```go
// Create a new playlist
playlist, err := client.Playlists.Create(ctx, &sattva.PlaylistCreateRequest{
    Name:        "My Music Playlist",
    Description: "Favorite tracks",
})
if err != nil {
    log.Fatal(err)
}

// Add tracks and manage playback
updated, err := client.Playlists.Update(ctx, playlist.ID, &sattva.PlaylistUpdateRequest{
    TrackIDs: []string{"track-1", "track-2", "track-3"},
})
if err != nil {
    log.Fatal(err)
}

// Get playlist status
status, err := client.Playlists.GetStatus(ctx, playlist.ID)
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Current track: %s\n", status.CurrentTrack)
```

### Setting Up Webhooks

```go
// Subscribe to stream events
webhook, err := client.Webhooks.Create(ctx, &sattva.WebhookCreateRequest{
    URL: "https://your-app.com/webhooks",
    EventTypes: []string{
        "stream.started",
        "stream.stopped",
        "stream.error",
    },
})
if err != nil {
    log.Fatal(err)
}

// Test the webhook
result, err := client.Webhooks.Test(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Test result: %v\n", result.Success)

// List webhook events
events, err := client.Webhooks.ListEvents(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}

for _, event := range events {
    fmt.Printf("Event %s: %s\n", event.EventType, event.Status)
}
```

### Managing API Keys

```go
// Create a new API key with limited scopes
key, err := client.APIKeys.Create(ctx, &sattva.APIKeyCreateRequest{
    Name:   "Read-only Integration",
    Scopes: []string{"read:streams", "read:playlists"},
})
if err != nil {
    log.Fatal(err)
}

// Store the key value securely
apiKeyValue := key.Key

// List all your API keys
keys, err := client.APIKeys.List(ctx)
if err != nil {
    log.Fatal(err)
}

for _, key := range keys {
    fmt.Printf("%s: %v\n", key.Name, key.Scopes)
}

// Revoke a compromised key
err = client.APIKeys.Revoke(ctx, "key-123")
if err != nil {
    log.Fatal(err)
}
```

### Working with Channels

```go
// List channels
channels, err := client.Channels.List(ctx)
if err != nil {
    log.Fatal(err)
}

// Get a specific channel
channel, err := client.Channels.Get(ctx, "channel-123")
if err != nil {
    log.Fatal(err)
}

// Create a channel
channel, err := client.Channels.Create(ctx, &sattva.ChannelCreateRequest{
    Name: "My Channel",
    URL:  "https://example.com/stream",
})
if err != nil {
    log.Fatal(err)
}

// Update a channel
updated, err := client.Channels.Update(ctx, channel.ID, &sattva.ChannelUpdateRequest{
    Name: "Updated Channel",
})
if err != nil {
    log.Fatal(err)
}

// Delete a channel
err = client.Channels.Delete(ctx, channel.ID)
if err != nil {
    log.Fatal(err)
}
```

### Context and Timeouts

```go
import (
    "context"
    "time"
)

// Create context with timeout
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

// Use context for cancellation
ctx, cancel = context.WithCancel(context.Background())
go func() {
    // Cancel after some condition
    cancel()
}()

streams, err := client.Streams.List(ctx)
if err != nil {
    log.Fatal(err)
}
```

### Custom Configuration

```go
// Configure retry behavior and timeouts
client := sattva.NewClient(
    apiKey,
    sattva.WithBaseURL("https://api.sattva.io/api/v1"),
    sattva.WithTimeout(30*time.Second),
    sattva.WithMaxRetries(5),
    sattva.WithRetryDelay(2*time.Second),
)
```

## Error Handling

The SDK returns errors for API failures:

```go
import (
    "errors"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

client := sattva.NewClient(apiKey)

stream, err := client.Streams.Get(ctx, "stream-123")
if err != nil {
    var authErr *sattva.AuthenticationError
    var rateLimitErr *sattva.RateLimitError
    var notFoundErr *sattva.NotFoundError

    switch {
    case errors.As(err, &authErr):
        log.Println("Invalid API key")
    case errors.As(err, &rateLimitErr):
        log.Printf("Rate limit exceeded: %v", rateLimitErr.RetryAfter)
    case errors.As(err, &notFoundErr):
        log.Println("Stream not found")
    default:
        log.Printf("API error: %v", err)
    }
    return
}

fmt.Printf("Stream: %v\n", stream)
```

## Rate Limiting

The SDK automatically handles rate limiting:

```go
import "time"

client := sattva.NewClient(
    apiKey,
    sattva.WithMaxRetries(3),             // Number of retries on rate limit
    sattva.WithRetryDelay(1*time.Second), // Delay between retries
)
```

## Webhook Signature Verification

Verify webhook signatures to ensure requests are from Sattva:

```go
import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "io"
    "net/http"
)

func webhookHandler(w http.ResponseWriter, r *http.Request) {
    // Read the payload
    payload, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read body", http.StatusBadRequest)
        return
    }

    // Get signature from header
    signature := r.Header.Get("X-Sattva-Signature")
    secret := "your-webhook-secret"

    // Verify signature
    if !sattva.VerifyWebhookSignature(payload, signature, secret) {
        http.Error(w, "Invalid signature", http.StatusUnauthorized)
        return
    }

    // Process the event
    event := sattva.WebhookEvent{}
    if err := json.Unmarshal(payload, &event); err != nil {
        http.Error(w, "Invalid payload", http.StatusBadRequest)
        return
    }

    fmt.Printf("Received event: %s\n", event.Type)

    w.WriteHeader(http.StatusOK)
}
```

## Resources

### Streams

```go
// List all streams
streams, err := client.Streams.List(ctx)

// Get a specific stream
stream, err := client.Streams.Get(ctx, "stream-123")

// Start a stream
response, err := client.Streams.Start(ctx, "channel-123")

// Stop a stream
response, err := client.Streams.Stop(ctx, "stream-123")

// Pause a stream
response, err := client.Streams.Pause(ctx, "stream-123")

// Resume a stream
response, err := client.Streams.Resume(ctx, "stream-123")
```

### Playlists

```go
// List playlists
playlists, err := client.Playlists.List(ctx)

// Get a playlist
playlist, err := client.Playlists.Get(ctx, "playlist-123")

// Create a playlist
playlist, err := client.Playlists.Create(ctx, &sattva.PlaylistCreateRequest{
    Name:        "My Playlist",
    Description: "A great playlist",
})

// Update a playlist
playlist, err := client.Playlists.Update(ctx, "playlist-123", &sattva.PlaylistUpdateRequest{
    Name: "Updated Name",
})

// Delete a playlist
err := client.Playlists.Delete(ctx, "playlist-123")
```

### Channels

```go
// List channels
channels, err := client.Channels.List(ctx)

// Get a channel
channel, err := client.Channels.Get(ctx, "channel-123")

// Create a channel
channel, err := client.Channels.Create(ctx, &sattva.ChannelCreateRequest{
    Name: "My Channel",
    URL:  "https://example.com/stream",
})

// Update a channel
channel, err := client.Channels.Update(ctx, "channel-123", &sattva.ChannelUpdateRequest{
    Name: "Updated Channel",
})

// Delete a channel
err := client.Channels.Delete(ctx, "channel-123")
```

### Webhooks

```go
// List webhooks
webhooks, err := client.Webhooks.List(ctx)

// Get a webhook
webhook, err := client.Webhooks.Get(ctx, "webhook-123")

// Create a webhook
webhook, err := client.Webhooks.Create(ctx, &sattva.WebhookCreateRequest{
    URL:        "https://example.com/webhooks",
    EventTypes: []string{"stream.started", "stream.stopped", "stream.error"},
})

// Test a webhook
result, err := client.Webhooks.Test(ctx, "webhook-123")

// Rotate webhook secret
webhook, err := client.Webhooks.RotateSecret(ctx, "webhook-123")

// Delete a webhook
err := client.Webhooks.Delete(ctx, "webhook-123")
```

### API Keys

```go
// List API keys
keys, err := client.APIKeys.List(ctx)

// Create an API key
key, err := client.APIKeys.Create(ctx, &sattva.APIKeyCreateRequest{
    Name:   "My Integration",
    Scopes: []string{"read:streams", "write:streams"},
})
// Save the key value - it won't be shown again
apiKeyValue := key.Key

// Revoke an API key
err := client.APIKeys.Revoke(ctx, "key-123")
```

## Development

### Installation for Development

```bash
git clone https://github.com/sattva/sattva-go-sdk.git
cd sattva-go-sdk
go mod download
```

### Running Tests

```bash
go test ./... -v
```

### Running Tests with Coverage

```bash
go test ./... -cover -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Code Formatting

```bash
go fmt ./...
go vet ./...
gofmt -l .
```

## API Reference

Full API documentation is available at [https://docs.sattva.io](https://docs.sattva.io)

## Event Types

The following webhook events are available:

- `stream.started` - Stream has started
- `stream.stopped` - Stream has stopped
- `stream.paused` - Stream has been paused
- `stream.resumed` - Stream has been resumed
- `stream.error` - Stream encountered an error
- `viewer.milestone` - Viewer milestone reached
- `viewer.joined` - Viewer joined the stream
- `viewer.left` - Viewer left the stream
- `track.started` - Track started playing
- `track.completed` - Track finished playing
- `track.failed` - Track failed to play
- `track.skipped` - Track was skipped

## Support

- Documentation: [https://docs.sattva.io](https://docs.sattva.io)
- Bug Reports: [GitHub Issues](https://github.com/sattva/sattva-go-sdk/issues)
- Email: api@sattva.io

## License

MIT License - see LICENSE file for details
