export type FeatureTier = 'core' | 'advanced' | 'unique';

export type FeatureConfig = {
  id: string;
  badgeKey: string;
  titleKey: string;
  descriptionKey: string;
  metricKey?: string;
  pointKeys?: string[];
  layout?: 'standard' | 'wide' | 'tall';
  tier: FeatureTier;
};

export type WorkflowStepConfig = {
  id: string;
  titleKey: string;
  descriptionKey: string;
};

export type UseCaseConfig = {
  id: string;
  titleKey: string;
  descriptionKey: string;
  accent: 'sky' | 'violet' | 'amber';
};

export const featureHighlights: FeatureConfig[] = [
  {
    id: 'multi-channel',
    badgeKey: 'landing_feature_multi_channel_badge',
    tier: 'unique',
    titleKey: 'landing_feature_multi_channel_title',
    descriptionKey: 'landing_feature_multi_channel_desc',
    metricKey: 'landing_feature_multi_channel_metric',
    pointKeys: ['landing_feature_multi_channel_point_isolation', 'landing_feature_multi_channel_point_console'],
    layout: 'wide',
  },
  {
    id: 'content-sources',
    tier: 'core',
    badgeKey: 'landing_feature_content_sources_badge',
    titleKey: 'landing_feature_content_sources_title',
    descriptionKey: 'landing_feature_content_sources_desc',
    metricKey: 'landing_feature_content_sources_metric',
    pointKeys: ['landing_feature_content_sources_point_mix', 'landing_feature_content_sources_point_switch'],
  },
  {
    id: 'schedule-engine',
    badgeKey: 'landing_feature_schedule_badge',
    tier: 'advanced',
    titleKey: 'landing_feature_schedule_title',
    descriptionKey: 'landing_feature_schedule_desc',
    metricKey: 'landing_feature_schedule_metric',
    pointKeys: ['landing_feature_schedule_point_templates', 'landing_feature_schedule_point_drag'],
    layout: 'tall',
  },
  {
    tier: 'advanced',
    id: 'secure-rbac',
    badgeKey: 'landing_feature_security_badge',
    titleKey: 'landing_feature_security_title',
    descriptionKey: 'landing_feature_security_desc',
    pointKeys: ['landing_feature_security_point_roles', 'landing_feature_security_point_mfa'],
  },
  {
    id: 'resilience',
    badgeKey: 'landing_feature_resilience_badge',
    tier: 'unique',
    titleKey: 'landing_feature_resilience_title',
    descriptionKey: 'landing_feature_resilience_desc',
    metricKey: 'landing_feature_resilience_metric',
    pointKeys: ['landing_feature_resilience_point_self_heal', 'landing_feature_resilience_point_alerts'],
    layout: 'wide',
  },
  {
    tier: 'core',
    id: 'observability',
    badgeKey: 'landing_feature_observe_badge',
    titleKey: 'landing_feature_observe_title',
    descriptionKey: 'landing_feature_observe_desc',
    pointKeys: ['landing_feature_observe_point_dashboards', 'landing_feature_observe_point_metrics'],
  },
];

export const workflowSteps: WorkflowStepConfig[] = [
  {
    id: 'connect',
    titleKey: 'landing_step_connect_title',
    descriptionKey: 'landing_step_connect_desc',
  },
  {
    id: 'playlist',
    titleKey: 'landing_step_playlist_title',
    descriptionKey: 'landing_step_playlist_desc',
  },
  {
    id: 'schedule',
    titleKey: 'landing_step_schedule_title',
    descriptionKey: 'landing_step_schedule_desc',
  },
  {
    id: 'monitor',
    titleKey: 'landing_step_monitor_title',
    descriptionKey: 'landing_step_monitor_desc',
  },
];

export const landingUseCases: UseCaseConfig[] = [
  {
    id: 'news',
    titleKey: 'landing_usecase_news_title',
    descriptionKey: 'landing_usecase_news_desc',
    accent: 'sky',
  },
  {
    id: 'radio',
    titleKey: 'landing_usecase_radio_title',
    descriptionKey: 'landing_usecase_radio_desc',
    accent: 'violet',
  },
  {
    id: 'media',
    titleKey: 'landing_usecase_media_title',
    descriptionKey: 'landing_usecase_media_desc',
    accent: 'amber',
  },
];
