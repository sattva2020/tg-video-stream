import { client } from './client';

export type PostType = 'stream_start' | 'stream_end' | 'custom';
export type PostStatus = 'pending' | 'posted' | 'failed' | 'cancelled';

export interface SocialMediaPost {
  id: string;
  channel_id: string;
  platform_id: string;
  post_type: PostType;
  status: PostStatus;
  content?: string;
  platform_post_id?: string;
  platform_post_url?: string;
  error_message?: string;
  retry_count: number;
  posted_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateSocialMediaPostData {
  channel_id: string;
  platform_id: string;
  post_type: PostType;
  content?: string;
}

export const socialMediaApi = {
  listPosts: async (params?: {
    channel_id?: string;
    platform_id?: string;
    post_type?: PostType;
    status?: PostStatus;
    skip?: number;
    limit?: number;
  }) => {
    const response = await client.get<{ posts: SocialMediaPost[]; total: number }>('/api/social-media/posts/', { params });
    return response.data;
  },

  createPost: async (data: CreateSocialMediaPostData) => {
    const response = await client.post<SocialMediaPost>('/api/social-media/posts/', data);
    return response.data;
  },

  getPost: async (postId: string) => {
    const response = await client.get<SocialMediaPost>(`/api/social-media/posts/${postId}`);
    return response.data;
  },

  deletePost: async (postId: string) => {
    const response = await client.delete<{ status: string }>(`/api/social-media/posts/${postId}`);
    return response.data;
  },
};
