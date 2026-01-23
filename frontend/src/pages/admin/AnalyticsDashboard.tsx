/**
 * AnalyticsDashboard Page
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * Comprehensive analytics dashboard with Real-time and Historical views.
 * Provides tabbed interface for different analytics perspectives.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, Calendar, Download, RefreshCw, Activity, Users, Play, Clock, Music } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../../components/layout';
import {
  MetricCard,
  ListenersChart,
  TopTracksTable,
  RealtimeViewersChart,
  StreamPerformanceCard,
  EngagementMetrics,
  ContentInsights,
  ExportReportDialog,
} from '../../components/analytics';
import * as analyticsApi from '../../api/analytics';
import type {
  AnalyticsPeriod,
  AnalyticsSummaryResponse,
  ListenerHistoryResponse,
  TopTracksResponse,
  EngagementMetricsResponse,
  StreamPerformanceResponse,
  ContentInsightsResponse,
  ListenerHistoryPoint,
} from '../../types/analytics';

const periodOptions: { value: AnalyticsPeriod; label: string }[] = [
  { value: '7d', label: '7 дней' },
  { value: '30d', label: '30 дней' },
  { value: '90d', label: '90 дней' },
  { value: 'all', label: 'Всё время' },
];

const AnalyticsDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'realtime' | 'historical'>('realtime');

  // Historical data state
  const [period, setPeriod] = useState<AnalyticsPeriod>('7d');
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [history, setHistory] = useState<ListenerHistoryResponse | null>(null);
  const [topTracks, setTopTracks] = useState<TopTracksResponse | null>(null);
  const [engagement, setEngagement] = useState<EngagementMetricsResponse | null>(null);
  const [streamPerf, setStreamPerf] = useState<StreamPerformanceResponse | null>(null);
  const [contentInsights, setContentInsights] = useState<ContentInsightsResponse | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch historical data
  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryData, historyData, tracksData, engagementData, streamData, contentData] =
        await Promise.all([
          analyticsApi.getSummary(period),
          analyticsApi.getListenerHistory(period, 'day'),
          analyticsApi.getTopTracks(period, 5),
          analyticsApi.getEngagement(period),
          analyticsApi.getStreamPerformance(period),
          analyticsApi.getContentInsights(period),
        ]);

      setSummary(summaryData);
      setHistory(historyData);
      setTopTracks(tracksData);
      setEngagement(engagementData);
      setStreamPerf(streamData);
      setContentInsights(contentData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError('Не удалось загрузить данные аналитики');
    } finally {
      setLoading(false);
    }
  }, [period]);

  // Initial load and auto-refresh
  useEffect(() => {
    if (activeTab === 'historical') {
      fetchHistoricalData();
      // Auto-refresh every 5 minutes
      const interval = setInterval(fetchHistoricalData, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [fetchHistoricalData, activeTab]);

  // Format helper
  const formatHours = (hours: number): string => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} мин`;
    }
    return `${hours.toFixed(1)} ч`;
  };

  // Tab items
  const tabItems = useMemo(
    () => [
      { key: 'realtime' as const, label: t('analytics.realtime', 'Реальное время') },
      { key: 'historical' as const, label: t('analytics.historical', 'Исторические данные') },
    ],
    [t]
  );

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-[color:var(--color-text)]">
                {t('analytics.dashboard', 'Аналитика')}
              </h1>
              <p className="text-sm text-[color:var(--color-text-muted)]">
                {t('analytics.subtitle', 'Статистика вещания и слушателей')}
              </p>
            </div>
          </div>

          {/* Actions for Historical Tab */}
          {activeTab === 'historical' && (
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
                      ${
                        period === option.value
                          ? 'bg-[color:var(--color-accent)] text-white'
                          : 'text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)]'
                      }
                    `}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              {/* Export Dialog */}
              <ExportReportDialog
                trigger={
                  <button
                    className="px-4 py-2 rounded-2xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-300 flex items-center gap-2 shadow-sm shadow-black/5"
                    title="Export analytics"
                  >
                    <Download className="w-4 h-4" />
                    <span className="hidden sm:inline">Export</span>
                  </button>
                }
                onExport={async (options) => {
                  console.log('Exporting analytics:', options);
                }}
                onSchedule={async (options) => {
                  console.log('Scheduling report:', options);
                }}
              />

              {/* Refresh Button */}
              <button
                onClick={fetchHistoricalData}
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
          )}
        </motion.div>

        {/* Tabs */}
        <div className="mt-3 sm:mt-4 mb-5">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {tabItems.map((item) => {
              const isActive = activeTab === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveTab(item.key)}
                  className={`px-3 sm:px-4 py-2 text-sm font-medium rounded-full transition-all border
                    ${
                      isActive
                        ? 'bg-[color:var(--color-accent)]/15 border-[color:var(--color-accent)] text-[color:var(--color-accent)] shadow-sm shadow-[color:var(--color-accent)]/30'
                        : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:border-[color:var(--color-border-strong)]'
                    }
                  `}
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="mt-3 sm:mt-4">
            {/* Real-time Tab */}
            {activeTab === 'realtime' && (
              <motion.div
                key="realtime"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                {/* Live indicator */}
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 w-fit">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                  </span>
                  <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    {t('analytics.liveData', 'Данные в реальном времени')}
                  </span>
                </div>

                {/* Real-time Viewers Chart */}
                <div className="grid lg:grid-cols-2 gap-6">
                  <RealtimeViewersChart
                    initialData={history?.data ?? []}
                    maxDataPoints={30}
                  />
                  <StreamPerformanceCard
                    data={streamPerf}
                    loading={loading}
                  />
                </div>

                {/* Engagement Metrics and Content Insights */}
                <div className="grid lg:grid-cols-2 gap-6">
                  <EngagementMetrics
                    data={engagement}
                    loading={loading}
                  />
                  <ContentInsights
                    mostWatched={contentInsights?.most_watched ?? []}
                    dropOffPoints={contentInsights?.drop_off_points ?? []}
                    averageCompletionRate={contentInsights?.average_completion_rate ?? 0}
                    loading={loading}
                  />
                </div>
              </motion.div>
            )}

            {/* Historical Tab */}
            {activeTab === 'historical' && (
              <motion.div
                key="historical"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
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
                    title={t('analytics.currentListeners', 'Слушатели сейчас')}
                    value={summary?.listeners.current ?? 0}
                    subtitle={`${t('analytics.peakToday', 'Пик сегодня')}: ${summary?.listeners.peak_today ?? 0}`}
                    icon={Users}
                    color="blue"
                    loading={loading}
                  />
                  <MetricCard
                    title={t('analytics.totalPlays', 'Всего воспроизведений')}
                    value={summary?.total_plays ?? 0}
                    subtitle={`${t('analytics.forPeriod', 'За')} ${periodOptions.find((p) => p.value === period)?.label}`}
                    icon={Play}
                    color="emerald"
                    loading={loading}
                  />
                  <MetricCard
                    title={t('analytics.streamTime', 'Время вещания')}
                    value={summary ? formatHours(summary.total_duration_hours) : '0 ч'}
                    subtitle={`${t('analytics.uniqueTracks', 'Уникальных треков')}: ${summary?.unique_tracks ?? 0}`}
                    icon={Clock}
                    color="amber"
                    loading={loading}
                  />
                  <MetricCard
                    title={t('analytics.peakWeek', 'Пик за неделю')}
                    value={summary?.listeners.peak_week ?? 0}
                    subtitle={`${t('analytics.average', 'Среднее')}: ${summary?.listeners.average_week.toFixed(1) ?? 0}`}
                    icon={Music}
                    color="violet"
                    loading={loading}
                  />
                </div>

                {/* Charts and Tables */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ListenersChart data={history?.data ?? []} loading={loading} />
                  <TopTracksTable tracks={topTracks?.tracks ?? []} loading={loading} />
                </div>

                {/* Last Updated */}
                {lastUpdated && (
                  <div className="text-center text-xs text-[color:var(--color-text-muted)]">
                    {t('analytics.lastUpdated', 'Последнее обновление')}: {lastUpdated.toLocaleTimeString('ru-RU')}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default AnalyticsDashboard;
