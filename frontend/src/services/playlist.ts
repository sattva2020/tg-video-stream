export interface PlaylistItem {
  id: string;
  url: string;
  title?: string;
  type: string;
  position: number;
  created_at: string;
  status: string;
  duration?: number | null;
}

const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function request(path: string, opts?: RequestInit) {
  const url = `${API_BASE}/api/playlist${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: {
      ...getAuthHeaders(),
      ...opts?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function getPlaylist(channelId?: string): Promise<PlaylistItem[]> {
  const q = channelId ? `?channel_id=${encodeURIComponent(channelId)}` : '';
  return request(`/${q}`);
}

export async function addPlaylistItem(payload: { url: string; title?: string; type?: string; duration?: number }): Promise<PlaylistItem> {
  return request('/', { 
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' }, 
    body: JSON.stringify(payload) 
  });
}

export async function deletePlaylistItem(id: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/api/playlist/${id}`, { 
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Delete failed ${res.status}`);
  return true;
}

// Aliases для обратной совместимости
export const addTrack = addPlaylistItem;
export const deleteTrack = deletePlaylistItem;

export default { getPlaylist, addPlaylistItem, deletePlaylistItem, addTrack, deleteTrack };
