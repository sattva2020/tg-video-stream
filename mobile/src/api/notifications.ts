/**
 * Notifications API Module
 *
 * Provides API functions for managing notification rules, channels, templates, recipients, and delivery logs.
 * Follows patterns from frontend/src/api/notifications.ts adapted for React Native.
 *
 * Features:
 * - Full CRUD for notification rules, channels, templates, recipients
 * - Delivery log filtering and querying
 * - Test functionality for rules and channels
 */

import { apiClient } from './client';

// ============================================
// Type Definitions
// ============================================

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

// ============================================
// API Functions
// ============================================

export const notificationsApi = {
  // Channels
  listChannels: async (): Promise<NotificationChannel[]> => {
    const response = await apiClient.get<NotificationChannel[]>('/api/notifications/channels');
    return response.data;
  },

  createChannel: async (data: NotificationChannelCreate): Promise<NotificationChannel> => {
    const response = await apiClient.post<NotificationChannel>('/api/notifications/channels', data);
    return response.data;
  },

  updateChannel: async (id: string, data: NotificationChannelUpdate): Promise<NotificationChannel> => {
    const response = await apiClient.patch<NotificationChannel>(`/api/notifications/channels/${id}`, data);
    return response.data;
  },

  deleteChannel: async (id: string): Promise<void> => {
    await apiClient.delete<void>(`/api/notifications/channels/${id}`);
  },

  testChannel: async (id: string, payload: ChannelTestRequest): Promise<ChannelTestResponse> => {
    const response = await apiClient.post<ChannelTestResponse>(`/api/notifications/channels/${id}/test`, payload);
    return response.data;
  },

  // Templates
  listTemplates: async (): Promise<NotificationTemplate[]> => {
    const response = await apiClient.get<NotificationTemplate[]>('/api/notifications/templates');
    return response.data;
  },

  createTemplate: async (data: NotificationTemplateCreate): Promise<NotificationTemplate> => {
    const response = await apiClient.post<NotificationTemplate>('/api/notifications/templates', data);
    return response.data;
  },

  updateTemplate: async (id: string, data: NotificationTemplateUpdate): Promise<NotificationTemplate> => {
    const response = await apiClient.patch<NotificationTemplate>(`/api/notifications/templates/${id}`, data);
    return response.data;
  },

  deleteTemplate: async (id: string): Promise<void> => {
    await apiClient.delete<void>(`/api/notifications/templates/${id}`);
  },

  // Recipients
  listRecipients: async (): Promise<NotificationRecipient[]> => {
    const response = await apiClient.get<NotificationRecipient[]>('/api/notifications/recipients');
    return response.data;
  },

  createRecipient: async (data: NotificationRecipientCreate): Promise<NotificationRecipient> => {
    const response = await apiClient.post<NotificationRecipient>('/api/notifications/recipients', data);
    return response.data;
  },

  updateRecipient: async (id: string, data: NotificationRecipientUpdate): Promise<NotificationRecipient> => {
    const response = await apiClient.patch<NotificationRecipient>(`/api/notifications/recipients/${id}`, data);
    return response.data;
  },

  deleteRecipient: async (id: string): Promise<void> => {
    await apiClient.delete<void>(`/api/notifications/recipients/${id}`);
  },

  // Rules
  listRules: async (): Promise<NotificationRule[]> => {
    const response = await apiClient.get<NotificationRule[]>('/api/notifications/rules');
    return response.data;
  },

  createRule: async (data: NotificationRuleCreate): Promise<NotificationRule> => {
    const response = await apiClient.post<NotificationRule>('/api/notifications/rules', data);
    return response.data;
  },

  updateRule: async (id: string, data: NotificationRuleUpdate): Promise<NotificationRule> => {
    const response = await apiClient.patch<NotificationRule>(`/api/notifications/rules/${id}`, data);
    return response.data;
  },

  deleteRule: async (id: string): Promise<void> => {
    await apiClient.delete<void>(`/api/notifications/rules/${id}`);
  },

  testRule: async (id: string, payload: RuleTestRequest): Promise<RuleTestResponse> => {
    const response = await apiClient.post<RuleTestResponse>(`/api/notifications/rules/${id}/test`, payload);
    return response.data;
  },

  // Delivery logs
  listLogs: async (filters?: DeliveryLogFilters): Promise<DeliveryLog[]> => {
    const response = await apiClient.get<DeliveryLog[]>('/api/notifications/logs', {
      params: filters,
    });
    return response.data;
  },
};
