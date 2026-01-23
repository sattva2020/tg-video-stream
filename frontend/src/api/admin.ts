import { client } from './client';

export interface StreamMetrics {
  online: boolean;
  current_stream_url?: string | null;
  current_stream_name?: string | null;
  metrics: {
    timestamp: number;
    system: {
      cpu_percent: number;
      memory_percent: number;
      memory_used: number;
      memory_total: number;
    };
    process: {
      cpu_percent: number;
      memory_rss: number;
      memory_vms: number;
    };
  } | null;
}

export interface CurrentTrack {
  id: string | null;
  title: string | null;
  url: string | null;
  duration: number | null;
  type: string | null;
}

export interface StreamStatus {
  online: boolean;
  status: 'running' | 'stopped' | 'error' | 'unknown';
  uptime_seconds: number;
  current_track: CurrentTrack | null;
  queue: {
    total: number;
    queued: number;
  };
  metrics: StreamMetrics['metrics'] | null;
  error?: string;
}

export interface User {
  id: string;
  email: string;
  status: string;
  role?: string;
  full_name?: string;
  created_at?: string;
}

export interface PaginatedUsersResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UsersListParams {
  status?: string;
  page?: number;
  page_size?: number;
  search?: string;
}

// Feature 022 Phase 2: Stream Quality Types
export interface AudioQualityMetrics {
  codec?: string;
  bitrate_kbps?: number;
  sample_rate_hz?: number;
  channels?: number;
  duration_sec?: number;
  quality?: string;  // low, medium, high, lossless
}

export interface VideoQualityMetrics {
  codec?: string;
  bitrate_kbps?: number;
  resolution?: string;  // e.g. "1920x1080"
  fps?: number;
  duration_sec?: number;
  quality?: string;  // low, medium, high, ultra
}

export interface PerformanceMetrics {
  dropped_frames?: number;
  speed?: number;
  fps?: number;
  bitrate_kbps?: number;
}

export interface StreamQualityResponse {
  url: string;
  audio?: AudioQualityMetrics | null;
  video?: VideoQualityMetrics | null;
  performance?: PerformanceMetrics | null;
  is_audio_only: boolean;
  is_video_only: boolean;
  has_both: boolean;
  overall_quality: string;  // low, medium, high, lossless, ultra, unknown
}

// ========== Feature 022 Phase 3: Trends & Alerts ==========

export interface QualityHistoryPoint {
  timestamp: string;  // ISO 8601
  overall_quality: string;
  audio_quality?: string;
  audio_bitrate_kbps?: number;
  video_quality?: string;
  video_bitrate_kbps?: number;
  video_resolution?: string;
  video_fps?: number;
  success: boolean;
  error_message?: string;
}

export interface QualityTrendData {
  stream_url: string;
  stream_name?: string;
  history: QualityHistoryPoint[];
  average_quality: string;
  min_quality: string;
  max_quality: string;
  audio_avg_bitrate_kbps?: number;
  video_avg_bitrate_kbps?: number;
  video_avg_resolution?: string;
  success_rate: number;  // 0-1
  period_start: string;  // ISO 8601
  period_end: string;    // ISO 8601
  samples_count: number;
}

export interface QualityAlertConfigUpdate {
  stream_url: string;
  stream_name?: string;
  min_overall_quality?: string;
  min_audio_quality?: string;
  min_video_quality?: string;
  min_audio_bitrate_kbps?: number;
  min_video_bitrate_kbps?: number;
  min_video_resolution?: string;
  min_video_fps?: number;
  enabled?: boolean;
  notify_on_degradation?: boolean;
  notify_on_recovery?: boolean;
  consecutive_failures?: number;
  alert_channels?: Record<string, string[]>;
}

export interface QualityAlertConfigResponse extends QualityAlertConfigUpdate {
  id: number;
  last_alert_at?: string;
  last_alert_type?: string;
  consecutive_failures_count: number;
  created_at: string;
  updated_at: string;
}

export const adminApi = {
  startStream: async () => {
    const response = await client.post('/api/admin/stream/start');
    return response.data;
  },
  stopStream: async () => {
    const response = await client.post('/api/admin/stream/stop');
    return response.data;
  },
  restartStream: async () => {
    const response = await client.post('/api/admin/stream/restart');
    return response.data;
  },
  getStreamStatus: async (): Promise<StreamStatus> => {
    const response = await client.get('/api/admin/stream/status');
    return response.data;
  },
  getLogs: async (lines: number = 100) => {
    const response = await client.get('/api/admin/stream/logs', { params: { lines } });
    return response.data;
  },
  getMetrics: async (): Promise<StreamMetrics> => {
    const response = await client.get('/api/admin/stream/metrics');
    return response.data;
  },
  listUsers: async (params?: UsersListParams): Promise<PaginatedUsersResponse> => {
    const response = await client.get('/api/admin/users', { params });
    return response.data;
  },
  approveUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/approve`);
    return response.data;
  },
  rejectUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/reject`);
    return response.data;
  },
  updateUserRole: async (id: string, role: string) => {
    const response = await client.put(`/api/admin/users/${id}/role`, { role });
    return response.data;
  },
  getPlaylist: async () => {
    const response = await client.get('/api/admin/playlist');
    return response.data;
  },
  updatePlaylist: async (items: string[]) => {
    const response = await client.post('/api/admin/playlist', { items });
    return response.data;
  },

  // Feature 022 Phase 2: Stream Quality Analysis
  getStreamQuality: async (streamUrl: string, timeout: number = 10, useCache: boolean = true): Promise<StreamQualityResponse | null> => {
    const response = await client.get('/api/admin/stream/quality/' + encodeURIComponent(streamUrl), {
      params: { timeout, use_cache: useCache }
    });
    return response.data;
  },

  batchAnalyzeStreams: async (urls: string[], timeout: number = 10): Promise<Record<string, StreamQualityResponse | null>> => {
    const response = await client.get('/api/admin/streams/quality/batch', {
      params: { urls, timeout }
    });
    return response.data;
  },

  clearQualityCache: async (streamUrl?: string) => {
    const response = await client.post('/api/admin/quality/cache/clear', null, {
      params: streamUrl ? { stream_url: streamUrl } : {}
    });
    return response.data;
  },

  // Feature 022 Phase 3: Trends & Alerts
  getQualityTrend: async (streamUrl: string, hours: number = 24): Promise<QualityTrendData> => {
    const response = await client.get(`/api/admin/stream/quality/trend/${encodeURIComponent(streamUrl)}`, {
      params: { hours }
    });
    return response.data;
  },

  setQualityAlertConfig: async (config: QualityAlertConfigUpdate): Promise<QualityAlertConfigResponse> => {
    const response = await client.post('/api/admin/stream/quality/alert/config', config);
    return response.data;
  },

  getQualityAlertConfig: async (streamUrl: string): Promise<QualityAlertConfigResponse | null> => {
    const response = await client.get(`/api/admin/stream/quality/alert/config/${encodeURIComponent(streamUrl)}`);
    return response.data;
  },

  // Feature 025: IP Whitelist Management
  getIPWhitelistEntries: async (params?: { active_only?: boolean; ipv4_only?: boolean; ipv6_only?: boolean }): Promise<IPWhitelistEntry[]> => {
    const response = await client.get('/api/admin/ip-whitelist/entries', { params });
    return response.data;
  },

  getIPWhitelistInfo: async (): Promise<IPWhitelistInfo> => {
    const response = await client.get('/api/admin/ip-whitelist/entries/info');
    return response.data;
  },

  getIPWhitelistEntry: async (entryId: string): Promise<IPWhitelistEntry> => {
    const response = await client.get(`/api/admin/ip-whitelist/entries/${entryId}`);
    return response.data;
  },

  createIPWhitelistEntry: async (data: IPWhitelistCreate): Promise<IPWhitelistEntry> => {
    const response = await client.post('/api/admin/ip-whitelist/entries', data);
    return response.data;
  },

  updateIPWhitelistEntry: async (entryId: string, data: IPWhitelistUpdate): Promise<IPWhitelistEntry> => {
    const response = await client.put(`/api/admin/ip-whitelist/entries/${entryId}`, data);
    return response.data;
  },

  deleteIPWhitelistEntry: async (entryId: string) => {
    const response = await client.delete(`/api/admin/ip-whitelist/entries/${entryId}`);
    return response.data;
  },

  activateIPWhitelistEntry: async (entryId: string) => {
    const response = await client.post(`/api/admin/ip-whitelist/entries/${entryId}/activate`);
    return response.data;
  },

  deactivateIPWhitelistEntry: async (entryId: string) => {
    const response = await client.post(`/api/admin/ip-whitelist/entries/${entryId}/deactivate`);
    return response.data;
  },

  checkIPWhitelist: async (ip: string) => {
    const response = await client.post('/api/admin/ip-whitelist/check', null, { params: { ip } });
    return response.data;
  },

  // Feature 025: Security Policy Management
  getSecurityPolicies: async (params?: {
    enabled_only?: boolean;
    policy_type?: string;
    enforcement_level?: string;
  }): Promise<SecurityPolicy[]> => {
    const response = await client.get('/api/admin/security-policies/policies', { params });
    return response.data;
  },

  getSecurityPolicyInfo: async (): Promise<SecurityPolicyInfo> => {
    const response = await client.get('/api/admin/security-policies/policies/info');
    return response.data;
  },

  getSecurityPolicy: async (policyId: string): Promise<SecurityPolicy> => {
    const response = await client.get(`/api/admin/security-policies/policies/${policyId}`);
    return response.data;
  },

  createSecurityPolicy: async (data: SecurityPolicyCreate): Promise<SecurityPolicy> => {
    const response = await client.post('/api/admin/security-policies/policies', data);
    return response.data;
  },

  updateSecurityPolicy: async (policyId: string, data: SecurityPolicyUpdate): Promise<SecurityPolicy> => {
    const response = await client.put(`/api/admin/security-policies/policies/${policyId}`, data);
    return response.data;
  },

  deleteSecurityPolicy: async (policyId: string) => {
    const response = await client.delete(`/api/admin/security-policies/policies/${policyId}`);
    return response.data;
  },

  enableSecurityPolicy: async (policyId: string) => {
    const response = await client.post(`/api/admin/security-policies/policies/${policyId}/enable`);
    return response.data;
  },

  disableSecurityPolicy: async (policyId: string) => {
    const response = await client.post(`/api/admin/security-policies/policies/${policyId}/disable`);
    return response.data;
  },

  // Feature 025: Security Dashboard
  getSecurityDashboard: async (framework: string = 'soc2', days: number = 30): Promise<SecurityDashboardResponse> => {
    const response = await client.get('/api/admin/security/dashboard', {
      params: { framework, days }
    });
    return response.data;
  },

  getSecurityMetrics: async (days: number = 30): Promise<SecurityMetrics> => {
    const response = await client.get('/api/admin/security/dashboard/metrics', {
      params: { days }
    });
    return response.data;
  },

  getComplianceStatus: async (framework: string): Promise<ComplianceStatusSummary> => {
    const response = await client.get(`/api/admin/security/dashboard/compliance/${framework}`);
    return response.data;
  },

  getDataProtectionStatus: async (): Promise<DataProtectionStatus> => {
    const response = await client.get('/api/admin/security/dashboard/data-protection');
    return response.data;
  },

  getAccessControlStatus: async (): Promise<AccessControlStatus> => {
    const response = await client.get('/api/admin/security/dashboard/access-control');
    return response.data;
  },

  getSecurityConfigSummary: async (): Promise<SecurityConfigSummary> => {
    const response = await client.get('/api/admin/security/dashboard/security-configs');
    return response.data;
  },

  getRecentCriticalEvents: async (limit: number = 10, severity?: string): Promise<{
    total: number;
    events: Array<{
      id: string;
      event_type: string;
      category: string;
      severity: string;
      compliance_status: string;
      title: string;
      description: string;
      resource_type?: string;
      resource_id?: string;
      timestamp: string | null;
    }>;
  }> => {
    const response = await client.get('/api/admin/security/dashboard/recent-events', {
      params: { limit, severity }
    });
    return response.data;
  },

  getSecurityEventsHistory: async (
    period: '1d' | '7d' | '30d' | '90d' | '1y' = '7d',
    interval: 'hour' | 'day' | 'week' = 'day',
    category?: string,
    severity?: string
  ): Promise<SecurityEventsHistoryResponse> => {
    const response = await client.get('/api/admin/security/security/events', {
      params: { period, interval, category, severity }
    });
    return response.data;
  },
};

// Feature 025: IP Whitelist Types
export interface IPWhitelistEntry {
  id: string;
  cidr: string;
  description: string | null;
  is_active: boolean;
  is_ipv4: boolean;
  is_ipv6: boolean;
  created_by_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface IPWhitelistInfo {
  total_entries: number;
  active_entries: number;
  inactive_entries: number;
  ipv4_entries: number;
  ipv6_entries: number;
}

export interface IPWhitelistCreate {
  cidr: string;
  description?: string;
  is_active?: boolean;
}

export interface IPWhitelistUpdate {
  description?: string;
  is_active?: boolean;
}

// Feature 025: Security Policy Types
export interface SecurityPolicy {
  id: string;
  name: string;
  policy_type: string;
  enabled: boolean;
  enforcement_level: string;
  affected_roles: string[] | null;
  grace_period_hours: number | null;
  allow_exempt_alternative_auth: boolean;
  policy_config: Record<string, unknown> | null;
  description: string | null;
  created_by_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SecurityPolicyInfo {
  total_policies: number;
  enabled_policies: number;
  disabled_policies: number;
  mandatory_policies: number;
  optional_policies: number;
  audit_only_policies: number;
  policies_by_type: Record<string, number>;
}

export interface SecurityPolicyCreate {
  name: string;
  policy_type?: string;
  enabled?: boolean;
  enforcement_level?: string;
  affected_roles?: string[] | null;
  grace_period_hours?: number | null;
  allow_exempt_alternative_auth?: boolean;
  policy_config?: Record<string, unknown> | null;
  description?: string | null;
}

export interface SecurityPolicyUpdate {
  name?: string;
  policy_type?: string;
  enabled?: boolean;
  enforcement_level?: string;
  affected_roles?: string[] | null;
  grace_period_hours?: number | null;
  allow_exempt_alternative_auth?: boolean;
  policy_config?: Record<string, unknown> | null;
  description?: string | null;
}

// Feature 025: Security Dashboard Types
export interface ComplianceStatusSummary {
  framework: string;
  overall_status: string;
  non_compliant_events_last_30_days: number;
  requirements: Array<{
    requirement: string;
    status: string;
    description: string;
  }>;
  last_checked: string;
}

export interface SecurityMetrics {
  total_events: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  unresolved_incidents: number;
  period: {
    start: string;
    end: string;
    days: number;
  };
}

export interface DataProtectionStatus {
  overall_status: string;
  checks: Record<string, {
    status: string;
    description: string;
    last_checked?: string;
  }>;
  last_checked: string;
}

export interface AccessControlStatus {
  overall_status: string;
  checks: Record<string, {
    status: string;
    description: string;
    last_checked?: string;
  }>;
  last_checked: string;
}

export interface SecurityConfigSummary {
  saml_configs_enabled: number;
  saml_configs_total: number;
  security_policies_enabled: number;
  security_policies_total: number;
  ip_whitelist_entries: number;
  two_factor_enforcement_enabled: boolean;
}

export interface SecurityDashboardResponse {
  compliance_status: ComplianceStatusSummary;
  security_metrics: SecurityMetrics;
  data_protection: DataProtectionStatus;
  access_control: AccessControlStatus;
  security_configs: SecurityConfigSummary;
  recent_critical_events: Array<{
    id: string;
    event_type: string;
    category: string;
    severity: string;
    compliance_status: string;
    title: string;
    description: string;
    timestamp: string | null;
  }>;
  generated_at: string;
}

export interface SecurityEventBucket {
  timestamp: string;
  total_events: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  critical_events: number;
  high_events: number;
  resolved_events: number;
}

export interface SecurityEventsHistoryResponse {
  period: {
    start: string;
    end: string;
    days: number;
  };
  interval: string;
  total_events: number;
  buckets: SecurityEventBucket[];
  summary: {
    resolved_events: number;
    critical_events: number;
    high_events: number;
    unresolved_events: number;
  };
}
