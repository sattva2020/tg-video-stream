package sattva

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// channelsResource implements the ChannelsResource interface.
type channelsResource struct {
	client *Client
}

// newChannelsResource creates a new channels resource.
func newChannelsResource(client *Client) channelsResource {
	return channelsResource{client: client}
}

// List retrieves all channels with optional filtering.
func (r channelsResource) List(ctx context.Context, opts *ListOptions) ([]Channel, error) {
	log.Printf("[DEBUG] Listing channels with options: %+v", opts)

	path := "/channels/" + buildQueryString(opts)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list channels: %w", err)
	}

	var channels []Channel
	if err := r.client.decodeJSON(data, &channels); err != nil {
		return nil, fmt.Errorf("failed to decode channels: %w", err)
	}

	return channels, nil
}

// Get retrieves a specific channel by ID.
func (r channelsResource) Get(ctx context.Context, channelID string) (*Channel, error) {
	log.Printf("[DEBUG] Getting channel: %s", channelID)

	path := fmt.Sprintf("/channels/%s/", channelID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get channel: %w", err)
	}

	var channel Channel
	if err := r.client.decodeJSON(data, &channel); err != nil {
		return nil, fmt.Errorf("failed to decode channel: %w", err)
	}

	return &channel, nil
}

// Create creates a new channel.
func (r channelsResource) Create(ctx context.Context, req *ChannelCreateRequest) (*Channel, error) {
	log.Printf("[DEBUG] Creating channel: %s", req.Name)

	path := "/channels/"
	data, err := r.client.Post(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create channel: %w", err)
	}

	var channel Channel
	if err := r.client.decodeJSON(data, &channel); err != nil {
		return nil, fmt.Errorf("failed to decode channel: %w", err)
	}

	return &channel, nil
}

// Update updates an existing channel.
func (r channelsResource) Update(ctx context.Context, channelID string, req *ChannelUpdateRequest) (*Channel, error) {
	log.Printf("[DEBUG] Updating channel: %s", channelID)

	path := fmt.Sprintf("/channels/%s/", channelID)
	data, err := r.client.Patch(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to update channel: %w", err)
	}

	var channel Channel
	if err := r.client.decodeJSON(data, &channel); err != nil {
		return nil, fmt.Errorf("failed to decode channel: %w", err)
	}

	return &channel, nil
}

// Delete deletes a channel.
func (r channelsResource) Delete(ctx context.Context, channelID string) error {
	log.Printf("[DEBUG] Deleting channel: %s", channelID)

	path := fmt.Sprintf("/channels/%s/", channelID)
	_, err := r.client.Delete(ctx, path)
	if err != nil {
		return fmt.Errorf("failed to delete channel: %w", err)
	}

	return nil
}

// MarshalJSON implements custom JSON marshaling for channelsResource.
func (r channelsResource) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"client": r.client.String(),
	})
}
