import { client } from './client';

export interface PlaylistEntry {
  url: string;
  title: string;
  duration: number;
  type: string;
  file_id?: string;
}

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
  items?: PlaylistEntry[];
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
};
