import { client } from './client';

// ============================================================================
// Alert Rule Interfaces
// ============================================================================

export interface AlertRule {
  id: string;
  name: string;
  description?: string | null;
  enabled: boolean;
  alert_type: string;
  severity: string;
  category?: string | null;
  conditions: Record<string, unknown>;
  cooldown_sec: number;
  rate_limit_minutes?: number | null;
  rate_limit_count?: number | null;
  notification_channels?: Record<string, unknown> | null;
  notify_on_recovery: boolean;
  auto_resolve: boolean;
  escalation_enabled: boolean;
  escalation_rules?: Record<string, unknown> | null;
  active_windows?: Record<string, unknown> | null;
  silence_windows?: Record<string, unknown> | null;
  last_triggered_at?: string | null;
  last_resolved_at?: string | null;
  trigger_count: number;
  consecutive_triggers: number;
  created_at: string;
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
}

export type AlertRuleCreate = Omit<AlertRule, 'id' | 'last_triggered_at' | 'last_resolved_at' | 'trigger_count' | 'consecutive_triggers' | 'created_at' | 'updated_at' | 'created_by' | 'updated_by'>;
export type AlertRuleUpdate = Partial<AlertRuleCreate>;

export interface AlertRuleFilters {
  enabled?: boolean;
  alert_type?: string;
  severity?: string;
}

// ============================================================================
// Alert Instance Interfaces
// ============================================================================

export interface AlertInstance {
  id: string;
  rule_id: string;
  group_id?: string | null;
  alert_type: string;
  severity: string;
  status: string;
  trigger_value?: Record<string, unknown> | null;
  context?: Record<string, unknown> | null;
  notification_sent: boolean;
  notification_channels?: Record<string, unknown> | null;
  fired_at: string;
  resolved_at?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  duration_sec?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export type AlertInstanceCreate = Omit<AlertInstance, 'id' | 'fired_at' | 'resolved_at' | 'acknowledged_at' | 'acknowledged_by' | 'duration_sec' | 'created_at' | 'updated_at'>;
export type AlertInstanceUpdate = Partial<Pick<AlertInstance, 'status' | 'notification_sent' | 'notification_channels'>> & {
  resolved_at?: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  duration_sec?: number;
};

export interface AlertInstanceFilters {
  rule_id?: string;
  status?: string;
  alert_type?: string;
  severity?: string;
  group_id?: string;
  limit?: number;
}

// ============================================================================
// Alert Group Interfaces
// ============================================================================

export interface AlertGroup {
  id: string;
  rule_id: string;
  group_key: string;
  name?: string | null;
  status: string;
  alert_count: number;
  first_alert_at: string;
  last_alert_at: string;
  notification_sent: boolean;
  last_notification_at?: string | null;
  notification_count: number;
  severity: string;
  context?: Record<string, unknown> | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export type AlertGroupCreate = Omit<AlertGroup, 'id' | 'alert_count' | 'first_alert_at' | 'last_alert_at' | 'notification_sent' | 'last_notification_at' | 'notification_count' | 'resolved_at' | 'resolved_by' | 'created_at' | 'updated_at'>;
export type AlertGroupUpdate = Partial<Pick<AlertGroup, 'name' | 'status' | 'severity' | 'context'>> & {
  resolved_at?: string;
  resolved_by?: string;
};

export interface AlertGroupFilters {
  rule_id?: string;
  status?: string;
  severity?: string;
  skip?: number;
  limit?: number;
}

export interface AlertGroupDetail extends AlertGroup {
  instances: Array<{
    id: string;
    alert_type: string;
    severity: string;
    status: string;
    trigger_value?: Record<string, unknown> | null;
    fired_at: string;
    resolved_at?: string | null;
    duration_sec?: number | null;
  }>;
}

export interface ResolveGroupRequest {
  resolved: boolean;
}

export interface ResolveGroupResponse {
  success: boolean;
  message: string;
  group_id: string;
}

// ============================================================================
// Alert Statistics Interfaces
// ============================================================================

export interface AlertStatistics {
  total_groups: number;
  active_groups: number;
  resolved_groups: number;
  suppressed_groups: number;
  total_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  info_alerts: number;
  most_active_group?: {
    id: string;
    group_key: string;
    alert_count: number;
    severity: string;
  } | null;
  oldest_active_group?: {
    id: string;
    group_key: string;
    created_at: string;
    alert_count: number;
  } | null;
  average_alerts_per_group?: number | null;
}

// ============================================================================
// Alert Test Interfaces
// ============================================================================

export interface AlertTestRequest {
  alert_type: string;
  metric: string;
  value: number;
  severity?: string;
  context?: Record<string, unknown>;
}

export interface AlertTestResponse {
  status: string;
  event_id: string;
  instance_id?: string | null;
}

// ============================================================================
// Alert API
// ============================================================================

export const alertsApi = {
  // Alert Rules
  listRules: async (filters?: AlertRuleFilters) => {
    const response = await client.get<AlertRule[]>('/api/alerts/rules', { params: filters });
    return response.data;
  },
  getRule: async (ruleId: string) => {
    const response = await client.get<AlertRule>(`/api/alerts/rules/${ruleId}`);
    return response.data;
  },
  createRule: async (data: AlertRuleCreate) => {
    const response = await client.post<AlertRule>('/api/alerts/rules', data);
    return response.data;
  },
  updateRule: async (ruleId: string, data: AlertRuleUpdate) => {
    const response = await client.patch<AlertRule>(`/api/alerts/rules/${ruleId}`, data);
    return response.data;
  },
  deleteRule: async (ruleId: string) => {
    const response = await client.delete<void>(`/api/alerts/rules/${ruleId}`);
    return response.data;
  },

  // Alert Instances
  listInstances: async (filters?: AlertInstanceFilters) => {
    const response = await client.get<AlertInstance[]>('/api/alerts/instances', { params: filters });
    return response.data;
  },
  getInstance: async (instanceId: string) => {
    const response = await client.get<AlertInstance>(`/api/alerts/instances/${instanceId}`);
    return response.data;
  },

  // Alert Groups
  listGroups: async (filters?: AlertGroupFilters) => {
    const response = await client.get<AlertGroup[]>('/api/alerts/groups', { params: filters });
    return response.data;
  },
  getGroup: async (groupId: string) => {
    const response = await client.get<AlertGroupDetail>(`/api/alerts/groups/${groupId}`);
    return response.data;
  },
  getStatistics: async () => {
    const response = await client.get<AlertStatistics>('/api/alerts/groups/statistics');
    return response.data;
  },
  resolveGroup: async (groupId: string, request: ResolveGroupRequest) => {
    const response = await client.patch<ResolveGroupResponse>(`/api/alerts/groups/${groupId}/resolve`, request);
    return response.data;
  },

  // Alert Test
  testAlert: async (request: AlertTestRequest) => {
    const response = await client.post<AlertTestResponse>('/api/alerts/test', request);
    return response.data;
  },
};
