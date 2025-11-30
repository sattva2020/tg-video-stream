import { client } from './client';

export interface StreamMetrics {
  online: boolean;
  metrics: {
    timestamp: number;
    system: {
      cpu_percent: number;
      memory_percent: number;
      memory_used: number;
      memory_total: number;
    };
    process: {
      cpu_percent: number;
      memory_rss: number;
      memory_vms: number;
    };
  } | null;
}

export interface CurrentTrack {
  id: string | null;
  title: string | null;
  url: string | null;
  duration: number | null;
  type: string | null;
}

export interface StreamStatus {
  online: boolean;
  status: 'running' | 'stopped' | 'error' | 'unknown';
  uptime_seconds: number;
  current_track: CurrentTrack | null;
  queue: {
    total: number;
    queued: number;
  };
  metrics: StreamMetrics['metrics'] | null;
  error?: string;
}

export interface User {
  id: string;
  email: string;
  status: string;
  role?: string;
  full_name?: string;
  created_at?: string;
}

export interface PaginatedUsersResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UsersListParams {
  status?: string;
  page?: number;
  page_size?: number;
  search?: string;
}

export const adminApi = {
  startStream: async () => {
    const response = await client.post('/api/admin/stream/start');
    return response.data;
  },
  stopStream: async () => {
    const response = await client.post('/api/admin/stream/stop');
    return response.data;
  },
  restartStream: async () => {
    const response = await client.post('/api/admin/stream/restart');
    return response.data;
  },
  getStreamStatus: async (): Promise<StreamStatus> => {
    const response = await client.get('/api/admin/stream/status');
    return response.data;
  },
  getLogs: async (lines: number = 100) => {
    const response = await client.get('/api/admin/stream/logs', { params: { lines } });
    return response.data;
  },
  getMetrics: async (): Promise<StreamMetrics> => {
    const response = await client.get('/api/admin/stream/metrics');
    return response.data;
  },
  listUsers: async (params?: UsersListParams): Promise<PaginatedUsersResponse> => {
    const response = await client.get('/api/admin/users', { params });
    return response.data;
  },
  approveUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/approve`);
    return response.data;
  },
  rejectUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/reject`);
    return response.data;
  },
  getPlaylist: async () => {
    const response = await client.get('/api/admin/playlist');
    return response.data;
  },
  updatePlaylist: async (items: string[]) => {
    const response = await client.post('/api/admin/playlist', { items });
    return response.data;
  },
};
