import { client } from './client';

export type PlatformType = 'youtube' | 'twitch' | 'twitter' | 'discord' | 'custom_rtmp';
export type PlatformStatus = 'inactive' | 'active' | 'error';
export type DestinationStatus = 'idle' | 'streaming' | 'error';

export interface StreamingPlatform {
  id: string;
  user_id: string;
  platform_type: PlatformType;
  platform_name: string;
  status: PlatformStatus;
  last_error?: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateStreamingPlatformData {
  platform_type: PlatformType;
  platform_name: string;
  stream_key?: string;
  stream_url?: string;
  encrypted_credentials?: string;
}

export interface UpdateStreamingPlatformData {
  platform_name?: string;
  stream_key?: string;
  stream_url?: string;
  encrypted_credentials?: string;
  status?: PlatformStatus;
}

export interface BroadcastDestination {
  id: string;
  channel_id: string;
  platform_id: string;
  enabled: boolean;
  status: DestinationStatus;
  last_error?: string;
  platform_settings?: Record<string, unknown>;
  custom_title?: string;
  custom_description?: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateBroadcastDestinationData {
  channel_id: string;
  platform_id: string;
  enabled?: boolean;
  platform_settings?: Record<string, unknown>;
  custom_title?: string;
  custom_description?: string;
}

export interface UpdateBroadcastDestinationData {
  enabled?: boolean;
  platform_settings?: Record<string, unknown>;
  custom_title?: string;
  custom_description?: string;
}

export const streamingPlatformsApi = {
  // Streaming Platform operations
  listPlatforms: async () => {
    const response = await client.get<{ platforms: StreamingPlatform[]; total: number }>('/api/streaming-platforms/');
    return response.data;
  },

  createPlatform: async (data: CreateStreamingPlatformData) => {
    const response = await client.post<StreamingPlatform>('/api/streaming-platforms/', data);
    return response.data;
  },

  getPlatform: async (platformId: string) => {
    const response = await client.get<StreamingPlatform>(`/api/streaming-platforms/${platformId}`);
    return response.data;
  },

  updatePlatform: async (platformId: string, data: UpdateStreamingPlatformData) => {
    const response = await client.put<StreamingPlatform>(`/api/streaming-platforms/${platformId}`, data);
    return response.data;
  },

  deletePlatform: async (platformId: string) => {
    const response = await client.delete<{ status: string }>(`/api/streaming-platforms/${platformId}`);
    return response.data;
  },

  testPlatform: async (platformId: string) => {
    const response = await client.post<{ status: string; message?: string }>(`/api/streaming-platforms/${platformId}/test`);
    return response.data;
  },

  // Broadcast Destination operations
  listDestinations: async (channelId?: string) => {
    const params = channelId ? { channel_id: channelId } : {};
    const response = await client.get<{ destinations: BroadcastDestination[]; total: number }>('/api/broadcast-destinations/', { params });
    return response.data;
  },

  createDestination: async (data: CreateBroadcastDestinationData) => {
    const response = await client.post<BroadcastDestination>('/api/broadcast-destinations/', data);
    return response.data;
  },

  getDestination: async (destinationId: string) => {
    const response = await client.get<BroadcastDestination>(`/api/broadcast-destinations/${destinationId}`);
    return response.data;
  },

  updateDestination: async (destinationId: string, data: UpdateBroadcastDestinationData) => {
    const response = await client.put<BroadcastDestination>(`/api/broadcast-destinations/${destinationId}`, data);
    return response.data;
  },

  deleteDestination: async (destinationId: string) => {
    const response = await client.delete<{ status: string }>(`/api/broadcast-destinations/${destinationId}`);
    return response.data;
  },

  enableDestination: async (destinationId: string) => {
    const response = await client.post<{ status: string }>(`/api/broadcast-destinations/${destinationId}/enable`);
    return response.data;
  },

  disableDestination: async (destinationId: string) => {
    const response = await client.post<{ status: string }>(`/api/broadcast-destinations/${destinationId}/disable`);
    return response.data;
  },
};
