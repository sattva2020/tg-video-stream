import { client } from './client';

export interface NotificationChannel {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  enabled: boolean;
  status: string;
  concurrency_limit?: number | null;
  retry_attempts: number;
  retry_interval_sec: number;
  timeout_sec: number;
  is_primary: boolean;
  test_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export type NotificationChannelCreate = Omit<NotificationChannel, 'id' | 'created_at' | 'updated_at' | 'test_at'>;
export type NotificationChannelUpdate = Partial<NotificationChannelCreate>;

export interface NotificationTemplate {
  id: string;
  name: string;
  locale: string;
  subject?: string | null;
  body: string;
  variables?: Record<string, unknown> | null;
  channel_id?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export type NotificationTemplateCreate = Omit<NotificationTemplate, 'id' | 'created_at' | 'updated_at'>;
export type NotificationTemplateUpdate = Partial<NotificationTemplateCreate>;

export interface NotificationRecipient {
  id: string;
  type: string;
  address: string;
  status: 'active' | 'blocked' | 'opt-out' | string;
  silence_windows?: Record<string, unknown> | null;
  created_at: string;
  updated_at?: string | null;
}

export type NotificationRecipientCreate = Omit<NotificationRecipient, 'id' | 'created_at' | 'updated_at'>;
export type NotificationRecipientUpdate = Partial<NotificationRecipientCreate>;

export interface NotificationRule {
  id: string;
  name: string;
  enabled: boolean;
  severity_filter?: Record<string, unknown> | null;
  tag_filter?: Record<string, unknown> | null;
  host_filter?: Record<string, unknown> | null;
  failover_timeout_sec: number;
  silence_windows?: Record<string, unknown> | null;
  rate_limit?: Record<string, unknown> | null;
  dedup_window_sec: number;
  template_id?: string | null;
  recipient_ids: string[];
  channel_ids: string[];
  test_channel_ids?: string[] | null;
  created_at: string;
  updated_at?: string | null;
}

export type NotificationRuleCreate = Omit<NotificationRule, 'id' | 'created_at' | 'updated_at'>;
export type NotificationRuleUpdate = Partial<NotificationRuleCreate>;

export interface RuleTestRequest {
  event_id?: string;
  severity?: string;
  tags?: Record<string, unknown>;
  host?: string;
  context?: Record<string, unknown>;
  subject?: string;
  body?: string;
}

export interface RuleTestResponse {
  status: string;
  event_id: string;
  tasks_enqueued: number;
}

export type DeliveryLogStatus =
  | 'success'
  | 'fail'
  | 'failover'
  | 'suppressed'
  | 'rate-limited'
  | 'deduped'
  | string;

export interface DeliveryLog {
  id: string;
  event_id: string;
  rule_id?: string | null;
  channel_id?: string | null;
  recipient_id?: string | null;
  status: DeliveryLogStatus;
  attempt: number;
  latency_ms?: number | null;
  response_code?: number | null;
  response_body?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface DeliveryLogFilters {
  rule_id?: string;
  channel_id?: string;
  recipient_id?: string;
  event_id?: string;
  statuses?: string[];
  created_from?: string;
  created_to?: string;
  limit?: number;
}

export interface ChannelTestRequest {
  recipient: string;
  subject?: string;
  body?: string;
  context?: Record<string, unknown>;
  use_celery?: boolean;
}

export interface ChannelTestResponse {
  status: string;
  event_id: string;
}

export const notificationsApi = {
  // Channels
  listChannels: async () => {
    const response = await client.get<NotificationChannel[]>('/api/notifications/channels');
    return response.data;
  },
  createChannel: async (data: NotificationChannelCreate) => {
    const response = await client.post<NotificationChannel>('/api/notifications/channels', data);
    return response.data;
  },
  updateChannel: async (id: string, data: NotificationChannelUpdate) => {
    const response = await client.patch<NotificationChannel>(`/api/notifications/channels/${id}`, data);
    return response.data;
  },
  deleteChannel: async (id: string) => {
    const response = await client.delete<void>(`/api/notifications/channels/${id}`);
    return response.data;
  },
  testChannel: async (id: string, payload: ChannelTestRequest) => {
    const response = await client.post<ChannelTestResponse>(`/api/notifications/channels/${id}/test`, payload);
    return response.data;
  },

  // Templates
  listTemplates: async () => {
    const response = await client.get<NotificationTemplate[]>('/api/notifications/templates');
    return response.data;
  },
  createTemplate: async (data: NotificationTemplateCreate) => {
    const response = await client.post<NotificationTemplate>('/api/notifications/templates', data);
    return response.data;
  },
  updateTemplate: async (id: string, data: NotificationTemplateUpdate) => {
    const response = await client.patch<NotificationTemplate>(`/api/notifications/templates/${id}`, data);
    return response.data;
  },
  deleteTemplate: async (id: string) => {
    const response = await client.delete<void>(`/api/notifications/templates/${id}`);
    return response.data;
  },

  // Recipients
  listRecipients: async () => {
    const response = await client.get<NotificationRecipient[]>('/api/notifications/recipients');
    return response.data;
  },
  createRecipient: async (data: NotificationRecipientCreate) => {
    const response = await client.post<NotificationRecipient>('/api/notifications/recipients', data);
    return response.data;
  },
  updateRecipient: async (id: string, data: NotificationRecipientUpdate) => {
    const response = await client.patch<NotificationRecipient>(`/api/notifications/recipients/${id}`, data);
    return response.data;
  },
  deleteRecipient: async (id: string) => {
    const response = await client.delete<void>(`/api/notifications/recipients/${id}`);
    return response.data;
  },

  // Rules
  listRules: async () => {
    const response = await client.get<NotificationRule[]>('/api/notifications/rules');
    return response.data;
  },
  createRule: async (data: NotificationRuleCreate) => {
    const response = await client.post<NotificationRule>('/api/notifications/rules', data);
    return response.data;
  },
  updateRule: async (id: string, data: NotificationRuleUpdate) => {
    const response = await client.patch<NotificationRule>(`/api/notifications/rules/${id}`, data);
    return response.data;
  },
  deleteRule: async (id: string) => {
    const response = await client.delete<void>(`/api/notifications/rules/${id}`);
    return response.data;
  },
  testRule: async (id: string, payload: RuleTestRequest) => {
    const response = await client.post<RuleTestResponse>(`/api/notifications/rules/${id}/test`, payload);
    return response.data;
  },

  // Delivery logs
  listLogs: async (filters?: DeliveryLogFilters) => {
    const response = await client.get<DeliveryLog[]>('/api/notifications/logs', { params: filters });
    return response.data;
  },
};
