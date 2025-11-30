/**
 * System Monitoring Types
 * Spec: 015-real-system-monitoring
 * 
 * Типы для компонентов SystemHealth и ActivityTimeline
 */

// Статус метрики для визуальной индикации
export type MetricStatus = 'healthy' | 'warning' | 'critical';

// Метрики системы (реальные данные с сервера)
export interface SystemMetrics {
  cpu_percent: number;        // 0-100
  ram_percent: number;        // 0-100
  disk_percent: number;       // 0-100
  db_connections_active: number;
  db_connections_idle: number;
  uptime_seconds: number;
  collected_at: string;       // ISO 8601
}

// Типы событий активности
export type ActivityEventType =
  | 'user_login'
  | 'user_logout'
  | 'stream_start'
  | 'stream_stop'
  | 'stream_error'
  | 'track_added'
  | 'track_removed'
  | 'system_warning'
  | 'system_error'
  | 'playlist_updated';

// Событие активности
export interface ActivityEvent {
  id: number;
  type: ActivityEventType;
  message: string;
  user_email?: string;
  details?: Record<string, unknown>;
  created_at: string;         // ISO 8601
}

// Ответ API для списка событий
export interface ActivityEventsResponse {
  events: ActivityEvent[];
  total: number;
}

// Пороговые значения для метрик
export const METRIC_THRESHOLDS = {
  cpu: { warning: 70, critical: 90 },
  ram: { warning: 70, critical: 85 },
  disk: { warning: 70, critical: 90 },
} as const;

/**
 * Определяет статус метрики по пороговым значениям
 */
export function getMetricStatus(
  value: number,
  warningThreshold: number,
  criticalThreshold: number
): MetricStatus {
  if (value >= criticalThreshold) return 'critical';
  if (value >= warningThreshold) return 'warning';
  return 'healthy';
}

/**
 * Форматирует uptime в человекочитаемый формат
 */
export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}д ${hours}ч`;
  }
  if (hours > 0) {
    return `${hours}ч ${minutes}м`;
  }
  return `${minutes}м`;
}
