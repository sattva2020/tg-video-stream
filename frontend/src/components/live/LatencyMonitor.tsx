/**
 * LatencyMonitor Component
 * Feature: 019-real-time-live-streaming-capabilities
 *
 * Компонент мониторинга задержки (latency) прямого эфира.
 * Показывает текущую задержку, исторические данные и статус качества соединения.
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Progress } from '@heroui/react';

export interface LatencyMonitorProps {
  currentLatency?: number;
  history?: number[];
  thresholdWarning?: number;
  thresholdCritical?: number;
  updateInterval?: number;
  className?: string;
}

type LatencyStatus = 'excellent' | 'good' | 'warning' | 'critical';

interface LatencyDataPoint {
  value: number;
  timestamp: number;
}

const getStatus = (
  latency: number,
  warningThreshold: number,
  criticalThreshold: number
): LatencyStatus => {
  if (latency >= criticalThreshold) return 'critical';
  if (latency >= warningThreshold) return 'warning';
  if (latency >= 100) return 'good';
  return 'excellent';
};

const getStatusColor = (status: LatencyStatus): string => {
  switch (status) {
    case 'excellent':
      return 'text-emerald-500';
    case 'good':
      return 'text-green-500';
    case 'warning':
      return 'text-amber-500';
    case 'critical':
      return 'text-rose-500';
    default:
      return 'text-gray-500';
  }
};

const getStatusBgColor = (status: LatencyStatus): string => {
  switch (status) {
    case 'excellent':
      return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/60 dark:border-emerald-500/40';
    case 'good':
      return 'bg-green-500/10 text-green-700 dark:text-green-300 border-green-200/60 dark:border-green-500/40';
    case 'warning':
      return 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/80 dark:border-amber-500/40';
    case 'critical':
      return 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200/80 dark:border-rose-500/40';
    default:
      return 'bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-200/80 dark:border-gray-500/40';
  }
};

const getStatusIcon = (status: LatencyStatus) => {
  switch (status) {
    case 'excellent':
    case 'good':
      return CheckCircle;
    case 'warning':
      return AlertTriangle;
    case 'critical':
      return XCircle;
    default:
      return Activity;
  }
};

const getStatusText = (status: LatencyStatus): string => {
  switch (status) {
    case 'excellent':
      return 'Excellent';
    case 'good':
      return 'Good';
    case 'warning':
      return 'High Latency';
    case 'critical':
      return 'Critical';
    default:
      return 'Unknown';
  }
};

/**
 * Simple sparkline visualization using bars
 */
const LatencySparkline: React.FC<{
  data: number[];
  max: number;
}> = ({ data, max }) => {
  if (data.length === 0) return null;

  return (
    <div className="flex items-end gap-0.5 h-12">
      {data.map((value, index) => {
        const height = Math.max((value / max) * 100, 5);
        const isRecent = index >= data.length - 3;

        return (
          <motion.div
            key={index}
            initial={{ height: 0 }}
            animate={{ height: `${height}%` }}
            transition={{ delay: index * 0.02 }}
            className={`flex-1 rounded-sm transition-colors ${
              isRecent
                ? 'bg-blue-400 dark:bg-blue-500'
                : 'bg-blue-300 dark:bg-blue-600/50'
            }`}
            style={{ height: `${height}%` }}
            title={`${value}ms`}
          />
        );
      })}
    </div>
  );
};

export const LatencyMonitor: React.FC<LatencyMonitorProps> = ({
  currentLatency = 0,
  history: initialHistory = [],
  thresholdWarning = 200,
  thresholdCritical = 500,
  updateInterval = 1000,
  className = '',
}) => {
  const { t } = useTranslation();
  const [latencyHistory, setLatencyHistory] = useState<LatencyDataPoint[]>(
    initialHistory.map((value) => ({
      value,
      timestamp: Date.now(),
    }))
  );

  const status = getStatus(currentLatency, thresholdWarning, thresholdCritical);
  const StatusIcon = getStatusIcon(status);
  const maxLatency = Math.max(
    thresholdCritical,
    ...latencyHistory.map((d) => d.value)
  );

  // Simulate real-time updates (in production, this would come from WebSocket or API)
  useEffect(() => {
    if (currentLatency === 0) return;

    const interval = setInterval(() => {
      setLatencyHistory((prev) => {
        const newHistory = [
          ...prev.slice(-19), // Keep last 20 data points
          {
            value: currentLatency,
            timestamp: Date.now(),
          },
        ];
        return newHistory;
      });
    }, updateInterval);

    return () => clearInterval(interval);
  }, [currentLatency, updateInterval]);

  // Calculate statistics
  const avgLatency =
    latencyHistory.length > 0
      ? latencyHistory.reduce((sum, d) => sum + d.value, 0) /
        latencyHistory.length
      : 0;
  const maxObservedLatency =
    latencyHistory.length > 0
      ? Math.max(...latencyHistory.map((d) => d.value))
      : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-xl bg-[color:var(--color-surface-muted)]/50 border border-[color:var(--color-border)] ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[color:var(--color-text-muted)]" />
          <span className="text-sm font-medium text-[color:var(--color-text-muted)]">
            {t('live.latency.title', 'Stream Latency')}
          </span>
        </div>
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${getStatusBgColor(
            status
          )}`}
        >
          <StatusIcon className="w-3.5 h-3.5" />
          {t(`live.latency.status.${status}`, getStatusText(status))}
        </div>
      </div>

      {/* Current latency display */}
      <div className="mb-4">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('live.latency.current', 'Current')}
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-[color:var(--color-text)]">
                {currentLatency}
              </span>
              <span className="text-sm text-[color:var(--color-text-muted)]">
                ms
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('live.latency.average', 'Average')}
            </p>
            <p className="text-lg font-semibold text-[color:var(--color-text)]">
              {Math.round(avgLatency)}
              <span className="text-sm text-[color:var(--color-text-muted)] ml-1">
                ms
              </span>
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <Progress
          size="sm"
          value={currentLatency}
          maxValue={thresholdCritical}
          color={
            status === 'critical'
              ? 'danger'
              : status === 'warning'
              ? 'warning'
              : 'success'
          }
          className="mt-3"
          aria-label={`Current latency: ${currentLatency}ms`}
        />
      </div>

      {/* Historical data sparkline */}
      {latencyHistory.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-[color:var(--color-text-muted)] mb-2">
            <span>{t('live.latency.history', 'Last 20 measurements')}</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {t('live.latency.peak', 'Peak')}: {maxObservedLatency}ms
            </span>
          </div>
          <LatencySparkline
            data={latencyHistory.map((d) => d.value)}
            max={maxLatency}
          />
        </div>
      )}

      {/* Quality indicators */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[color:var(--color-border)]">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Zap className="w-3 h-3 text-emerald-500" />
            <span className="text-xs font-medium text-[color:var(--color-text-muted)]">
              {t('live.latency.excellent', '&lt;100ms')}
            </span>
          </div>
          <p className="text-xs text-emerald-600 dark:text-emerald-400">
            {t('live.latency.excellentDesc', 'Excellent')}
          </p>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <Activity className="w-3 h-3 text-amber-500" />
            <span className="text-xs font-medium text-[color:var(--color-text-muted)]">
              {t('live.latency.good', '&lt;200ms')}
            </span>
          </div>
          <p className="text-xs text-amber-600 dark:text-amber-400">
            {t('live.latency.goodDesc', 'Good')}
          </p>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <AlertTriangle className="w-3 h-3 text-rose-500" />
            <span className="text-xs font-medium text-[color:var(--color-text-muted)]">
              {t('live.latency.high', '&gt;200ms')}
            </span>
          </div>
          <p className="text-xs text-rose-600 dark:text-rose-400">
            {t('live.latency.highDesc', 'High Latency')}
          </p>
        </div>
      </div>
    </motion.div>
  );
};

export default LatencyMonitor;
