/**
 * RealtimeViewersChart Component
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * График зрителей в реальном времени с обновлением через WebSocket.
 */

import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { motion } from 'framer-motion';
import { Eye, Activity } from 'lucide-react';
import { useAnalyticsWebSocket } from '../../hooks/useAnalyticsWebSocket';
import type { ListenerHistoryPoint } from '../../types/analytics';

interface RealtimeViewersChartProps {
  /** Исторические данные для инициализации графика */
  initialData: ListenerHistoryPoint[];
  /** Максимальное количество точек для отображения (default: 30) */
  maxDataPoints?: number;
}

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export const RealtimeViewersChart: React.FC<RealtimeViewersChartProps> = ({
  initialData,
  maxDataPoints = 30,
}) => {
  const { listenerStats, isConnected, lastUpdate } = useAnalyticsWebSocket();
  const [chartData, setChartData] = useState<ListenerHistoryPoint[]>(initialData);

  // Обновляем график при получении новых данных через WebSocket
  useEffect(() => {
    if (listenerStats && lastUpdate) {
      const newPoint: ListenerHistoryPoint = {
        timestamp: lastUpdate.toISOString(),
        count: listenerStats.current,
      };

      setChartData(prev => {
        const updated = [...prev, newPoint];
        // Ограничиваем количество точек
        return updated.slice(-maxDataPoints);
      });
    }
  }, [listenerStats, lastUpdate, maxDataPoints]);

  // Обновляем данные при изменении initialData
  useEffect(() => {
    setChartData(initialData);
  }, [initialData]);

  // Подготавливаем данные для графика
  const transformedData = chartData.map(point => ({
    ...point,
    time: formatTime(point.timestamp),
    displayLabel: formatTime(point.timestamp),
  }));

  const currentViewers = listenerStats?.current ?? chartData[chartData.length - 1]?.count ?? 0;
  const peakViewers = listenerStats?.peak_today ?? Math.max(...chartData.map(d => d.count), 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-lg"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-500/10 rounded-xl">
            <Eye className="w-5 h-5 text-green-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Зрители в реальном времени
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Текущее количество зрителей
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Activity
            className={`w-4 h-4 ${
              isConnected ? 'text-green-500 animate-pulse' : 'text-gray-400'
            }`}
          />
          <span className={`text-xs font-medium ${
            isConnected ? 'text-green-500' : 'text-gray-400'
          }`}>
            {isConnected ? 'В эфире' : 'Отключено'}
          </span>
        </div>
      </div>

      {/* Метрики */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border border-green-200 dark:border-green-800">
          <p className="text-sm text-green-600 dark:text-green-400 font-medium mb-1">
            Сейчас смотрят
          </p>
          <p className="text-3xl font-bold text-green-700 dark:text-green-300">
            {currentViewers}
          </p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">
            Пик сегодня
          </p>
          <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">
            {peakViewers}
          </p>
        </div>
      </div>

      {/* График */}
      <div className="h-64">
        {transformedData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={transformedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorViewers" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
              <XAxis
                dataKey="displayLabel"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
                axisLine={{ stroke: '#E5E7EB' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
                axisLine={{ stroke: '#E5E7EB' }}
                tickLine={false}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(17, 24, 39, 0.9)',
                  border: 'none',
                  borderRadius: '0.75rem',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                labelStyle={{ color: '#9CA3AF' }}
                itemStyle={{ color: '#10B981' }}
                formatter={(value) => {
                  const numericValue =
                    typeof value === 'number' ? value : Number(value ?? 0);
                  const safeValue = Number.isFinite(numericValue) ? numericValue : 0;
                  return [`${safeValue} зрителей`, 'Количество'];
                }}
                labelFormatter={(label) => label}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#10B981"
                strokeWidth={2}
                fill="url(#colorViewers)"
                animationDuration={500}
                isAnimationActive={true}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
            Ожидание данных...
          </div>
        )}
      </div>

      {/* Последнее обновление */}
      {lastUpdate && (
        <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
          Последнее обновление: {formatTime(lastUpdate.toISOString())}
        </div>
      )}
    </motion.div>
  );
};

export default RealtimeViewersChart;
