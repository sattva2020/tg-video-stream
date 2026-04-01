/**
 * PeakHoursChart Component
 * Feature: 015-smart-scheduling-auto-pilot-mode
 *
 * Тепловая карта пиковых часов с использованием Recharts.
 * Показывает engagement и количество слушателей по дням недели и часам.
 */

import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  Tooltip,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { motion } from 'framer-motion';
import { TrendingUp, Clock, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PeakHoursResponse, PeakHourData } from '../../api/scheduleAI';

// ==================== Types ====================

interface PeakHoursChartProps {
  data: PeakHoursResponse | null;
  loading?: boolean;
  error?: string | null;
}

interface HeatmapData {
  day: string;
  dayIndex: number;
  hour: number;
  hourLabel: string;
  listeners: number;
  engagement: number;
  isPeak: boolean;
}

// ==================== Constants ====================

const DAYS_OF_WEEK = [
  'Воскресенье',
  'Понедельник',
  'Вторник',
  'Среда',
  'Четверг',
  'Пятница',
  'Суббота',
];

const HOURS_OF_DAY = Array.from({ length: 24 }, (_, i) => i);

// ==================== Helper Functions ====================

function getEngagementColor(
  engagement: number,
  maxEngagement: number
): string {
  const ratio = engagement / maxEngagement;
  if (ratio > 0.8) return '#8B5CF6'; // violet - очень высокий
  if (ratio > 0.6) return '#3B82F6'; // blue - высокий
  if (ratio > 0.4) return '#06B6D4'; // cyan - средний
  if (ratio > 0.2) return '#10B981'; // emerald - ниже среднего
  return '#6B7280'; // gray - низкий
}

function getDayLabel(dayIndex: number): string {
  return DAYS_OF_WEEK[dayIndex];
}

function getHourLabel(hour: number): string {
  return `${hour}:00`;
}

// ==================== Sub-Components ====================

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  const { t } = useTranslation();

  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-gray-700">
      <p className="text-sm font-semibold text-white mb-2">
        {data.dayLabel}, {data.hourLabel}
      </p>
      <div className="space-y-1">
        <p className="text-xs text-gray-300">
          <span className="text-gray-400">Слушатели:</span>{' '}
          <span className="font-semibold text-white">{data.listeners}</span>
        </p>
        <p className="text-xs text-gray-300">
          <span className="text-gray-400">Engagement:</span>{' '}
          <span className="font-semibold text-white">{data.engagement.toFixed(1)}</span>
        </p>
        {data.isPeak && (
          <p className="text-xs font-semibold text-violet-400 mt-1">
            ⭐ Пиковый час
          </p>
        )}
      </div>
    </div>
  );
};

const SummaryCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
}> = ({ icon, label, value, color }) => (
  <div className="flex items-center gap-3 p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
    <div className={`p-2 rounded-lg ${color}`}>{icon}</div>
    <div className="flex-1">
      <p className="text-xs text-[color:var(--color-text-muted)]">{label}</p>
      <p className="text-lg font-bold text-[color:var(--color-text)]">{value}</p>
    </div>
  </div>
);

// ==================== Main Component ====================

export const PeakHoursChart: React.FC<PeakHoursChartProps> = ({
  data,
  loading = false,
  error = null,
}) => {
  const { t } = useTranslation();

  // Transform data into heatmap format
  const { heatmapData, maxEngagement } = useMemo(() => {
    if (!data?.peak_hours) {
      return { heatmapData: [], maxEngagement: 1 };
    }

    // Create a matrix of day x hour
    const matrix: HeatmapData[] = [];

    // Initialize all cells with zero values
    for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
      for (const hour of HOURS_OF_DAY) {
        matrix.push({
          day: getDayLabel(dayIndex),
          dayIndex,
          hour,
          hourLabel: getHourLabel(hour),
          listeners: 0,
          engagement: 0,
          isPeak: false,
        });
      }
    }

    // Fill with actual data
    let maxEng = 0;
    data.peak_hours.forEach((item: PeakHourData) => {
      const cellIndex = item.day_of_week * 24 + item.hour;
      if (matrix[cellIndex]) {
        matrix[cellIndex] = {
          day: getDayLabel(item.day_of_week),
          dayIndex: item.day_of_week,
          hour: item.hour,
          hourLabel: getHourLabel(item.hour),
          listeners: item.avg_listeners,
          engagement: item.engagement_score,
          isPeak: item.engagement_score > 0,
        };
        maxEng = Math.max(maxEng, item.engagement_score);
      }
    });

    return { heatmapData: matrix, maxEngagement: maxEng || 1 };
  }, [data]);

  // Loading State
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] shadow-lg"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('schedule.peakHours.title', 'Пиковые часы')}
            </h3>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.peakHours.description', 'Аналитика активности слушателей')}
            </p>
          </div>
        </div>
        <div className="h-96 flex items-center justify-center">
          <div className="w-full h-full bg-[color:var(--color-surface-muted)] rounded animate-pulse" />
        </div>
      </motion.div>
    );
  }

  // Error State
  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] shadow-lg"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 shadow-lg shadow-rose-500/25">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('schedule.peakHours.title', 'Пиковые часы')}
            </h3>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.peakHours.description', 'Аналитика активности слушателей')}
            </p>
          </div>
        </div>
        <div className="h-96 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 font-semibold mb-2">
              {t('schedule.peakHours.error', 'Ошибка загрузки данных')}
            </p>
            <p className="text-sm text-[color:var(--color-text-muted)]">{error}</p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Empty State
  if (!data || !data.peak_hours || data.peak_hours.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] shadow-lg"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('schedule.peakHours.title', 'Пиковые часы')}
            </h3>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.peakHours.description', 'Аналитика активности слушателей')}
            </p>
          </div>
        </div>
        <div className="h-96 flex items-center justify-center">
          <div className="text-center">
            <Clock className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
            <p className="text-[color:var(--color-text-muted)]">
              {t('schedule.peakHours.noData', 'Нет данных за выбранный период')}
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Main Chart
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] shadow-lg"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('schedule.peakHours.title', 'Пиковые часы')}
          </h3>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            {t('schedule.peakHours.description', 'Аналитика активности слушателей')}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[color:var(--color-text-muted)]">
            {t('schedule.peakHours.period', 'Период')}:
          </p>
          <p className="text-sm font-semibold text-[color:var(--color-text)]">
            {data.period}
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      {data.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <SummaryCard
            icon={<Users className="w-5 h-5 text-violet-500" />}
            label={t('schedule.peakHours.bestDay', 'Лучший день')}
            value={DAYS_OF_WEEK[data.summary.best_day]}
            color="bg-violet-500/10"
          />
          <SummaryCard
            icon={<Clock className="w-5 h-5 text-blue-500" />}
            label={t('schedule.peakHours.bestHour', 'Лучший час')}
            value={`${data.summary.best_hour}:00`}
            color="bg-blue-500/10"
          />
          <SummaryCard
            icon={<TrendingUp className="w-5 h-5 text-emerald-500" />}
            label={t('schedule.peakHours.avgEngagement', 'Средний engagement')}
            value={data.summary.avg_engagement.toFixed(1)}
            color="bg-emerald-500/10"
          />
          <SummaryCard
            icon={<Users className="w-5 h-5 text-amber-500" />}
            label={t('schedule.peakHours.totalSamples', 'Всего записей')}
            value={data.summary.total_samples}
            color="bg-amber-500/10"
          />
        </div>
      )}

      {/* Heatmap */}
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          {/* Custom heatmap implementation using simple divs */}
          <div className="w-full h-full relative">
            <div className="absolute inset-0 flex flex-col">
              {/* Day labels */}
              <div className="flex flex-col justify-between py-8 pr-2">
                {DAYS_OF_WEEK.map((day, index) => (
                  <div
                    key={day}
                    className="text-xs text-[color:var(--color-text-muted)] text-right h-10 flex items-center justify-end"
                    style={{ transform: 'translateY(-50%)' }}
                  >
                    {day}
                  </div>
                ))}
              </div>

              {/* Heatmap grid */}
              <div className="flex-1 ml-2 grid grid-rows-7 gap-1">
                {DAYS_OF_WEEK.map((_, dayIndex) => (
                  <div key={dayIndex} className="grid grid-cols-24 gap-1">
                    {HOURS_OF_DAY.map((hour) => {
                      const cellData = heatmapData.find(
                        (d) => d.dayIndex === dayIndex && d.hour === hour
                      );
                      const color = cellData
                        ? getEngagementColor(cellData.engagement, maxEngagement)
                        : '#374151';

                      return (
                        <div
                          key={`${dayIndex}-${hour}`}
                          className="relative aspect-square rounded-sm hover:ring-2 hover:ring-white transition-all cursor-pointer"
                          style={{
                            backgroundColor: color,
                            opacity: cellData?.engagement ? 0.3 + (cellData.engagement / maxEngagement) * 0.7 : 0.1,
                          }}
                          title={`${getDayLabel(dayIndex)} ${getHourLabel(hour)}: ${cellData?.listeners || 0} слушателей`}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>

            {/* Hour labels at bottom */}
            <div className="absolute bottom-0 left-0 right-0 flex justify-between px-10 pt-2">
              {HOURS_OF_DAY.filter((h) => h % 3 === 0).map((hour) => (
                <div
                  key={hour}
                  className="text-xs text-[color:var(--color-text-muted)]"
                >
                  {hour}:00
                </div>
              ))}
            </div>
          </div>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="mt-6 flex items-center justify-center gap-4">
        <span className="text-xs text-[color:var(--color-text-muted)]">
          {t('schedule.peakHours.lowActivity', 'Низкая активность')}
        </span>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: '#6B7280', opacity: 0.3 }} />
          <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: '#10B981', opacity: 0.5 }} />
          <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: '#06B6D4', opacity: 0.6 }} />
          <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: '#3B82F6', opacity: 0.8 }} />
          <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: '#8B5CF6', opacity: 1 }} />
        </div>
        <span className="text-xs text-[color:var(--color-text-muted)]">
          {t('schedule.peakHours.highActivity', 'Высокая активность')}
        </span>
      </div>
    </motion.div>
  );
};

export default PeakHoursChart;
