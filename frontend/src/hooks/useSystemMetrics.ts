/**
 * useSystemMetrics Hook
 * Spec: 015-real-system-monitoring
 * 
 * TanStack Query хук для получения системных метрик.
 * Автоматически обновляется каждые 30 секунд.
 */

import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../api/system';
import { METRIC_THRESHOLDS, getMetricStatus } from '../types/system';
import type { MetricStatus } from '../types/system';

/**
 * Query key для системных метрик.
 */
export const SYSTEM_METRICS_QUERY_KEY = ['system', 'metrics'] as const;

/**
 * Интервал автообновления метрик (30 секунд).
 */
export const METRICS_REFETCH_INTERVAL = 30 * 1000;

/**
 * Хук для получения системных метрик.
 * 
 * @example
 * ```tsx
 * function SystemHealth() {
 *   const { data, isLoading, error, cpuStatus } = useSystemMetrics();
 *   
 *   if (isLoading) return <Skeleton />;
 *   if (error) return <ErrorMessage />;
 *   
 *   return (
 *     <div>CPU: {data.cpu_percent}% ({cpuStatus})</div>
 *   );
 * }
 * ```
 */
export function useSystemMetrics() {
  const query = useQuery({
    queryKey: SYSTEM_METRICS_QUERY_KEY,
    queryFn: systemApi.getMetrics,
    staleTime: METRICS_REFETCH_INTERVAL / 2, // 15 секунд
    refetchInterval: METRICS_REFETCH_INTERVAL,
    refetchOnWindowFocus: true,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });

  // Вычисляем статусы метрик
  const cpuStatus: MetricStatus = query.data
    ? getMetricStatus(
        query.data.cpu_percent,
        METRIC_THRESHOLDS.cpu.warning,
        METRIC_THRESHOLDS.cpu.critical
      )
    : 'healthy';

  const ramStatus: MetricStatus = query.data
    ? getMetricStatus(
        query.data.ram_percent,
        METRIC_THRESHOLDS.ram.warning,
        METRIC_THRESHOLDS.ram.critical
      )
    : 'healthy';

  const diskStatus: MetricStatus = query.data
    ? getMetricStatus(
        query.data.disk_percent,
        METRIC_THRESHOLDS.disk.warning,
        METRIC_THRESHOLDS.disk.critical
      )
    : 'healthy';

  // Общий статус системы — worst case
  const overallStatus: MetricStatus = 
    cpuStatus === 'critical' || ramStatus === 'critical' || diskStatus === 'critical'
      ? 'critical'
      : cpuStatus === 'warning' || ramStatus === 'warning' || diskStatus === 'warning'
        ? 'warning'
        : 'healthy';

  return {
    ...query,
    // Алиасы для удобства
    metrics: query.data,
    // Вычисленные статусы
    cpuStatus,
    ramStatus,
    diskStatus,
    overallStatus,
    // Флаг критического состояния
    hasCriticalIssues: overallStatus === 'critical',
    hasWarnings: overallStatus === 'warning',
  };
}

/**
 * Возвращает только данные метрик (без статусов).
 * Полезно для компонентов, которым не нужны вычисления.
 */
export function useSystemMetricsData() {
  return useQuery({
    queryKey: SYSTEM_METRICS_QUERY_KEY,
    queryFn: systemApi.getMetrics,
    staleTime: METRICS_REFETCH_INTERVAL / 2,
    refetchInterval: METRICS_REFETCH_INTERVAL,
  });
}

export default useSystemMetrics;
