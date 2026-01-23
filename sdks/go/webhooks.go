package sattva

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// webhooksResource implements the WebhooksResource interface.
type webhooksResource struct {
	client *Client
}

// newWebhooksResource creates a new webhooks resource.
func newWebhooksResource(client *Client) webhooksResource {
	return webhooksResource{client: client}
}

// List retrieves all webhook subscriptions with optional filtering.
func (r webhooksResource) List(ctx context.Context, opts *ListOptions) ([]Webhook, error) {
	log.Printf("[DEBUG] Listing webhooks with options: %+v", opts)

	path := "/webhooks/" + buildQueryString(opts)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list webhooks: %w", err)
	}

	var webhooks []Webhook
	if err := r.client.decodeJSON(data, &webhooks); err != nil {
		return nil, fmt.Errorf("failed to decode webhooks: %w", err)
	}

	return webhooks, nil
}

// Get retrieves a specific webhook by ID.
func (r webhooksResource) Get(ctx context.Context, webhookID string) (*Webhook, error) {
	log.Printf("[DEBUG] Getting webhook: %s", webhookID)

	path := fmt.Sprintf("/webhooks/%s/", webhookID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get webhook: %w", err)
	}

	var webhook Webhook
	if err := r.client.decodeJSON(data, &webhook); err != nil {
		return nil, fmt.Errorf("failed to decode webhook: %w", err)
	}

	return &webhook, nil
}

// Create creates a new webhook subscription.
func (r webhooksResource) Create(ctx context.Context, req *WebhookCreateRequest) (*Webhook, error) {
	log.Printf("[DEBUG] Creating webhook for URL: %s", req.URL)

	path := "/webhooks/"
	data, err := r.client.Post(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create webhook: %w", err)
	}

	var webhook Webhook
	if err := r.client.decodeJSON(data, &webhook); err != nil {
		return nil, fmt.Errorf("failed to decode webhook: %w", err)
	}

	return &webhook, nil
}

// Update updates an existing webhook subscription.
func (r webhooksResource) Update(ctx context.Context, webhookID string, req *WebhookUpdateRequest) (*Webhook, error) {
	log.Printf("[DEBUG] Updating webhook: %s", webhookID)

	path := fmt.Sprintf("/webhooks/%s/", webhookID)
	data, err := r.client.Patch(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to update webhook: %w", err)
	}

	var webhook Webhook
	if err := r.client.decodeJSON(data, &webhook); err != nil {
		return nil, fmt.Errorf("failed to decode webhook: %w", err)
	}

	return &webhook, nil
}

// Delete deletes a webhook subscription.
func (r webhooksResource) Delete(ctx context.Context, webhookID string) error {
	log.Printf("[DEBUG] Deleting webhook: %s", webhookID)

	path := fmt.Sprintf("/webhooks/%s/", webhookID)
	_, err := r.client.Delete(ctx, path)
	if err != nil {
		return fmt.Errorf("failed to delete webhook: %w", err)
	}

	return nil
}

// Test sends a test event to a webhook.
func (r webhooksResource) Test(ctx context.Context, webhookID string) (*WebhookTestResult, error) {
	log.Printf("[DEBUG] Testing webhook: %s", webhookID)

	path := fmt.Sprintf("/webhooks/%s/test/", webhookID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to test webhook: %w", err)
	}

	var result WebhookTestResult
	if err := r.client.decodeJSON(data, &result); err != nil {
		return nil, fmt.Errorf("failed to decode webhook test result: %w", err)
	}

	return &result, nil
}

// RotateSecret rotates the webhook secret and returns the new secret.
func (r webhooksResource) RotateSecret(ctx context.Context, webhookID string) (*Webhook, error) {
	log.Printf("[DEBUG] Rotating secret for webhook: %s", webhookID)

	path := fmt.Sprintf("/webhooks/%s/rotate-secret/", webhookID)
	data, err := r.client.Post(ctx, path, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to rotate webhook secret: %w", err)
	}

	var webhook Webhook
	if err := r.client.decodeJSON(data, &webhook); err != nil {
		return nil, fmt.Errorf("failed to decode webhook: %w", err)
	}

	return &webhook, nil
}

// ListEvents retrieves delivery events for a webhook.
func (r webhooksResource) ListEvents(ctx context.Context, webhookID string, opts *ListOptions) ([]WebhookEvent, error) {
	log.Printf("[DEBUG] Listing events for webhook: %s with options: %+v", webhookID, opts)

	path := fmt.Sprintf("/webhooks/%s/events/", webhookID) + buildQueryString(opts)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list webhook events: %w", err)
	}

	var events []WebhookEvent
	if err := r.client.decodeJSON(data, &events); err != nil {
		return nil, fmt.Errorf("failed to decode webhook events: %w", err)
	}

	return events, nil
}

// MarshalJSON implements custom JSON marshaling for webhooksResource.
func (r webhooksResource) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"client": r.client.String(),
	})
}
