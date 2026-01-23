/**
 * SecurityMetrics Component
 * Feature: 025-advanced-security-compliance-features
 *
 * График истории событий безопасности с использованием Recharts.
 */

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';
import type { SecurityEventBucket } from '../../api/admin';

interface SecurityMetricsProps {
  data: SecurityEventBucket[];
  loading?: boolean;
}

const formatDate = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  });
};

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const SecurityMetrics: React.FC<SecurityMetricsProps> = ({
  data,
  loading = false,
}) => {
  // Transform data for Recharts
  const chartData = data.map((bucket) => ({
    ...bucket,
    date: formatDate(bucket.timestamp),
    time: formatTime(bucket.timestamp),
    displayLabel: formatDate(bucket.timestamp),
    critical: bucket.by_severity.critical || 0,
    high: bucket.by_severity.high || 0,
    medium: bucket.by_severity.medium || 0,
    low: bucket.by_severity.low || 0,
  }));

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-500/10 rounded-xl">
            <Shield className="w-5 h-5 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            История событий безопасности
          </h3>
        </div>
        <div className="h-64 flex items-center justify-center">
          <div className="w-full h-full bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        </div>
      </motion.div>
    );
  }

  if (!data.length) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-500/10 rounded-xl">
            <Shield className="w-5 h-5 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            История событий безопасности
          </h3>
        </div>
        <div className="h-64 flex items-center justify-center text-gray-500">
          Нет данных за выбранный период
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-lg"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-red-500/10 rounded-xl">
          <Shield className="w-5 h-5 text-red-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          История событий безопасности
        </h3>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#DC2626" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#F97316" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#EAB308" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
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
              formatter={(value, name) => {
                const numericValue = typeof value === 'number' ? value : Number(value ?? 0);
                const safeValue = Number.isFinite(numericValue) ? numericValue : 0;
                const labelMap: Record<string, string> = {
                  critical: 'Критические',
                  high: 'Высокие',
                  medium: 'Средние',
                  low: 'Низкие',
                  total_events: 'Всего событий',
                };
                return [`${safeValue}`, labelMap[name] || name];
              }}
              labelFormatter={(label) => label}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Area
              type="monotone"
              dataKey="critical"
              stackId="security"
              stroke="#DC2626"
              strokeWidth={2}
              fill="url(#colorCritical)"
              animationDuration={1000}
              name="Критические"
            />
            <Area
              type="monotone"
              dataKey="high"
              stackId="security"
              stroke="#F97316"
              strokeWidth={2}
              fill="url(#colorHigh)"
              animationDuration={1000}
              name="Высокие"
            />
            <Area
              type="monotone"
              dataKey="medium"
              stackId="security"
              stroke="#EAB308"
              strokeWidth={2}
              fill="url(#colorMedium)"
              animationDuration={1000}
              name="Средние"
            />
            <Area
              type="monotone"
              dataKey="low"
              stackId="security"
              stroke="#3B82F6"
              strokeWidth={2}
              fill="url(#colorLow)"
              animationDuration={1000}
              name="Низкие"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
};

export default SecurityMetrics;
