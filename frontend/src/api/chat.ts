import { client } from './client';

export interface ChatMessage {
  id: string;
  platform_id: string;
  channel_id: string;
  platform_message_id: string;
  author_name: string;
  author_display_name?: string;
  content: string;
  message_timestamp: string;
  author_color?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ChatMessageListResponse {
  messages: ChatMessage[];
  total: number;
}

export interface ChatMessageAggregatedResponse {
  channel_id: string;
  messages: ChatMessage[];
  platforms: string[];
  total: number;
}

export const chatApi = {
  listMessages: async (params?: {
    channel_id?: string;
    platform_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await client.get<ChatMessageListResponse>('/api/chat/messages/', { params });
    return response.data;
  },

  getMessage: async (messageId: string) => {
    const response = await client.get<ChatMessage>(`/api/chat/messages/${messageId}`);
    return response.data;
  },

  deleteMessage: async (messageId: string) => {
    const response = await client.delete<{ status: string }>(`/api/chat/messages/${messageId}`);
    return response.data;
  },

  getAggregatedMessages: async (params?: {
    channel_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await client.get<ChatMessageAggregatedResponse[]>('/api/chat/messages/aggregated/', { params });
    return response.data;
  },
};
