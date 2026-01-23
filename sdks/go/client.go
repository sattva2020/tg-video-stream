package sattva

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	// DefaultBaseURL is the default base URL for the Sattva API.
	DefaultBaseURL = "https://api.sattva.io/api/v1"
	// DefaultTimeout is the default request timeout.
	DefaultTimeout = 30 * time.Second
	// DefaultMaxRetries is the default number of retries for rate-limited requests.
	DefaultMaxRetries = 3
	// DefaultRetryDelay is the default delay between retries.
	DefaultRetryDelay = 1 * time.Second
	// UserAgent is the user agent header for the SDK.
	UserAgent = "SattvaGoSDK/0.1.0"
)

// APIError represents an error response from the API.
type APIError struct {
	Message  string                 `json:"message"`
	Detail   string                 `json:"detail,omitempty"`
	StatusCode int                    `json:"status_code,omitempty"`
	Response  map[string]interface{} `json:"response,omitempty"`
}

func (e *APIError) Error() string {
	if e.Detail != "" {
		return fmt.Sprintf("%s: %s", e.Message, e.Detail)
	}
	return e.Message
}

// Error types.
var (
	ErrAuthenticationRequired = &APIError{Message: "Authentication required"}
	ErrUnauthorized           = &APIError{Message: "Unauthorized access"}
	ErrRateLimitExceeded      = &APIError{Message: "Rate limit exceeded"}
	ErrNotFound               = &APIError{Message: "Resource not found"}
	ErrValidationError        = &APIError{Message: "Validation failed"}
)

// AuthenticationError is returned when authentication fails.
type AuthenticationError struct {
	*APIError
}

func (e *AuthenticationError) Error() string {
	return fmt.Sprintf("authentication error: %s", e.APIError.Error())
}

// RateLimitError is returned when rate limit is exceeded.
type RateLimitError struct {
	*APIError
	RetryAfter *time.Duration
}

func (e *RateLimitError) Error() string {
	msg := fmt.Sprintf("rate limit error: %s", e.APIError.Error())
	if e.RetryAfter != nil {
		msg = fmt.Sprintf("%s (retry after: %v)", msg, *e.RetryAfter)
	}
	return msg
}

// NotFoundError is returned when a resource is not found.
type NotFoundError struct {
	*APIError
}

func (e *NotFoundError) Error() string {
	return fmt.Sprintf("not found error: %s", e.APIError.Error())
}

// ValidationError is returned when request validation fails.
type ValidationError struct {
	*APIError
	Errors map[string]interface{} `json:"errors,omitempty"`
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("validation error: %s", e.APIError.Error())
}

// Client is the Sattva API client.
type Client struct {
	config     ClientConfig
	httpClient *http.Client

	// API resources
	Streams  StreamsResource
	Channels ChannelsResource
	Playlists PlaylistsResource
	Webhooks WebhooksResource
	APIKeys  APIKeysResource
}

// NewClient creates a new Sattva API client.
func NewClient(apiKey string, opts ...ClientOption) *Client {
	if apiKey == "" {
		panic("api key is required")
	}

	config := ClientConfig{
		APIKey:     apiKey,
		BaseURL:    DefaultBaseURL,
		Timeout:    DefaultTimeout,
		MaxRetries: DefaultMaxRetries,
		RetryDelay: DefaultRetryDelay,
	}

	for _, opt := range opts {
		opt(&config)
	}

	client := &Client{
		config: config,
		httpClient: &http.Client{
			Timeout: config.Timeout,
		},
	}

	// Initialize resources (will be implemented in subtask 7-3)
	// client.Streams = newStreamsResource(client)
	// client.Channels = newChannelsResource(client)
	// client.Playlists = newPlaylistsResource(client)
	// client.Webhooks = newWebhooksResource(client)
	// client.APIKeys = newAPIKeysResource(client)

	return client
}

// String returns a string representation of the client.
func (c *Client) String() string {
	return fmt.Sprintf("SattvaClient(baseURL='%s')", c.config.BaseURL)
}

// Close closes the HTTP client and releases resources.
func (c *Client) Close() {
	if c.httpClient != nil {
		c.httpClient.CloseIdleConnections()
		c.httpClient = nil
	}
}

// doRequest performs an HTTP request with retry logic for rate limiting.
func (c *Client) doRequest(ctx context.Context, method, path string, body interface{}, retries int) ([]byte, error) {
	// Build the full URL
	fullURL, err := url.JoinPath(c.config.BaseURL, path)
	if err != nil {
		return nil, fmt.Errorf("failed to build URL: %w", err)
	}

	// Marshal request body if present
	var reqBody io.Reader
	if body != nil {
		jsonData, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		reqBody = bytes.NewReader(jsonData)
	}

	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, method, fullURL, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("X-API-Key", c.config.APIKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", UserAgent)

	// Perform request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		// Check for context cancellation
		if ctx.Err() != nil {
			return nil, fmt.Errorf("request cancelled: %w", ctx.Err())
		}
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	// Handle rate limiting with automatic retry
	if resp.StatusCode == http.StatusTooManyRequests && retries < c.config.MaxRetries {
		retryAfter := c.parseRetryAfter(resp.Header.Get("Retry-After"))
		if retryAfter == 0 {
			retryAfter = c.config.RetryDelay
		}

		log.Printf("[WARN] Rate limited. Retrying in %v (attempt %d/%d)", retryAfter, retries+1, c.config.MaxRetries)

		// Wait before retrying
		select {
		case <-time.After(retryAfter):
		case <-ctx.Done():
			return nil, fmt.Errorf("request cancelled during retry wait: %w", ctx.Err())
		}

		// Retry the request
		return c.doRequest(ctx, method, path, body, retries+1)
	}

	// Handle error responses
	if resp.StatusCode >= 400 {
		return respBody, c.handleError(resp.StatusCode, respBody)
	}

	return respBody, nil
}

// parseRetryAfter parses the Retry-After header.
func (c *Client) parseRetryAfter(retryAfter string) time.Duration {
	if retryAfter == "" {
		return 0
	}

	// Try to parse as integer seconds
	var seconds int
	if _, err := fmt.Sscanf(retryAfter, "%d", &seconds); err == nil {
		return time.Duration(seconds) * time.Second
	}

	// Try to parse as HTTP date
	if t, err := http.ParseTime(retryAfter); err == nil {
		return time.Until(t)
	}

	return 0
}

// handleError handles API error responses and returns appropriate error types.
func (c *Client) handleError(statusCode int, body []byte) error {
	var apiErr APIError
	if err := json.Unmarshal(body, &apiErr); err != nil {
		// If we can't parse the error body, create a generic error
		apiErr = APIError{
			Message:   string(body),
			StatusCode: statusCode,
		}
	} else {
		apiErr.StatusCode = statusCode
	}

	switch statusCode {
	case http.StatusUnauthorized, http.StatusForbidden:
		return &AuthenticationError{APIError: &apiErr}
	case http.StatusNotFound:
		return &NotFoundError{APIError: &apiErr}
	case http.StatusTooManyRequests:
		return &RateLimitError{APIError: &apiErr}
	case http.StatusBadRequest, http.StatusUnprocessableEntity:
		return &ValidationError{APIError: &apiErr}
	default:
		return &apiErr
	}
}

// Get performs a GET request.
func (c *Client) Get(ctx context.Context, path string) ([]byte, error) {
	return c.doRequest(ctx, http.MethodGet, path, nil, 0)
}

// Post performs a POST request.
func (c *Client) Post(ctx context.Context, path string, body interface{}) ([]byte, error) {
	return c.doRequest(ctx, http.MethodPost, path, body, 0)
}

// Patch performs a PATCH request.
func (c *Client) Patch(ctx context.Context, path string, body interface{}) ([]byte, error) {
	return c.doRequest(ctx, http.MethodPatch, path, body, 0)
}

// Delete performs a DELETE request.
func (c *Client) Delete(ctx context.Context, path string) ([]byte, error) {
	return c.doRequest(ctx, http.MethodDelete, path, nil, 0)
}

// Put performs a PUT request.
func (c *Client) Put(ctx context.Context, path string, body interface{}) ([]byte, error) {
	return c.doRequest(ctx, http.MethodPut, path, body, 0)
}

// decodeJSON decodes JSON response into a target value.
func (c *Client) decodeJSON(data []byte, v interface{}) error {
	if err := json.Unmarshal(data, v); err != nil {
		return fmt.Errorf("failed to decode JSON response: %w", err)
	}
	return nil
}

// buildQueryString builds a query string from list options.
func buildQueryString(opts *ListOptions) string {
	if opts == nil {
		return ""
	}

	var params []string
	if opts.Limit > 0 {
		params = append(params, fmt.Sprintf("limit=%d", opts.Limit))
	}
	if opts.Offset > 0 {
		params = append(params, fmt.Sprintf("offset=%d", opts.Offset))
	}
	if opts.Status != "" {
		params = append(params, fmt.Sprintf("status=%s", opts.Status))
	}

	if len(params) == 0 {
		return ""
	}
	return "?" + strings.Join(params, "&")
}
