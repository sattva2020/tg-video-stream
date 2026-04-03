import { client } from './client';

// ========== Rate Limit Types ==========

export interface AccountLimitStatus {
  account_id: string;
  endpoint_type: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  status: 'healthy' | 'warning' | 'critical';
  predicted_breach_time?: string | null;
  time_until_breach_seconds?: number | null;
}

export interface RateLimitStatusResponse {
  overall_status: 'healthy' | 'warning' | 'critical';
  total_accounts: number;
  active_accounts: number;
  rate_limited_accounts: number;
  accounts: AccountLimitStatus[];
  timestamp: string;
}

export interface UsageMetrics {
  account_id: string;
  requests_per_minute: number;
  trend: 'increasing' | 'stable' | 'decreasing';
  confidence: number;
  window_start?: string | null;
  window_end?: string | null;
}

export interface PredictionMetrics {
  endpoint_type: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  predicted_breach_time?: string | null;
  time_until_breach_seconds?: number | null;
  trend: 'increasing' | 'stable' | 'decreasing';
  confidence: number;
  alert_triggered: boolean;
  is_critical: boolean;
}

export interface RateLimitMetricsResponse {
  usage_metrics: UsageMetrics[];
  predictions: PredictionMetrics[];
  summary: Record<string, any>;
  timestamp: string;
}

export interface RateLimitPrediction {
  account_id: string;
  endpoint_type: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  predicted_breach_time?: string | null;
  time_until_breach_seconds?: number | null;
  trend: 'increasing' | 'stable' | 'decreasing';
  confidence: number;
  status: 'healthy' | 'warning' | 'critical';
}

export interface PredictionsResponse {
  predictions: RateLimitPrediction[];
  summary: Record<string, any>;
  timestamp: string;
}

export interface AccountInfo {
  account_id: string;
  status: 'active' | 'rate_limited' | 'disabled' | 'failed' | 'banned';
  health: 'healthy' | 'degraded' | 'failed' | 'disabled';
  usage_percent: number;
  success_count: number;
  failure_count: number;
  last_used?: string | null;
}

export interface AccountDistributionResponse {
  total_accounts: number;
  active_accounts: number;
  rate_limited_accounts: number;
  disabled_accounts: number;
  failed_accounts: number;
  accounts: AccountInfo[];
  selection_strategy: string;
  timestamp: string;
}

export interface QueueStats {
  priority_level: 'HIGH' | 'MEDIUM' | 'LOW';
  pending_requests: number;
  processing_requests: number;
  completed_last_minute: number;
  average_wait_time_seconds: number;
}

export interface QueueStatsResponse {
  total_pending: number;
  total_processing: number;
  stats_by_priority: QueueStats[];
  batch_size: number;
  batch_timeout_seconds: number;
  timestamp: string;
}

export interface AccountAddRequest {
  account_id: string;
  phone: string;
}

export interface AccountUpdateRequest {
  status: 'active' | 'disabled' | 'failed';
}

export interface AccountOperationResponse {
  success: boolean;
  message: string;
  account_id: string;
}

export interface AlertThresholds {
  warning_threshold_percent?: number;
  critical_threshold_percent?: number;
}

export interface NotificationPreferences {
  enabled?: boolean;
  channels?: string[];
  notify_on_warning?: boolean;
  notify_on_critical?: boolean;
  cooldown_seconds?: number;
}

export interface RateLimitSettingsRequest {
  alert_thresholds?: AlertThresholds;
  notification_preferences?: NotificationPreferences;
}

export interface RateLimitSettingsResponse {
  alert_thresholds: AlertThresholds;
  notification_preferences: NotificationPreferences;
  timestamp: string;
}

// ========== Rate Limit API ==========

export const rateLimitsApi = {
  // Get overall rate limit status
  getStatus: async (): Promise<RateLimitStatusResponse> => {
    const response = await client.get('/api/v1/rate-limits/status');
    return response.data;
  },

  // Get detailed metrics with usage and predictions
  getMetrics: async (accountId?: string): Promise<RateLimitMetricsResponse> => {
    const response = await client.get('/api/v1/rate-limits/metrics', {
      params: accountId ? { account_id: accountId } : {}
    });
    return response.data;
  },

  // Get predictions for all accounts
  getPredictions: async (accountId?: string): Promise<PredictionsResponse> => {
    const response = await client.get('/api/v1/rate-limits/predictions', {
      params: accountId ? { account_id: accountId } : {}
    });
    return response.data;
  },

  // Get account pool distribution
  getAccounts: async (): Promise<AccountDistributionResponse> => {
    const response = await client.get('/api/v1/rate-limits/accounts');
    return response.data;
  },

  // Get queue statistics
  getQueueStats: async (): Promise<QueueStatsResponse> => {
    const response = await client.get('/api/v1/rate-limits/queue');
    return response.data;
  },

  // Add account to pool
  addAccount: async (request: AccountAddRequest): Promise<AccountOperationResponse> => {
    const response = await client.post('/api/v1/rate-limits/accounts', request);
    return response.data;
  },

  // Update account status
  updateAccount: async (accountId: string, request: AccountUpdateRequest): Promise<AccountOperationResponse> => {
    const response = await client.put(`/api/v1/rate-limits/accounts/${accountId}`, request);
    return response.data;
  },

  // Remove account from pool
  removeAccount: async (accountId: string): Promise<AccountOperationResponse> => {
    const response = await client.delete(`/api/v1/rate-limits/accounts/${accountId}`);
    return response.data;
  },

  // Update rate limit settings
  updateSettings: async (request: RateLimitSettingsRequest): Promise<RateLimitSettingsResponse> => {
    const response = await client.put('/api/v1/rate-limits/settings', request);
    return response.data;
  },
};
