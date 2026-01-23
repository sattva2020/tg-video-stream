import { client } from './client';

export interface Webhook {
  id: string;
  owner_id: string;
  url: string;
  event_types: string[];
  is_active: boolean;
  last_success_at: string | null;
  last_failure_at: string | null;
  failure_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface CreateWebhookData {
  url: string;
  event_types: string[];
}

export interface WebhookResponse extends Webhook {
  secret?: string | null;
}

export interface WebhookEvent {
  id: number;
  webhook_id: string;
  event_type: string;
  event_id: string | null;
  status: 'pending' | 'success' | 'failed' | 'retrying';
  attempt_number: number;
  attempted_at: string;
  response_status_code: number | null;
  response_body: string | null;
  response_headers: Record<string, unknown> | null;
  should_retry: boolean;
  next_retry_at: string | null;
  duration_ms: number | null;
}

export interface UpdateWebhookData {
  url?: string;
  event_types?: string[];
  is_active?: boolean;
}

export const webhooksApi = {
  list: async () => {
    const response = await client.get<Webhook[]>('/api/v1/webhooks/');
    return response.data;
  },

  create: async (data: CreateWebhookData) => {
    const response = await client.post<WebhookResponse>('/api/v1/webhooks/', data);
    return response.data;
  },

  get: async (webhookId: string) => {
    const response = await client.get<Webhook>(`/api/v1/webhooks/${webhookId}`);
    return response.data;
  },

  update: async (webhookId: string, data: UpdateWebhookData) => {
    const response = await client.patch<Webhook>(`/api/v1/webhooks/${webhookId}`, data);
    return response.data;
  },

  delete: async (webhookId: string) => {
    const response = await client.delete(`/api/v1/webhooks/${webhookId}`);
    return response.data;
  },

  test: async (webhookId: string) => {
    const response = await client.post<{ message: string }>(`/api/v1/webhooks/${webhookId}/test`);
    return response.data;
  },

  rotateSecret: async (webhookId: string) => {
    const response = await client.post<{ secret: string }>(`/api/v1/webhooks/${webhookId}/rotate-secret`);
    return response.data;
  },

  listEvents: async (webhookId: string, page: number = 1, pageSize: number = 20) => {
    const response = await client.get<{
      items: WebhookEvent[];
      total: number;
      page: number;
      page_size: number;
    }>(`/api/v1/webhooks/${webhookId}/events`, {
      params: { page, page_size: pageSize }
    });
    return response.data;
  },
};
