/**
 * StreamPerformanceCard Component
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * Карточка для отображения метрик производительности потока.
 * Показывает аптайм, буферизацию и индикаторы качества.
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  Clock,
  Activity,
  Signal,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { StreamPerformanceResponse } from '@/types/analytics';

interface StreamPerformanceCardProps {
  /** Данные производительности потока */
  data: StreamPerformanceResponse | null;
  /** Загрузка данных */
  loading?: boolean;
}

/**
 * Определяет цвет индикатора на основе процента
 */
const getStatusColor = (percentage: number, type: 'uptime' | 'buffering'): string => {
  if (type === 'uptime') {
    if (percentage >= 99) return 'text-emerald-500';
    if (percentage >= 95) return 'text-amber-500';
    return 'text-rose-500';
  } else {
    // buffering - lower is better
    if (percentage <= 1) return 'text-emerald-500';
    if (percentage <= 3) return 'text-amber-500';
    return 'text-rose-500';
  }
};

/**
 * Определяет иконку статуса качества
 */
const getQualityIcon = (quality: string) => {
  const qualityLower = quality.toLowerCase();
  if (qualityLower.includes('high') || qualityLower.includes('высокое')) {
    return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
  }
  if (qualityLower.includes('medium') || qualityLower.includes('среднее')) {
    return <Activity className="w-4 h-4 text-amber-500" />;
  }
  return <AlertTriangle className="w-4 h-4 text-rose-500" />;
};

export const StreamPerformanceCard: React.FC<StreamPerformanceCardProps> = ({
  data,
  loading = false,
}) => {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`
          relative overflow-hidden rounded-2xl p-6
          bg-[color:var(--color-panel)]
          border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
          shadow-md shadow-black/5
        `}
      >
        <div className="space-y-6">
          <div className="h-6 w-48 bg-[color:var(--color-border)] rounded animate-pulse" />
          <div className="space-y-4">
            <div className="h-16 w-full bg-[color:var(--color-border)] rounded animate-pulse" />
            <div className="h-16 w-full bg-[color:var(--color-border)] rounded animate-pulse" />
            <div className="h-16 w-full bg-[color:var(--color-border)] rounded animate-pulse" />
          </div>
        </div>
      </motion.div>
    );
  }

  if (!data) {
    return null;
  }

  const uptimeColor = getStatusColor(data.uptime_percentage, 'uptime');
  const bufferingColor = getStatusColor(data.average_buffering_percentage, 'buffering');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative overflow-hidden rounded-2xl p-6
        bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
      `}
    >
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-1">
          Производительность потока
        </h3>
        <p className="text-sm text-[color:var(--color-text-muted)]">
          Качество трансляции и стабильность
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="space-y-4">
        {/* Uptime */}
        <div className="flex items-center justify-between p-4 rounded-xl bg-violet-500/5 border border-violet-500/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-500/10">
              <Clock className="w-5 h-5 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-[color:var(--color-text-muted)]">
                Аптайм
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {data.uptime_hours.toFixed(1)} ч. за период
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-bold ${uptimeColor}`}>
              {data.uptime_percentage.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Buffering */}
        <div className="flex items-center justify-between p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Activity className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-[color:var(--color-text-muted)]">
                Буферизация
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                Среднее значение
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-bold ${bufferingColor}`}>
              {data.average_buffering_percentage.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Quality Indicators */}
        <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Signal className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <p className="text-sm font-medium text-[color:var(--color-text-muted)]">
                Качество потока
              </p>
            </div>
            {getQualityIcon(data.current_quality)}
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                Текущее качество
              </p>
              <p className="text-lg font-semibold text-[color:var(--color-text)]">
                {data.current_quality}
              </p>
            </div>

            {data.bandwidth_usage_mbps && (
              <div className="text-right">
                <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                  Пропускная способность
                </p>
                <p className="text-lg font-semibold text-[color:var(--color-text)]">
                  {data.bandwidth_usage_mbps.toFixed(1)} Mbps
                </p>
              </div>
            )}
          </div>

          {data.quality_changes_count > 0 && (
            <div className="mt-3 pt-3 border-t border-[color:var(--color-border)]">
              <div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                <TrendingUp className="w-3 h-3" />
                <span>
                  Изменений качества: <span className="font-medium text-[color:var(--color-text)]">{data.quality_changes_count}</span>
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Quality Distribution Mini */}
        {data.quality_distribution && data.quality_distribution.length > 0 && (
          <div className="pt-2">
            <p className="text-xs text-[color:var(--color-text-muted)] mb-2">
              Распределение по качеству:
            </p>
            <div className="flex flex-wrap gap-2">
              {data.quality_distribution.slice(0, 4).map((item) => (
                <div
                  key={item.quality}
                  className="px-3 py-1 rounded-full bg-[color:var(--color-border)] text-xs"
                >
                  <span className="text-[color:var(--color-text-muted)]">{item.quality}:</span>{' '}
                  <span className="font-medium text-[color:var(--color-text)]">{item.percentage.toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default StreamPerformanceCard;
