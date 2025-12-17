import { client } from './client';

export interface StreamMetrics {
  online: boolean;
  current_stream_url?: string | null;
  current_stream_name?: string | null;
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

// Feature 022 Phase 2: Stream Quality Types
export interface AudioQualityMetrics {
  codec?: string;
  bitrate_kbps?: number;
  sample_rate_hz?: number;
  channels?: number;
  duration_sec?: number;
  quality?: string;  // low, medium, high, lossless
}

export interface VideoQualityMetrics {
  codec?: string;
  bitrate_kbps?: number;
  resolution?: string;  // e.g. "1920x1080"
  fps?: number;
  duration_sec?: number;
  quality?: string;  // low, medium, high, ultra
}

export interface PerformanceMetrics {
  dropped_frames?: number;
  speed?: number;
  fps?: number;
  bitrate_kbps?: number;
}

export interface StreamQualityResponse {
  url: string;
  audio?: AudioQualityMetrics | null;
  video?: VideoQualityMetrics | null;
  performance?: PerformanceMetrics | null;
  is_audio_only: boolean;
  is_video_only: boolean;
  has_both: boolean;
  overall_quality: string;  // low, medium, high, lossless, ultra, unknown
}

// ========== Feature 022 Phase 3: Trends & Alerts ==========

export interface QualityHistoryPoint {
  timestamp: string;  // ISO 8601
  overall_quality: string;
  audio_quality?: string;
  audio_bitrate_kbps?: number;
  video_quality?: string;
  video_bitrate_kbps?: number;
  video_resolution?: string;
  video_fps?: number;
  success: boolean;
  error_message?: string;
}

export interface QualityTrendData {
  stream_url: string;
  stream_name?: string;
  history: QualityHistoryPoint[];
  average_quality: string;
  min_quality: string;
  max_quality: string;
  audio_avg_bitrate_kbps?: number;
  video_avg_bitrate_kbps?: number;
  video_avg_resolution?: string;
  success_rate: number;  // 0-1
  period_start: string;  // ISO 8601
  period_end: string;    // ISO 8601
  samples_count: number;
}

export interface QualityAlertConfigUpdate {
  stream_url: string;
  stream_name?: string;
  min_overall_quality?: string;
  min_audio_quality?: string;
  min_video_quality?: string;
  min_audio_bitrate_kbps?: number;
  min_video_bitrate_kbps?: number;
  min_video_resolution?: string;
  min_video_fps?: number;
  enabled?: boolean;
  notify_on_degradation?: boolean;
  notify_on_recovery?: boolean;
  consecutive_failures?: number;
  alert_channels?: Record<string, string[]>;
}

export interface QualityAlertConfigResponse extends QualityAlertConfigUpdate {
  id: number;
  last_alert_at?: string;
  last_alert_type?: string;
  consecutive_failures_count: number;
  created_at: string;
  updated_at: string;
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
  updateUserRole: async (id: string, role: string) => {
    const response = await client.put(`/api/admin/users/${id}/role`, { role });
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

  // Feature 022 Phase 2: Stream Quality Analysis
  getStreamQuality: async (streamUrl: string, timeout: number = 10, useCache: boolean = true): Promise<StreamQualityResponse | null> => {
    const response = await client.get('/api/admin/stream/quality/' + encodeURIComponent(streamUrl), {
      params: { timeout, use_cache: useCache }
    });
    return response.data;
  },

  batchAnalyzeStreams: async (urls: string[], timeout: number = 10): Promise<Record<string, StreamQualityResponse | null>> => {
    const response = await client.get('/api/admin/streams/quality/batch', {
      params: { urls, timeout }
    });
    return response.data;
  },

  clearQualityCache: async (streamUrl?: string) => {
    const response = await client.post('/api/admin/quality/cache/clear', null, {
      params: streamUrl ? { stream_url: streamUrl } : {}
    });
    return response.data;
  },

  // Feature 022 Phase 3: Trends & Alerts
  getQualityTrend: async (streamUrl: string, hours: number = 24): Promise<QualityTrendData> => {
    const response = await client.get(`/api/admin/stream/quality/trend/${encodeURIComponent(streamUrl)}`, {
      params: { hours }
    });
    return response.data;
  },

  setQualityAlertConfig: async (config: QualityAlertConfigUpdate): Promise<QualityAlertConfigResponse> => {
    const response = await client.post('/api/admin/stream/quality/alert/config', config);
    return response.data;
  },

  getQualityAlertConfig: async (streamUrl: string): Promise<QualityAlertConfigResponse | null> => {
    const response = await client.get(`/api/admin/stream/quality/alert/config/${encodeURIComponent(streamUrl)}`);
    return response.data;
  },
};
