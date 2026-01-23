/**
 * Playlists API
 *
 * API endpoints for managing playlists.
 * Follows patterns from frontend/src/api/playlists.ts
 */

import { client } from './client';

/**
 * Playlist entry (track)
 */
export interface PlaylistEntry {
  url: string;
  title: string;
  duration: number;
  type: string;
  file_id?: string;
}

/**
 * Playlist interface
 */
export interface Playlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_public: boolean;
  color: string;
  icon: string;
  source_type?: string;
  source_url?: string;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  share_code?: string;
  created_at: string;
  updated_at?: string;
}

/**
 * Data for creating a new playlist
 */
export interface PlaylistCreate {
  name: string;
  description?: string;
  is_public?: boolean;
  color?: string;
  icon?: string;
  source_type?: string;
  source_url?: string;
  items?: PlaylistEntry[];
}

/**
 * Data for updating a playlist
 */
export interface PlaylistUpdate {
  name?: string;
  description?: string;
  is_public?: boolean;
  color?: string;
  icon?: string;
  source_type?: string;
  source_url?: string;
  items?: PlaylistEntry[];
}

/**
 * Response for playlist play operation
 */
export interface PlaylistPlayResponse {
  status: string;
  channel_id: string;
  slot_id: string;
}

/**
 * Playlists API endpoints
 */
export const playlistsApi = {
  /**
   * Get user's playlists
   */
  getMyPlaylists: async (skip = 0, limit = 100): Promise<Playlist[]> => {
    const response = await client.get<Playlist[]>('/api/playlists/', {
      params: { skip, limit },
    });
    return response.data;
  },

  /**
   * Get public playlists
   */
  getPublicPlaylists: async (skip = 0, limit = 100): Promise<Playlist[]> => {
    const response = await client.get<Playlist[]>('/api/playlists/public', {
      params: { skip, limit },
    });
    return response.data;
  },

  /**
   * Get a single playlist by ID
   */
  getPlaylist: async (id: string): Promise<Playlist> => {
    const response = await client.get<Playlist>(`/api/playlists/${id}`);
    return response.data;
  },

  /**
   * Create a new playlist
   */
  createPlaylist: async (data: PlaylistCreate): Promise<Playlist> => {
    const response = await client.post<Playlist>('/api/playlists/', data);
    return response.data;
  },

  /**
   * Update an existing playlist
   */
  updatePlaylist: async (id: string, data: PlaylistUpdate): Promise<Playlist> => {
    const response = await client.put<Playlist>(`/api/playlists/${id}`, data);
    return response.data;
  },

  /**
   * Delete a playlist
   */
  deletePlaylist: async (id: string): Promise<{ status: string }> => {
    const response = await client.delete<{ status: string }>(`/api/playlists/${id}`);
    return response.data;
  },

  /**
   * Clone a playlist
   */
  clonePlaylist: async (id: string): Promise<Playlist> => {
    const response = await client.post<Playlist>(`/api/playlists/${id}/clone`);
    return response.data;
  },

  /**
   * Play a playlist on a channel
   */
  playPlaylist: async (id: string, channelId?: string): Promise<PlaylistPlayResponse> => {
    const response = await client.post<PlaylistPlayResponse>(
      `/api/playlists/${id}/play`,
      null,
      { params: { channel_id: channelId } }
    );
    return response.data;
  },

  /**
   * Import playlist from M3U file
   * Note: On mobile, file upload requires expo-document-picker
   */
  importPlaylist: async (file: File): Promise<Playlist> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post<Playlist>('/api/playlists/import/m3u', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
