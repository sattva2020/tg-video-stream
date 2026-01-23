package sattva

import (
	"context"
	"encoding/json"
	"time"
)

// ClientConfig holds the configuration for the Sattva API client.
type ClientConfig struct {
	APIKey     string
	BaseURL    string
	Timeout    time.Duration
	MaxRetries int
	RetryDelay time.Duration
}

// ClientOption is a function that configures the ClientConfig.
type ClientOption func(*ClientConfig)

// WithBaseURL sets the base URL for the API.
func WithBaseURL(baseURL string) ClientOption {
	return func(c *ClientConfig) {
		c.BaseURL = baseURL
	}
}

// WithTimeout sets the request timeout.
func WithTimeout(timeout time.Duration) ClientOption {
	return func(c *ClientConfig) {
		c.Timeout = timeout
	}
}

// WithMaxRetries sets the maximum number of retries for rate-limited requests.
func WithMaxRetries(maxRetries int) ClientOption {
	return func(c *ClientConfig) {
		c.MaxRetries = maxRetries
	}
}

// WithRetryDelay sets the delay between retries.
func WithRetryDelay(retryDelay time.Duration) ClientOption {
	return func(c *ClientConfig) {
		c.RetryDelay = retryDelay
	}
}

// Stream represents a Sattva stream.
type Stream struct {
	ID           string                 `json:"id"`
	ChannelID    string                 `json:"channel_id"`
	Status       string                 `json:"status"`
	StartedAt    *time.Time             `json:"started_at,omitempty"`
	StoppedAt    *time.Time             `json:"stopped_at,omitempty"`
	ErrorMessage string                 `json:"error_message,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// StreamStartResponse represents the response when starting a stream.
type StreamStartResponse struct {
	StreamID   string `json:"stream_id"`
	ChannelID  string `json:"channel_id"`
	Status     string `json:"status"`
	Message    string `json:"message"`
	StreamURL  string `json:"stream_url,omitempty"`
}

// StreamStopResponse represents the response when stopping a stream.
type StreamStopResponse struct {
	StreamID string `json:"stream_id"`
	Status   string `json:"status"`
	Message  string `json:"message"`
}

// Channel represents a Sattva channel.
type Channel struct {
	ID          string     `json:"id"`
	Name        string     `json:"name"`
	Description string     `json:"description,omitempty"`
	ThumbnailURL string    `json:"thumbnail_url,omitempty"`
	IsActive    bool       `json:"is_active"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
}

// ChannelCreateRequest represents a request to create a channel.
type ChannelCreateRequest struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	URL         string `json:"url,omitempty"`
}

// ChannelUpdateRequest represents a request to update a channel.
type ChannelUpdateRequest struct {
	Name        string `json:"name,omitempty"`
	Description string `json:"description,omitempty"`
	URL         string `json:"url,omitempty"`
}

// Playlist represents a Sattva playlist.
type Playlist struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Description string  `json:"description,omitempty"`
	TrackIDs  []string  `json:"track_ids"`
	IsActive  bool      `json:"is_active"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// PlaylistCreateRequest represents a request to create a playlist.
type PlaylistCreateRequest struct {
	Name        string   `json:"name"`
	Description string   `json:"description,omitempty"`
	TrackIDs    []string `json:"track_ids,omitempty"`
}

// PlaylistUpdateRequest represents a request to update a playlist.
type PlaylistUpdateRequest struct {
	Name        string   `json:"name,omitempty"`
	Description string   `json:"description,omitempty"`
	TrackIDs    []string `json:"track_ids,omitempty"`
}

// PlaylistStatus represents the status of a playlist.
type PlaylistStatus struct {
	PlaylistID    string     `json:"playlist_id"`
	CurrentTrack  string     `json:"current_track,omitempty"`
	NextTrack     string     `json:"next_track,omitempty"`
	TrackPosition int        `json:"track_position,omitempty"`
	IsPlaying     bool       `json:"is_playing"`
	UpdatedAt     time.Time  `json:"updated_at"`
}

// PlaylistReorderRequest represents a request to reorder playlist tracks.
type PlaylistReorderRequest struct {
	TrackIDs []string `json:"track_ids"`
}

// Webhook represents a webhook subscription.
type Webhook struct {
	ID             string     `json:"id"`
	URL            string     `json:"url"`
	EventTypes     []string   `json:"event_types"`
	Secret         string     `json:"secret,omitempty"`
	IsActive       bool       `json:"is_active"`
	LastSuccessAt  *time.Time `json:"last_success_at,omitempty"`
	LastFailureAt  *time.Time `json:"last_failure_at,omitempty"`
	FailureCount   int        `json:"failure_count"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
}

// WebhookCreateRequest represents a request to create a webhook.
type WebhookCreateRequest struct {
	URL        string   `json:"url"`
	EventTypes []string `json:"event_types"`
}

// WebhookUpdateRequest represents a request to update a webhook.
type WebhookUpdateRequest struct {
	URL        *string   `json:"url,omitempty"`
	EventTypes *[]string `json:"event_types,omitempty"`
	IsActive   *bool     `json:"is_active,omitempty"`
}

// WebhookTestResult represents the result of testing a webhook.
type WebhookTestResult struct {
	Success      bool   `json:"success"`
	StatusCode   int    `json:"status_code"`
	ResponseBody string `json:"response_body,omitempty"`
	Message      string `json:"message"`
}

// WebhookEvent represents a webhook event delivery attempt.
type WebhookEvent struct {
	ID                 string     `json:"id"`
	WebhookID          string     `json:"webhook_id"`
	EventType          string     `json:"event_type"`
	EventID            string     `json:"event_id"`
	Status             string     `json:"status"`
	AttemptNumber      int        `json:"attempt_number"`
	AttemptedAt        time.Time  `json:"attempted_at"`
	ResponseStatusCode int        `json:"response_status_code,omitempty"`
	ResponseBody       string     `json:"response_body,omitempty"`
	ResponseHeaders    map[string]string `json:"response_headers,omitempty"`
	ShouldRetry        bool       `json:"should_retry"`
	NextRetryAt        *time.Time `json:"next_retry_at,omitempty"`
	DurationMs         int        `json:"duration_ms,omitempty"`
}

// WebhookPayload represents a webhook event payload.
type WebhookPayload struct {
	EventType string                 `json:"event_type"`
	EventID   string                 `json:"event_id"`
	Timestamp string                 `json:"timestamp"`
	Data      map[string]interface{} `json:"data"`
}

// APIKey represents an API key.
type APIKey struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Key       string    `json:"key,omitempty"`
	Scopes    []string  `json:"scopes"`
	RateLimit *int      `json:"rate_limit,omitempty"`
	IsActive  bool      `json:"is_active"`
	ExpiresAt *time.Time `json:"expires_at,omitempty"`
	LastUsed  *time.Time `json:"last_used,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// APIKeyCreateRequest represents a request to create an API key.
type APIKeyCreateRequest struct {
	Name      string   `json:"name"`
	Scopes    []string `json:"scopes"`
	RateLimit *int     `json:"rate_limit,omitempty"`
	ExpiresAt *string  `json:"expires_at,omitempty"`
}

// APIKeyUpdateRequest represents a request to update an API key.
type APIKeyUpdateRequest struct {
	Name      *string   `json:"name,omitempty"`
	IsActive  *bool     `json:"is_active,omitempty"`
	ExpiresAt *string   `json:"expires_at,omitempty"`
}

// ListOptions represents options for listing resources.
type ListOptions struct {
	Limit  int    `json:"limit,omitempty"`
	Offset int    `json:"offset,omitempty"`
	Status string `json:"status,omitempty"`
}

// ListResponse represents a paginated list response.
type ListResponse struct {
	Total  int    `json:"total"`
	Limit  int    `json:"limit"`
	Offset int    `json:"offset"`
	Items  []json.RawMessage `json:"items"`
}

// Resource is an interface that all API resources must implement.
type Resource interface {
	// Base methods that all resources share
}

// StreamsResource provides methods to manage streams.
type StreamsResource interface {
	List(ctx context.Context, opts *ListOptions) ([]Stream, error)
	Get(ctx context.Context, streamID string) (*Stream, error)
	Start(ctx context.Context, channelID string) (*StreamStartResponse, error)
	Stop(ctx context.Context, streamID string) (*StreamStopResponse, error)
	Pause(ctx context.Context, streamID string) (*StreamStopResponse, error)
	Resume(ctx context.Context, streamID string) (*StreamStartResponse, error)
}

// ChannelsResource provides methods to manage channels.
type ChannelsResource interface {
	List(ctx context.Context, opts *ListOptions) ([]Channel, error)
	Get(ctx context.Context, channelID string) (*Channel, error)
	Create(ctx context.Context, req *ChannelCreateRequest) (*Channel, error)
	Update(ctx context.Context, channelID string, req *ChannelUpdateRequest) (*Channel, error)
	Delete(ctx context.Context, channelID string) error
}

// PlaylistsResource provides methods to manage playlists.
type PlaylistsResource interface {
	List(ctx context.Context, opts *ListOptions) ([]Playlist, error)
	Get(ctx context.Context, playlistID string) (*Playlist, error)
	Create(ctx context.Context, req *PlaylistCreateRequest) (*Playlist, error)
	Update(ctx context.Context, playlistID string, req *PlaylistUpdateRequest) (*Playlist, error)
	Delete(ctx context.Context, playlistID string) error
	GetStatus(ctx context.Context, playlistID string) (*PlaylistStatus, error)
	Reorder(ctx context.Context, playlistID string, req *PlaylistReorderRequest) error
}

// WebhooksResource provides methods to manage webhooks.
type WebhooksResource interface {
	List(ctx context.Context, opts *ListOptions) ([]Webhook, error)
	Get(ctx context.Context, webhookID string) (*Webhook, error)
	Create(ctx context.Context, req *WebhookCreateRequest) (*Webhook, error)
	Update(ctx context.Context, webhookID string, req *WebhookUpdateRequest) (*Webhook, error)
	Delete(ctx context.Context, webhookID string) error
	Test(ctx context.Context, webhookID string) (*WebhookTestResult, error)
	RotateSecret(ctx context.Context, webhookID string) (*Webhook, error)
	ListEvents(ctx context.Context, webhookID string, opts *ListOptions) ([]WebhookEvent, error)
}

// APIKeysResource provides methods to manage API keys.
type APIKeysResource interface {
	List(ctx context.Context) ([]APIKey, error)
	Get(ctx context.Context, keyID string) (*APIKey, error)
	Create(ctx context.Context, req *APIKeyCreateRequest) (*APIKey, error)
	Update(ctx context.Context, keyID string, req *APIKeyUpdateRequest) (*APIKey, error)
	Delete(ctx context.Context, keyID string) error
	Revoke(ctx context.Context, keyID string) error
}
