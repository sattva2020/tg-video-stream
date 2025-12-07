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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Аналитика
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Статистика вещания и слушателей
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Period Selector */}
            <div className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-xl p-1 border border-gray-200 dark:border-gray-700">
              <Calendar className="w-4 h-4 text-gray-400 ml-2" />
              {periodOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setPeriod(option.value)}
                  className={`
                    px-3 py-1.5 text-sm font-medium rounded-lg transition-all
                    ${period === option.value
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
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
                p-2 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700
                transition-all disabled:opacity-50
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
            className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-red-600 dark:text-red-400"
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
          <div className="text-center text-xs text-gray-400 dark:text-gray-500">
            Последнее обновление: {lastUpdated.toLocaleTimeString('ru-RU')}
          </div>
        )}
      </div>
    </div>
  );
};

export default Analytics;
