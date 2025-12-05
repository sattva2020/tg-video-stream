import { client } from './client';

export interface Channel {
  id: string;
  account_id: string;
  chat_id: number;
  name: string;
  status: 'stopped' | 'running' | 'error' | 'starting' | 'stopping' | 'unknown';
  ffmpeg_args?: string;
  video_quality: string;
}

export interface CreateChannelData {
  account_id: string;
  chat_id: number;
  name: string;
  ffmpeg_args?: string;
  video_quality?: string;
}

export const channelsApi = {
  list: async () => {
    const response = await client.get<Channel[]>('/api/channels/');
    return response.data;
  },

  create: async (data: CreateChannelData) => {
    const response = await client.post<Channel>('/api/channels/', data);
    return response.data;
  },

  start: async (channelId: string) => {
    const response = await client.post<{ status: string }>(`/api/channels/${channelId}/start`);
    return response.data;
  },

  stop: async (channelId: string) => {
    const response = await client.post<{ status: string }>(`/api/channels/${channelId}/stop`);
    return response.data;
  },

  getStatus: async (channelId: string) => {
    const response = await client.get<{ status: string }>(`/api/channels/${channelId}/status`);
    return response.data;
  },
};
