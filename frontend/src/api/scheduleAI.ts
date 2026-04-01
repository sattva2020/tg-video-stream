/**
 * API клиент для AI-функционала расписания.
 *
 * Функционал:
 * - AI-рекомендации для расписания
 * - Оптимизация расписания
 * - Автопилот (автоматическая генерация расписания)
 * - Анализ пиковых часов
 * - Обнаружение и разрешение конфликтов
 */

import { client } from './client';

// ==================== Types ====================

export type RecommendationType = 'content' | 'timing' | 'recurring' | 'gap_fill';
export type OptimizationStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface ScheduleRecommendation {
  id: string;
  channel_id: string;
  target_date: string;
  recommendation_type: RecommendationType;
  playlist_id?: string;
  playlist_name?: string;
  suggested_start_time?: string;
  suggested_end_time?: string;
  confidence_score: number;
  reason: string;
  estimated_engagement?: number;
  created_at: string;
}

export interface ScheduleRecommendationResponse {
  channel_id: string;
  target_date: string;
  recommendations: ScheduleRecommendation[];
  metadata: {
    total_recommendations: number;
    by_type: Record<RecommendationType, number>;
    avg_confidence: number;
  };
  generated_at: string;
}

export interface OptimizationParameters {
  prioritize_coverage: boolean;
  prioritize_variety: boolean;
  prioritize_peak_hours: boolean;
  maximize_engagement: boolean;
  avoid_conflicts: boolean;
  weights?: {
    coverage?: number;
    engagement?: number;
    variety?: number;
    conflicts?: number;
    peak_hours?: number;
  };
}

export interface OptimizationMetrics {
  coverage: number;
  engagement_score: number;
  variety_score: number;
  conflicts_count: number;
  peak_hours_coverage: number;
}

export interface ScheduleSuggestion {
  date: string;
  start_time: string;
  end_time: string;
  playlist_id?: string;
  playlist_name?: string;
  reason: string;
  priority: number;
}

export interface ScheduleOptimizationResponse {
  id: string;
  channel_id: string;
  start_date: string;
  end_date: string;
  status: OptimizationStatus;
  metrics: OptimizationMetrics;
  suggestions: ScheduleSuggestion[];
  parameters: OptimizationParameters;
  warnings?: string[];
  created_at: string;
}

export interface ScheduleOptimizationRequest {
  channel_id: string;
  start_date: string;
  end_date: string;
  parameters: OptimizationParameters;
}

export interface PeakHourData {
  day_of_week: number;
  hour: number;
  avg_listeners: number;
  play_count: number;
  peak_listeners: number;
  engagement_score: number;
}

export interface PeakHoursResponse {
  channel_id: string;
  period: string;
  peak_hours: PeakHourData[];
  summary: {
    best_day: number;
    best_hour: number;
    avg_engagement: number;
    total_samples: number;
  };
  generated_at: string;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface AutoPilotRequest {
  channel_id: string;
  date_range: DateRange;
  use_ai_recommendations: boolean;
  template_id?: string;
  max_daily_hours?: number;
  resolve_conflicts?: boolean;
}

export interface AutoPilotResponse {
  channel_id: string;
  date_range: DateRange;
  slots_created: number;
  gaps_filled: number;
  conflicts_resolved: number;
  status: 'completed' | 'partial' | 'failed';
  warnings?: string[];
  generated_at: string;
}

export interface ConflictInfo {
  slot_id: string;
  playlist_name: string;
  start_time: string;
  end_time: string;
  priority: number;
}

export interface ConflictGroup {
  date: string;
  time_range: string;
  conflicts: ConflictInfo[];
}

export interface ConflictDetectionResponse {
  channel_id: string;
  start_date: string;
  end_date: string;
  conflicts: ConflictGroup[];
  total_conflicts: number;
  affected_dates: number;
  analyzed_at: string;
}

export interface ConflictDetectionRequest {
  channel_id: string;
  start_date: string;
  end_date: string;
}

export interface AlternativeTimeSuggestion {
  start_time: string;
  end_time: string;
  reason: string;
}

export interface ConflictResolution {
  conflict_group: ConflictGroup;
  resolution: 'keep_highest_priority' | 'move' | 'delete';
  alternative_times?: AlternativeTimeSuggestion[];
}

export interface ConflictResolutionResponse {
  channel_id: string;
  date: string;
  resolutions_applied: number;
  slots_removed: number;
  slots_modified: number;
  remaining_conflicts: number;
  resolutions?: ConflictResolution[];
  resolved_at: string;
}

export interface GapInfo {
  date: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  is_peak_hour: boolean;
}

export interface GapDetectionResponse {
  channel_id: string;
  start_date: string;
  end_date: string;
  gaps: GapInfo[];
  total_gap_hours: number;
  peak_hours_gaps: number;
  analyzed_at: string;
}

export interface GapDetectionRequest {
  channel_id: string;
  start_date: string;
  end_date: string;
  consider_peak_hours?: boolean;
}

// ==================== API Functions ====================

export const scheduleAIApi = {
  /**
   * Получить AI-рекомендации для расписания
   */
  getRecommendations: async (
    channelId: string,
    date: string,
    params?: {
      recommendation_types?: RecommendationType[];
      max_recommendations?: number;
      min_confidence?: number;
    }
  ): Promise<ScheduleRecommendationResponse> => {
    const response = await client.get('/api/schedule-ai/recommendations', {
      params: {
        channel_id: channelId,
        date,
        recommendation_types: params?.recommendation_types,
        max_recommendations: params?.max_recommendations ?? 10,
        min_confidence: params?.min_confidence ?? 50.0,
      },
    });
    return response.data;
  },

  /**
   * Предпросмотр оптимизации расписания
   */
  previewOptimization: async (request: ScheduleOptimizationRequest): Promise<ScheduleOptimizationResponse> => {
    const response = await client.post('/api/schedule-ai/optimize/preview', request);
    return response.data;
  },

  /**
   * Сгенерировать расписание в режиме автопилота
   */
  generateAutoPilotSchedule: async (request: AutoPilotRequest): Promise<AutoPilotResponse> => {
    const response = await client.post('/api/schedule-ai/auto-pilot/generate', request);
    return response.data;
  },

  /**
   * Предпросмотр расписания автопилота без применения
   */
  previewAutoPilotSchedule: async (request: AutoPilotRequest): Promise<any> => {
    const response = await client.post('/api/schedule-ai/auto-pilot/preview', request);
    return response.data;
  },

  /**
   * Получить анализ пиковых часов
   */
  getPeakHours: async (
    channelId: string,
    period: string = '30d',
    minSampleSize: number = 7
  ): Promise<PeakHoursResponse> => {
    const response = await client.get('/api/schedule-ai/peak-hours', {
      params: {
        channel_id: channelId,
        period,
        min_sample_size: minSampleSize,
      },
    });
    return response.data;
  },

  /**
   * Обнаружить конфликты в расписании
   */
  detectConflicts: async (request: ConflictDetectionRequest): Promise<ConflictDetectionResponse> => {
    const response = await client.post('/api/schedule-ai/detect-conflicts', request);
    return response.data;
  },

  /**
   * Разрешить конфликты в расписании
   */
  resolveConflicts: async (request: ConflictDetectionRequest): Promise<ConflictResolutionResponse> => {
    const response = await client.post('/api/schedule-ai/resolve-conflicts', request);
    return response.data;
  },

  /**
   * Обнаружить пробелы в расписании
   */
  detectGaps: async (request: GapDetectionRequest): Promise<GapDetectionResponse> => {
    const response = await client.post('/api/schedule-ai/detect-gaps', request);
    return response.data;
  },
};

export default scheduleAIApi;
