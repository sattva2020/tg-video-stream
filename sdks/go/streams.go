package sattva

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// streamsResource implements the StreamsResource interface.
type streamsResource struct {
	client *Client
}

// newStreamsResource creates a new streams resource.
func newStreamsResource(client *Client) streamsResource {
	return streamsResource{client: client}
}

// List retrieves all streams with optional filtering.
func (r streamsResource) List(ctx context.Context, opts *ListOptions) ([]Stream, error) {
	log.Printf("[DEBUG] Listing streams with options: %+v", opts)

	path := "/streams/" + buildQueryString(opts)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list streams: %w", err)
	}

	var streams []Stream
	if err := r.client.decodeJSON(data, &streams); err != nil {
		return nil, fmt.Errorf("failed to decode streams: %w", err)
	}

	return streams, nil
}

// Get retrieves a specific stream by ID.
func (r streamsResource) Get(ctx context.Context, streamID string) (*Stream, error) {
	log.Printf("[DEBUG] Getting stream: %s", streamID)

	path := fmt.Sprintf("/streams/%s/", streamID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get stream: %w", err)
	}

	var stream Stream
	if err := r.client.decodeJSON(data, &stream); err != nil {
		return nil, fmt.Errorf("failed to decode stream: %w", err)
	}

	return &stream, nil
}

// Start starts a stream for a channel.
func (r streamsResource) Start(ctx context.Context, channelID string) (*StreamStartResponse, error) {
	log.Printf("[DEBUG] Starting stream for channel: %s", channelID)

	path := fmt.Sprintf("/channels/%s/start/", channelID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to start stream: %w", err)
	}

	var response StreamStartResponse
	if err := r.client.decodeJSON(data, &response); err != nil {
		return nil, fmt.Errorf("failed to decode stream start response: %w", err)
	}

	return &response, nil
}

// Stop stops a running stream.
func (r streamsResource) Stop(ctx context.Context, streamID string) (*StreamStopResponse, error) {
	log.Printf("[DEBUG] Stopping stream: %s", streamID)

	path := fmt.Sprintf("/streams/%s/stop/", streamID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to stop stream: %w", err)
	}

	var response StreamStopResponse
	if err := r.client.decodeJSON(data, &response); err != nil {
		return nil, fmt.Errorf("failed to decode stream stop response: %w", err)
	}

	return &response, nil
}

// Pause pauses a running stream.
func (r streamsResource) Pause(ctx context.Context, streamID string) (*StreamStopResponse, error) {
	log.Printf("[DEBUG] Pausing stream: %s", streamID)

	path := fmt.Sprintf("/streams/%s/pause/", streamID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to pause stream: %w", err)
	}

	var response StreamStopResponse
	if err := r.client.decodeJSON(data, &response); err != nil {
		return nil, fmt.Errorf("failed to decode stream pause response: %w", err)
	}

	return &response, nil
}

// Resume resumes a paused stream.
func (r streamsResource) Resume(ctx context.Context, streamID string) (*StreamStartResponse, error) {
	log.Printf("[DEBUG] Resuming stream: %s", streamID)

	path := fmt.Sprintf("/streams/%s/resume/", streamID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to resume stream: %w", err)
	}

	var response StreamStartResponse
	if err := r.client.decodeJSON(data, &response); err != nil {
		return nil, fmt.Errorf("failed to decode stream resume response: %w", err)
	}

	return &response, nil
}

// Restart restarts a stopped or failed stream.
func (r streamsResource) Restart(ctx context.Context, streamID string) (*StreamStartResponse, error) {
	log.Printf("[DEBUG] Restarting stream: %s", streamID)

	path := fmt.Sprintf("/streams/%s/restart/", streamID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to restart stream: %w", err)
	}

	var response StreamStartResponse
	if err := r.client.decodeJSON(data, &response); err != nil {
		return nil, fmt.Errorf("failed to decode stream restart response: %w", err)
	}

	return &response, nil
}

// MarshalJSON implements custom JSON marshaling for streamsResource.
func (r streamsResource) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"client": r.client.String(),
	})
}
