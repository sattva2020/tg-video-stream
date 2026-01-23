import { client } from './client';

export interface PlaylistEntry {
  url: string;
  title: string;
  duration: number;
  type: string;
  file_id?: string;
  thumbnail?: string;
}

export type RepeatMode = 'none' | 'one' | 'all';

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
  repeat_mode?: RepeatMode;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  share_code?: string;
  created_at: string;
  updated_at?: string;
}

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

export interface PlaylistUpdate {
  name?: string;
  description?: string;
  is_public?: boolean;
  color?: string;
  icon?: string;
  source_type?: string;
  source_url?: string;
  repeat_mode?: RepeatMode;
  items?: PlaylistEntry[];
}

export interface PlaylistTemplate {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_public: boolean;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  created_at: string;
  updated_at?: string;
}

export interface PlaylistTemplateCreate {
  name: string;
  description?: string;
  is_public?: boolean;
  items?: PlaylistEntry[];
}

export interface PlaylistTemplateUpdate {
  name?: string;
  description?: string;
  is_public?: boolean;
  items?: PlaylistEntry[];
}

export interface SmartPlaylistCriteria {
  filters?: {
    duration_min?: number;
    duration_max?: number;
    type?: string;
    tags?: string[];
    source?: string;
  };
  order_by?: 'date_added' | 'duration' | 'name' | 'source';
  order_direction?: 'asc' | 'desc';
  limit?: number;
  shuffle?: boolean;
}

export interface SmartPlaylist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_public: boolean;
  criteria: SmartPlaylistCriteria;
  auto_update: boolean;
  auto_update_interval: number;
  group_id?: string;
  items_count: number;
  total_duration: number;
  playlist_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface SmartPlaylistCreate {
  name: string;
  description?: string;
  is_public?: boolean;
  criteria: SmartPlaylistCriteria;
  auto_update?: boolean;
  auto_update_interval?: number;
  group_id?: string;
}

export interface SmartPlaylistUpdate {
  name?: string;
  description?: string;
  is_public?: boolean;
  criteria?: SmartPlaylistCriteria;
  auto_update?: boolean;
  auto_update_interval?: number;
  group_id?: string;
}

const PLAYLISTS_BASE = '/api/playlists';

export const playlistsApi = {
  getMyPlaylists: async (skip = 0, limit = 100) => {
    const response = await client.get<Playlist[]>(`${PLAYLISTS_BASE}/`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getPublicPlaylists: async (skip = 0, limit = 100) => {
    const response = await client.get<Playlist[]>(`${PLAYLISTS_BASE}/public`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getPlaylist: async (id: string) => {
    const response = await client.get<Playlist>(`${PLAYLISTS_BASE}/${id}`);
    return response.data;
  },

  createPlaylist: async (data: PlaylistCreate) => {
    const response = await client.post<Playlist>(`${PLAYLISTS_BASE}/`, data);
    return response.data;
  },

  updatePlaylist: async (id: string, data: PlaylistUpdate) => {
    const response = await client.put<Playlist>(`${PLAYLISTS_BASE}/${id}`, data);
    return response.data;
  },

  deletePlaylist: async (id: string) => {
    await client.delete(`${PLAYLISTS_BASE}/${id}`);
  },

  clonePlaylist: async (id: string) => {
    const response = await client.post<Playlist>(`${PLAYLISTS_BASE}/${id}/clone`);
    return response.data;
  },

  playPlaylist: async (id: string, channelId?: string) => {
    const response = await client.post<{ status: string; channel_id: string; slot_id: string }>(
      `${PLAYLISTS_BASE}/${id}/play`,
      null,
      { params: { channel_id: channelId } }
    );
    return response.data;
  },

  exportPlaylist: async (id: string, name: string) => {
    const response = await client.get(`${PLAYLISTS_BASE}/${id}/export/m3u`, {
      responseType: 'blob',
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${name.replace(/\s+/g, '_')}.m3u`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  importPlaylist: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post<Playlist>(`${PLAYLISTS_BASE}/import/m3u`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Template methods
  getMyTemplates: async (skip = 0, limit = 100) => {
    const response = await client.get<PlaylistTemplate[]>(`${PLAYLISTS_BASE}/templates`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getPublicTemplates: async (skip = 0, limit = 100) => {
    const response = await client.get<PlaylistTemplate[]>(`${PLAYLISTS_BASE}/templates/public`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getTemplate: async (templateId: string) => {
    const response = await client.get<PlaylistTemplate>(`${PLAYLISTS_BASE}/templates/${templateId}`);
    return response.data;
  },

  createTemplate: async (data: PlaylistTemplateCreate) => {
    const response = await client.post<PlaylistTemplate>(`${PLAYLISTS_BASE}/templates`, data);
    return response.data;
  },

  updateTemplate: async (templateId: string, data: PlaylistTemplateUpdate) => {
    const response = await client.put<PlaylistTemplate>(`${PLAYLISTS_BASE}/templates/${templateId}`, data);
    return response.data;
  },

  deleteTemplate: async (templateId: string) => {
    await client.delete(`${PLAYLISTS_BASE}/templates/${templateId}`);
  },

  applyTemplate: async (templateId: string, playlistName: string) => {
    const response = await client.post<Playlist>(`${PLAYLISTS_BASE}/templates/${templateId}/apply`, {
      name: playlistName,
    });
    return response.data;
  },

  cloneTemplate: async (templateId: string) => {
    const response = await client.post<PlaylistTemplate>(`${PLAYLISTS_BASE}/templates/${templateId}/clone`);
    return response.data;
  },

  // Smart playlist methods
  getMySmartPlaylists: async (skip = 0, limit = 100) => {
    const response = await client.get<SmartPlaylist[]>(`${PLAYLISTS_BASE}/smart`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getPublicSmartPlaylists: async (skip = 0, limit = 100) => {
    const response = await client.get<SmartPlaylist[]>(`${PLAYLISTS_BASE}/smart/public`, {
      params: { skip, limit },
    });
    return response.data;
  },

  getSmartPlaylist: async (smartPlaylistId: string) => {
    const response = await client.get<SmartPlaylist>(`${PLAYLISTS_BASE}/smart/${smartPlaylistId}`);
    return response.data;
  },

  createSmartPlaylist: async (data: SmartPlaylistCreate) => {
    const response = await client.post<SmartPlaylist>(`${PLAYLISTS_BASE}/smart`, data);
    return response.data;
  },

  updateSmartPlaylist: async (smartPlaylistId: string, data: SmartPlaylistUpdate) => {
    const response = await client.put<SmartPlaylist>(`${PLAYLISTS_BASE}/smart/${smartPlaylistId}`, data);
    return response.data;
  },

  deleteSmartPlaylist: async (smartPlaylistId: string) => {
    await client.delete(`${PLAYLISTS_BASE}/smart/${smartPlaylistId}`);
  },

  refreshSmartPlaylist: async (smartPlaylistId: string) => {
    const response = await client.post<Playlist>(`${PLAYLISTS_BASE}/smart/${smartPlaylistId}/refresh`);
    return response.data;
  },

  cloneSmartPlaylist: async (smartPlaylistId: string) => {
    const response = await client.post<SmartPlaylist>(`${PLAYLISTS_BASE}/smart/${smartPlaylistId}/clone`);
    return response.data;
  },
};
