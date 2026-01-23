package sattva

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// apiKeysResource implements the APIKeysResource interface.
type apiKeysResource struct {
	client *Client
}

// newAPIKeysResource creates a new API keys resource.
func newAPIKeysResource(client *Client) apiKeysResource {
	return apiKeysResource{client: client}
}

// List retrieves all API keys for the authenticated user.
func (r apiKeysResource) List(ctx context.Context) ([]APIKey, error) {
	log.Printf("[DEBUG] Listing API keys")

	path := "/keys/"
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list API keys: %w", err)
	}

	var keys []APIKey
	if err := r.client.decodeJSON(data, &keys); err != nil {
		return nil, fmt.Errorf("failed to decode API keys: %w", err)
	}

	return keys, nil
}

// Get retrieves a specific API key by ID.
func (r apiKeysResource) Get(ctx context.Context, keyID string) (*APIKey, error) {
	log.Printf("[DEBUG] Getting API key: %s", keyID)

	path := fmt.Sprintf("/keys/%s/", keyID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get API key: %w", err)
	}

	var key APIKey
	if err := r.client.decodeJSON(data, &key); err != nil {
		return nil, fmt.Errorf("failed to decode API key: %w", err)
	}

	return &key, nil
}

// Create creates a new API key.
func (r apiKeysResource) Create(ctx context.Context, req *APIKeyCreateRequest) (*APIKey, error) {
	log.Printf("[DEBUG] Creating API key: %s", req.Name)

	path := "/keys/"
	data, err := r.client.Post(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create API key: %w", err)
	}

	var key APIKey
	if err := r.client.decodeJSON(data, &key); err != nil {
		return nil, fmt.Errorf("failed to decode API key: %w", err)
	}

	return &key, nil
}

// Update updates an existing API key.
func (r apiKeysResource) Update(ctx context.Context, keyID string, req *APIKeyUpdateRequest) (*APIKey, error) {
	log.Printf("[DEBUG] Updating API key: %s", keyID)

	path := fmt.Sprintf("/keys/%s/", keyID)
	data, err := r.client.Patch(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to update API key: %w", err)
	}

	var key APIKey
	if err := r.client.decodeJSON(data, &key); err != nil {
		return nil, fmt.Errorf("failed to decode API key: %w", err)
	}

	return &key, nil
}

// Delete permanently deletes an API key.
func (r apiKeysResource) Delete(ctx context.Context, keyID string) error {
	log.Printf("[DEBUG] Deleting API key: %s", keyID)

	path := fmt.Sprintf("/keys/%s/", keyID)
	_, err := r.client.Delete(ctx, path)
	if err != nil {
		return fmt.Errorf("failed to delete API key: %w", err)
	}

	return nil
}

// Revoke revokes an API key (soft delete).
func (r apiKeysResource) Revoke(ctx context.Context, keyID string) error {
	log.Printf("[DEBUG] Revoking API key: %s", keyID)

	path := fmt.Sprintf("/keys/%s/revoke/", keyID)
	_, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return fmt.Errorf("failed to revoke API key: %w", err)
	}

	return nil
}

// MarshalJSON implements custom JSON marshaling for apiKeysResource.
func (r apiKeysResource) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"client": r.client.String(),
	})
}
