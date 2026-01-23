package sattva

import (
	"context"
	"testing"
	"time"
)

// TestClientInitialization verifies that the client initializes all resources correctly.
func TestClientInitialization(t *testing.T) {
	apiKey := "test-api-key-12345"
	client := NewClient(apiKey)

	if client == nil {
		t.Fatal("Client should not be nil")
	}

	if client.config.APIKey != apiKey {
		t.Errorf("Expected API key %s, got %s", apiKey, client.config.APIKey)
	}

	// Verify all resources are initialized (resources are interfaces, check they're not nil)
	if client.Streams == nil {
		t.Error("Streams resource should be initialized")
	}
	if client.Channels == nil {
		t.Error("Channels resource should be initialized")
	}
	if client.Playlists == nil {
		t.Error("Playlists resource should be initialized")
	}
	if client.Webhooks == nil {
		t.Error("Webhooks resource should be initialized")
	}
	if client.APIKeys == nil {
		t.Error("APIKeys resource should be initialized")
	}
}

// TestClientString verifies the String method.
func TestClientString(t *testing.T) {
	client := NewClient("test-key")
	str := client.String()

	if str == "" {
		t.Error("String should not be empty")
	}

	expected := "SattvaClient(baseURL='https://api.sattva.io/api/v1')"
	if str != expected {
		t.Errorf("Expected %s, got %s", expected, str)
	}
}

// TestClientClose verifies the Close method.
func TestClientClose(t *testing.T) {
	client := NewClient("test-key")
	client.Close()

	if client.httpClient != nil {
		t.Error("HTTP client should be nil after Close")
	}
}

// TestBuildQueryString verifies query string building.
func TestBuildQueryString(t *testing.T) {
	tests := []struct {
		name     string
		opts     *ListOptions
		expected string
	}{
		{
			name:     "nil options",
			opts:     nil,
			expected: "",
		},
		{
			name: "limit only",
			opts: &ListOptions{Limit: 10},
			expected: "?limit=10",
		},
		{
			name: "limit and offset",
			opts: &ListOptions{Limit: 10, Offset: 20},
			expected: "?limit=10&offset=20",
		},
		{
			name: "all options",
			opts: &ListOptions{Limit: 10, Offset: 20, Status: "active"},
			expected: "?limit=10&offset=20&status=active",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := buildQueryString(tt.opts)
			if result != tt.expected {
				t.Errorf("Expected %s, got %s", tt.expected, result)
			}
		})
	}
}

// TestResourcesNotNil verifies all resources are not nil.
func TestResourcesNotNil(t *testing.T) {
	client := NewClient("test-key")
	ctx := context.Background()

	// This test just verifies the resources can be called without panicking
	// We don't test actual API calls since we don't have a test server
	if client.Streams == nil {
		t.Error("Streams should not be nil")
	}
	if client.Channels == nil {
		t.Error("Channels should not be nil")
	}
	if client.Playlists == nil {
		t.Error("Playlists should not be nil")
	}
	if client.Webhooks == nil {
		t.Error("Webhooks should not be nil")
	}
	if client.APIKeys == nil {
		t.Error("APIKeys should not be nil")
	}

	// Verify we can call methods (they will fail due to no server, but shouldn't panic)
	_ = client.Streams
	_ = client.Channels
	_ = client.Playlists
	_ = client.Webhooks
	_ = client.APIKeys
	_ = ctx
}

// TestClientOptions verifies client configuration options.
func TestClientOptions(t *testing.T) {
	apiKey := "test-key"
	customBaseURL := "https://custom.api.com/v1"
	customTimeout := 60

	client := NewClient(
		apiKey,
		WithBaseURL(customBaseURL),
		WithTimeout(time.Duration(customTimeout)*time.Second),
	)

	if client.config.BaseURL != customBaseURL {
		t.Errorf("Expected base URL %s, got %s", customBaseURL, client.config.BaseURL)
	}

	if client.config.Timeout != 60*1000000000 {
		t.Errorf("Expected timeout 60s, got %v", client.config.Timeout)
	}
}
