/**
 * Recommendations Page
 * Feature: 014-ai-powered-content-recommendations
 *
 * Страница рекомендаций в админ-панели.
 * Отображает:
 * - Сводные метрики (карточки)
 * - Список рекомендаций с обратной связью
 * - Статистику качества рекомендаций
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, RefreshCw, TrendingUp, Clock, ThumbsUp, BarChart3 } from 'lucide-react';
import { RecommendationCard } from '../../components/recommendations';
import { AppLayout } from '../../components/layout';
import * as recommendationsApi from '../../api/recommendations';
import type {
  RecommendationAlgorithm,
  RecommendationResponse,
  RecommendationStatsResponse,
} from '../../types/recommendations';

const algorithmOptions: { value: RecommendationAlgorithm; label: string }[] = [
  { value: 'collaborative_filtering', label: 'Коллаборативная' },
  { value: 'content_based', label: 'По содержанию' },
  { value: 'hybrid', label: 'Гибридная' },
];

const Recommendations: React.FC = () => {
  const [algorithm, setAlgorithm] = useState<RecommendationAlgorithm>('hybrid');
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [stats, setStats] = useState<RecommendationStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [recommendationsData, statsData] = await Promise.all([
        recommendationsApi.getRecommendations({ algorithm, limit: 10 }),
        recommendationsApi.getRecommendationStats('7d'),
      ]);

      setRecommendations(recommendationsData);
      setStats(statsData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch recommendations:', err);
      setError('Не удалось загрузить данные рекомендаций');
    } finally {
      setLoading(false);
    }
  }, [algorithm]);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatSeconds = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)} сек`;
    }
    const minutes = Math.floor(seconds / 60);
    return `${minutes} мин`;
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
              Рекомендации
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
              AI-рекомендации контента на основе предпочтений пользователей
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Algorithm Selector */}
            <div className="flex items-center gap-2 rounded-2xl p-1 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-sm shadow-black/5">
              <Sparkles className="w-4 h-4 text-[color:var(--color-text-muted)] ml-2" />
              {algorithmOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setAlgorithm(option.value)}
                  className={`
                    px-3 py-1.5 text-sm font-medium rounded-xl transition-colors duration-300
                    ${algorithm === option.value
                      ? 'bg-[color:var(--color-accent)] text-white'
                      : 'text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)]'
                    }
                  `}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {/* Refresh Button */}
            <button
              onClick={fetchData}
              disabled={loading}
              className={`
                p-2 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
                text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)]
                transition-colors duration-300 disabled:opacity-50
                ${loading ? 'animate-spin' : ''}
              `}
              title="Обновить"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </motion.div>

        {/* Error State */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl p-4 bg-red-500/10 border border-red-500/20 text-red-300"
          >
            {error}
          </motion.div>
        )}

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="CTR рекомендаций"
            value={stats ? formatPercentage(stats.quality_metrics.click_through_rate) : '0%'}
            subtitle="Доля кликов по рекомендациям"
            icon={TrendingUp}
            color="emerald"
            loading={loading}
          />
          <MetricCard
            title="Среднее время просмотра"
            value={stats ? formatSeconds(stats.quality_metrics.average_watch_time_seconds) : '0 сек'}
            subtitle="Средняя длительность сессии"
            icon={Clock}
            color="blue"
            loading={loading}
          />
          <MetricCard
            title="Положительная обратная связь"
            value={stats ? formatPercentage(stats.quality_metrics.feedback_positive_rate) : '0%'}
            subtitle="Доля лайков от всех отзывов"
            icon={ThumbsUp}
            color="violet"
            loading={loading}
          />
          <MetricCard
            title="Всего рекомендаций"
            value={stats ? formatNumber(stats.quality_metrics.total_recommendations_shown) : '0'}
            subtitle={`Взаимодействий: ${stats ? formatNumber(stats.quality_metrics.total_interactions) : 0}`}
            icon={BarChart3}
            color="amber"
            loading={loading}
          />
        </div>

        {/* Recommendations List */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-[color:var(--color-text)]">
            Рекомендуемый контент
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {loading ? (
              // Skeleton loaders
              Array.from({ length: 4 }).map((_, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="rounded-2xl p-5 bg-[color:var(--color-panel)] border border-[color:var(--color-border)]"
                >
                  <RecommendationCard
                    recommendation={{
                      playlist_item_id: 'skeleton',
                      title: 'Загрузка...',
                      artist: 'Загрузка...',
                      score: 0,
                      algorithm: 'hybrid',
                    }}
                    loading={true}
                  />
                </motion.div>
              ))
            ) : recommendations && recommendations.recommendations.length > 0 ? (
              recommendations.recommendations.map((item, index) => (
                <motion.div
                  key={item.playlist_item_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <RecommendationCard recommendation={item} />
                </motion.div>
              ))
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="col-span-1 md:col-span-2 rounded-2xl p-8 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center"
              >
                <p className="text-[color:var(--color-text-muted)]">
                  Рекомендации暂时 недоступны. Недостаточно данных для генерации рекомендаций.
                </p>
              </motion.div>
            )}
          </div>
        </div>

        {/* Last Updated */}
        {lastUpdated && (
          <div className="text-center text-xs text-[color:var(--color-text-muted)]">
            Последнее обновление: {lastUpdated.toLocaleTimeString('ru-RU')}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

// Simple MetricCard component for stats display
interface MetricCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'emerald' | 'blue' | 'violet' | 'amber';
  loading: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  loading,
}) => {
  const colorConfig = {
    emerald: {
      gradient: 'from-emerald-500/10 to-green-500/10',
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-500/20',
    },
    blue: {
      gradient: 'from-blue-500/10 to-indigo-500/10',
      bg: 'bg-blue-500/10',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-500/20',
    },
    violet: {
      gradient: 'from-violet-500/10 to-purple-500/10',
      bg: 'bg-violet-500/10',
      text: 'text-violet-600 dark:text-violet-400',
      border: 'border-violet-500/20',
    },
    amber: {
      gradient: 'from-amber-500/10 to-orange-500/10',
      bg: 'bg-amber-500/10',
      text: 'text-amber-600 dark:text-amber-400',
      border: 'border-amber-500/20',
    },
  };

  const theme = colorConfig[color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative overflow-hidden rounded-2xl p-5
        bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
      `}
    >
      {/* Gradient Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${theme.gradient}`} />

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          {/* Icon */}
          <div className={`p-2.5 rounded-xl ${theme.bg}`}>
            <Icon className={`w-5 h-5 ${theme.text}`} />
          </div>
        </div>

        {/* Value */}
        <div className="space-y-1">
          {loading ? (
            <>
              <div className="h-7 w-20 bg-[color:var(--color-border)] rounded animate-pulse" />
              <div className="h-4 w-full bg-[color:var(--color-border)] rounded animate-pulse" />
            </>
          ) : (
            <>
              <div className={`text-2xl font-bold ${theme.text}`}>
                {value}
              </div>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {subtitle}
              </p>
            </>
          )}
        </div>

        {/* Title */}
        <p className="text-sm font-medium text-[color:var(--color-text-muted)] mt-3">
          {title}
        </p>
      </div>
    </motion.div>
  );
};

export default Recommendations;
