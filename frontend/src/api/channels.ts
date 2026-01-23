import { client } from './client';

export interface Channel {
  id: string;
  account_id: string;
  chat_id: number;
  chat_username?: string;
  name: string;
  status: 'stopped' | 'running' | 'error' | 'starting' | 'stopping' | 'unknown';
  error_message?: string;
  ffmpeg_args?: string;
  video_quality: string;
  stream_type?: 'video' | 'audio';
  placeholder_image?: string;
  video_codec?: string;
  audio_codec?: string;
  video_bitrate?: number;
  audio_bitrate?: number;
  resolution?: string;
}

export interface CreateChannelData {
  account_id: string;
  chat_id: number;
  chat_username?: string;
  name: string;
  ffmpeg_args?: string;
  video_quality?: string;
  stream_type?: 'video' | 'audio';
  playlist_id?: string;
  video_codec?: string;
  audio_codec?: string;
  video_bitrate?: number;
  audio_bitrate?: number;
  resolution?: string;
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

  delete: async (channelId: string) => {
    const response = await client.delete<{ status: string }>(`/api/channels/${channelId}`);
    return response.data;
  },

  update: async (channelId: string, data: CreateChannelData) => {
    const response = await client.put<Channel>(`/api/channels/${channelId}`, data);
    return response.data;
  },

  uploadPlaceholder: async (channelId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post<{ status: string, path: string }>(`/api/channels/${channelId}/placeholder`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
