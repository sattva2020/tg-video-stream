/**
 * Channels API
 *
 * API endpoints for managing Telegram streaming channels.
 * Follows patterns from frontend/src/api/channels.ts
 */

import { client } from './client';

/**
 * Streaming channel interface
 * Represents a Telegram channel that can stream video/audio
 */
export interface StreamingChannel {
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
  created_at?: string;
  updated_at?: string;
}

/**
 * Data for creating a new channel
 */
export interface CreateChannelData {
  account_id: string;
  chat_id: number;
  chat_username?: string;
  name: string;
  ffmpeg_args?: string;
  video_quality?: string;
  stream_type?: 'video' | 'audio';
  playlist_id?: string;
}

/**
 * Response for channel start/stop operations
 */
export interface ChannelOperationResponse {
  status: string;
  message?: string;
}

/**
 * Channels API endpoints
 */
export const channelsApi = {
  /**
   * List all streaming channels
   */
  list: async (): Promise<StreamingChannel[]> => {
    const response = await client.get<StreamingChannel[]>('/api/channels/');
    return response.data;
  },

  /**
   * Get a single channel by ID
   */
  get: async (channelId: string): Promise<StreamingChannel> => {
    const response = await client.get<StreamingChannel>(`/api/channels/${channelId}`);
    return response.data;
  },

  /**
   * Create a new streaming channel
   */
  create: async (data: CreateChannelData): Promise<StreamingChannel> => {
    const response = await client.post<StreamingChannel>('/api/channels/', data);
    return response.data;
  },

  /**
   * Update an existing channel
   */
  update: async (channelId: string, data: Partial<CreateChannelData>): Promise<StreamingChannel> => {
    const response = await client.put<StreamingChannel>(`/api/channels/${channelId}`, data);
    return response.data;
  },

  /**
   * Delete a channel
   */
  delete: async (channelId: string): Promise<{ status: string }> => {
    const response = await client.delete<{ status: string }>(`/api/channels/${channelId}`);
    return response.data;
  },

  /**
   * Start streaming to a channel
   */
  start: async (channelId: string): Promise<ChannelOperationResponse> => {
    const response = await client.post<ChannelOperationResponse>(`/api/channels/${channelId}/start`);
    return response.data;
  },

  /**
   * Stop streaming to a channel
   */
  stop: async (channelId: string): Promise<ChannelOperationResponse> => {
    const response = await client.post<ChannelOperationResponse>(`/api/channels/${channelId}/stop`);
    return response.data;
  },

  /**
   * Get current status of a channel
   */
  getStatus: async (channelId: string): Promise<{ status: string }> => {
    const response = await client.get<{ status: string }>(`/api/channels/${channelId}/status`);
    return response.data;
  },

  /**
   * Upload a placeholder image for the channel
   */
  uploadPlaceholder: async (channelId: string, file: File): Promise<{ status: string; path: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post<{ status: string; path: string }>(
      `/api/channels/${channelId}/placeholder`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};
