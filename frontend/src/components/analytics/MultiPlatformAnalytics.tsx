/**
 * MultiPlatformAnalytics Component
 * Feature: 021-social-media-integration-cross-platform-broadcasti
 *
 * Дашборд с объединённой аналитикой по всем платформам.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Broadcast,
  Clock,
  Send,
  TrendingUp,
  Calendar,
  RefreshCw,
  Video,
  Youtube,
  Gamepad2,
  AtSign,
  MessageCircle,
  Radio,
} from 'lucide-react';
import { Card, CardBody, CardHeader, Button, Chip } from '@heroui/react';
import { MetricCard } from './MetricCard';
import { AppLayout } from '../layout';
import * as analyticsApi from '../../api/analytics';
import type {
  AnalyticsPeriod,
  MultiPlatformAnalyticsResponse,
  PlatformMetrics,
} from '../../types/analytics';
import { useTranslation } from 'react-i18next';

const periodOptions: { value: AnalyticsPeriod; label: string }[] = [
  { value: '7d', label: '7 дней' },
  { value: '30d', label: '30 дней' },
  { value: '90d', label: '90 дней' },
  { value: 'all', label: 'Всё время' },
];

const platformIcons: Record<string, React.ElementType> = {
  youtube: Youtube,
  twitch: Gamepad2,
  twitter: AtSign,
  discord: MessageCircle,
  custom_rtmp: Radio,
};

const platformColors: Record<string, string> = {
  youtube: 'text-red-500',
  twitch: 'text-purple-500',
  twitter: 'text-sky-500',
  discord: 'text-indigo-500',
  custom_rtmp: 'text-gray-500',
};

const platformBackgrounds: Record<string, string> = {
  youtube: 'bg-red-500/10',
  twitch: 'bg-purple-500/10',
  twitter: 'bg-sky-500/10',
  discord: 'bg-indigo-500/10',
  custom_rtmp: 'bg-gray-500/10',
};

const formatHours = (hours: number): string => {
  if (hours < 1) {
    return `${Math.round(hours * 60)} мин`;
  }
  return `${hours.toFixed(1)} ч`;
};

const formatDate = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 60) {
    return `${diffMins} мин назад`;
  } else if (diffHours < 24) {
    return `${diffHours} ч назад`;
  } else if (diffDays < 7) {
    return `${diffDays} дн. назад`;
  }
  return date.toLocaleDateString('ru-RU');
};

export const MultiPlatformAnalytics: React.FC = () => {
  const { t } = useTranslation();
  const [period, setPeriod] = useState<AnalyticsPeriod>('7d');
  const [analytics, setAnalytics] = useState<MultiPlatformAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await analyticsApi.getMultiPlatformAnalytics(period);
      setAnalytics(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError('Не удалось загрузить данные аналитики');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getPlatformStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'inactive': return 'default';
      case 'error': return 'danger';
      default: return 'default';
    }
  };

  const getPlatformStatusLabel = (status: string) => {
    switch (status) {
      case 'active': return 'Активна';
      case 'inactive': return 'Неактивна';
      case 'error': return 'Ошибка';
      default: return status;
    }
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
              Мультиплатформенная аналитика
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
              Объединённая статистика по всем платформам
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Period Selector */}
            <div className="flex items-center gap-2 rounded-2xl p-1 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-sm shadow-black/5">
              <Calendar className="w-4 h-4 text-[color:var(--color-text-muted)] ml-2" />
              {periodOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setPeriod(option.value)}
                  className={`
                    px-3 py-1.5 text-sm font-medium rounded-xl transition-colors duration-300
                    ${period === option.value
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
            title="Активные платформы"
            value={analytics?.active_platforms ?? 0}
            subtitle={`Всего: ${analytics?.total_platforms ?? 0}`}
            icon={Broadcast}
            color="blue"
            loading={loading}
          />
          <MetricCard
            title="Всего стримов"
            value={analytics?.total_streams ?? 0}
            subtitle={`За ${periodOptions.find(p => p.value === period)?.label}`}
            icon={Video}
            color="emerald"
            loading={loading}
          />
          <MetricCard
            title="Время стриминга"
            value={analytics ? formatHours(analytics.total_stream_hours) : '0 ч'}
            subtitle="Суммарно по всем платформам"
            icon={Clock}
            color="amber"
            loading={loading}
          />
          <MetricCard
            title="Соц. сети посты"
            value={analytics?.total_posts ?? 0}
            subtitle={`Успешность: ${analytics?.successful_posts_rate.toFixed(1) ?? 0}%`}
            icon={Send}
            color="violet"
            loading={loading}
          />
        </div>

        {/* Platform Breakdown */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              Детализация по платформам
            </h3>
          </CardHeader>
          <CardBody>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-[color:var(--color-surface)] rounded-xl animate-pulse" />
                ))}
              </div>
            ) : !analytics?.platforms.length ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Broadcast className="w-12 h-12 text-[color:var(--color-text-muted)] mb-4" />
                <p className="text-[color:var(--color-text-muted)]">
                  Нет данных о платформах за выбранный период
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {analytics.platforms.map((platform: PlatformMetrics) => {
                  const Icon = platformIcons[platform.platform_type] || Video;
                  const iconColor = platformColors[platform.platform_type] || 'text-gray-500';
                  const iconBg = platformBackgrounds[platform.platform_type] || 'bg-gray-500/10';

                  return (
                    <motion.div
                      key={platform.platform_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-4 rounded-xl bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1">
                          <div className={`p-2 rounded-lg ${iconBg} ${iconColor}`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium text-[color:var(--color-text)]">
                                {platform.platform_name}
                              </h4>
                              <Chip
                                size="sm"
                                color={getPlatformStatusColor(platform.status) as any}
                                variant="flat"
                              >
                                {getPlatformStatusLabel(platform.status)}
                              </Chip>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                              <div>
                                <span className="text-[color:var(--color-text-muted)]">Стримы: </span>
                                <span className="font-medium text-[color:var(--color-text)]">
                                  {platform.stream_count}
                                </span>
                              </div>
                              <div>
                                <span className="text-[color:var(--color-text-muted)]">Время: </span>
                                <span className="font-medium text-[color:var(--color-text)]">
                                  {formatHours(platform.total_stream_hours)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[color:var(--color-text-muted)]">Посты: </span>
                                <span className="font-medium text-[color:var(--color-text)]">
                                  {platform.post_count}
                                </span>
                              </div>
                              {platform.last_activity && (
                                <div>
                                  <span className="text-[color:var(--color-text-muted)]">Активность: </span>
                                  <span className="font-medium text-[color:var(--color-text)]">
                                    {formatDate(platform.last_activity)}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        {platform.failed_posts > 0 && (
                          <div className="text-right">
                            <div className="text-xs text-[color:var(--color-text-muted)] mb-1">
                              Успешность постов
                            </div>
                            <div className="text-sm font-medium text-rose-500">
                              {((platform.successful_posts / platform.post_count) * 100).toFixed(1)}%
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>

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

export default MultiPlatformAnalytics;
