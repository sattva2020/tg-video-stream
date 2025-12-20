/**
 * Analytics Page
 * Feature: 021-admin-analytics-menu
 * 
 * Страница аналитики в админ-панели.
 * Отображает:
 * - Сводные метрики (карточки)
 * - График истории слушателей
 * - Таблица топ треков
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Users, Play, Clock, Music, RefreshCw, Calendar } from 'lucide-react';
import { MetricCard, ListenersChart, TopTracksTable } from '../../components/analytics';
import { ResponsiveHeader } from '../../components/layout';
import * as analyticsApi from '../../api/analytics';
import type {
  AnalyticsPeriod,
  AnalyticsSummaryResponse,
  ListenerHistoryResponse,
  TopTracksResponse,
} from '../../types/analytics';

const periodOptions: { value: AnalyticsPeriod; label: string }[] = [
  { value: '7d', label: '7 дней' },
  { value: '30d', label: '30 дней' },
  { value: '90d', label: '90 дней' },
  { value: 'all', label: 'Всё время' },
];

const Analytics: React.FC = () => {
  const [period, setPeriod] = useState<AnalyticsPeriod>('7d');
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [history, setHistory] = useState<ListenerHistoryResponse | null>(null);
  const [topTracks, setTopTracks] = useState<TopTracksResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryData, historyData, tracksData] = await Promise.all([
        analyticsApi.getSummary(period),
        analyticsApi.getListenerHistory(period, 'day'),
        analyticsApi.getTopTracks(period, 5),
      ]);

      setSummary(summaryData);
      setHistory(historyData);
      setTopTracks(tracksData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
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

  const formatHours = (hours: number): string => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} мин`;
    }
    return `${hours.toFixed(1)} ч`;
  };

  return (
    <>
      <ResponsiveHeader />
      <main className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
          >
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
              Аналитика
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
              Статистика вещания и слушателей
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
            title="Слушатели сейчас"
            value={summary?.listeners.current ?? 0}
            subtitle={`Пик сегодня: ${summary?.listeners.peak_today ?? 0}`}
            icon={Users}
            color="blue"
            loading={loading}
          />
          <MetricCard
            title="Всего воспроизведений"
            value={summary?.total_plays ?? 0}
            subtitle={`За ${periodOptions.find(p => p.value === period)?.label}`}
            icon={Play}
            color="emerald"
            loading={loading}
          />
          <MetricCard
            title="Время вещания"
            value={summary ? formatHours(summary.total_duration_hours) : '0 ч'}
            subtitle={`Уникальных треков: ${summary?.unique_tracks ?? 0}`}
            icon={Clock}
            color="amber"
            loading={loading}
          />
          <MetricCard
            title="Пик за неделю"
            value={summary?.listeners.peak_week ?? 0}
            subtitle={`Среднее: ${summary?.listeners.average_week.toFixed(1) ?? 0}`}
            icon={Music}
            color="violet"
            loading={loading}
          />
        </div>

        {/* Charts and Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ListenersChart
            data={history?.data ?? []}
            loading={loading}
          />
          <TopTracksTable
            tracks={topTracks?.tracks ?? []}
            loading={loading}
          />
        </div>

        {/* Last Updated */}
        {lastUpdated && (
          <div className="text-center text-xs text-[color:var(--color-text-muted)]">
            Последнее обновление: {lastUpdated.toLocaleTimeString('ru-RU')}
          </div>
        )}
      </div>
    </main>
    </>
  );
};

export default Analytics;
