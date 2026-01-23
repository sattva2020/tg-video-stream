package sattva

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// playlistsResource implements the PlaylistsResource interface.
type playlistsResource struct {
	client *Client
}

// newPlaylistsResource creates a new playlists resource.
func newPlaylistsResource(client *Client) playlistsResource {
	return playlistsResource{client: client}
}

// List retrieves all playlists with optional filtering.
func (r playlistsResource) List(ctx context.Context, opts *ListOptions) ([]Playlist, error) {
	log.Printf("[DEBUG] Listing playlists with options: %+v", opts)

	path := "/playlists/" + buildQueryString(opts)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to list playlists: %w", err)
	}

	var playlists []Playlist
	if err := r.client.decodeJSON(data, &playlists); err != nil {
		return nil, fmt.Errorf("failed to decode playlists: %w", err)
	}

	return playlists, nil
}

// Get retrieves a specific playlist by ID.
func (r playlistsResource) Get(ctx context.Context, playlistID string) (*Playlist, error) {
	log.Printf("[DEBUG] Getting playlist: %s", playlistID)

	path := fmt.Sprintf("/playlists/%s/", playlistID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get playlist: %w", err)
	}

	var playlist Playlist
	if err := r.client.decodeJSON(data, &playlist); err != nil {
		return nil, fmt.Errorf("failed to decode playlist: %w", err)
	}

	return &playlist, nil
}

// Create creates a new playlist.
func (r playlistsResource) Create(ctx context.Context, req *PlaylistCreateRequest) (*Playlist, error) {
	log.Printf("[DEBUG] Creating playlist: %s", req.Name)

	path := "/playlists/"
	data, err := r.client.Post(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create playlist: %w", err)
	}

	var playlist Playlist
	if err := r.client.decodeJSON(data, &playlist); err != nil {
		return nil, fmt.Errorf("failed to decode playlist: %w", err)
	}

	return &playlist, nil
}

// Update updates an existing playlist.
func (r playlistsResource) Update(ctx context.Context, playlistID string, req *PlaylistUpdateRequest) (*Playlist, error) {
	log.Printf("[DEBUG] Updating playlist: %s", playlistID)

	path := fmt.Sprintf("/playlists/%s/", playlistID)
	data, err := r.client.Patch(ctx, path, req)
	if err != nil {
		return nil, fmt.Errorf("failed to update playlist: %w", err)
	}

	var playlist Playlist
	if err := r.client.decodeJSON(data, &playlist); err != nil {
		return nil, fmt.Errorf("failed to decode playlist: %w", err)
	}

	return &playlist, nil
}

// Delete deletes a playlist.
func (r playlistsResource) Delete(ctx context.Context, playlistID string) error {
	log.Printf("[DEBUG] Deleting playlist: %s", playlistID)

	path := fmt.Sprintf("/playlists/%s/", playlistID)
	_, err := r.client.Delete(ctx, path)
	if err != nil {
		return fmt.Errorf("failed to delete playlist: %w", err)
	}

	return nil
}

// GetStatus retrieves the current status of a playlist.
func (r playlistsResource) GetStatus(ctx context.Context, playlistID string) (*PlaylistStatus, error) {
	log.Printf("[DEBUG] Getting status for playlist: %s", playlistID)

	path := fmt.Sprintf("/playlists/%s/status/", playlistID)
	data, err := r.client.Get(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to get playlist status: %w", err)
	}

	var status PlaylistStatus
	if err := r.client.decodeJSON(data, &status); err != nil {
		return nil, fmt.Errorf("failed to decode playlist status: %w", err)
	}

	return &status, nil
}

// Reorder reorders the tracks in a playlist.
func (r playlistsResource) Reorder(ctx context.Context, playlistID string, req *PlaylistReorderRequest) error {
	log.Printf("[DEBUG] Reordering tracks in playlist: %s", playlistID)

	path := fmt.Sprintf("/playlists/%s/reorder/", playlistID)
	_, err := r.client.Post(ctx, path, req)
	if err != nil {
		return fmt.Errorf("failed to reorder playlist: %w", err)
	}

	return nil
}

// MarshalJSON implements custom JSON marshaling for playlistsResource.
func (r playlistsResource) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"client": r.client.String(),
	})
}
