/**
 * ContentInsights Component
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * Анализ контента с самыми просматриваемыми и точками отказа.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Film, Clock, Eye, TrendingDown } from 'lucide-react';
import type { ContentPerformanceItem, DropOffPoint } from '../../types/analytics';

interface ContentInsightsProps {
  mostWatched: ContentPerformanceItem[];
  dropOffPoints: DropOffPoint[];
  averageCompletionRate: number;
  loading?: boolean;
}

const formatDuration = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);

  if (minutes > 0) {
    return `${minutes}м ${secs}с`;
  }
  return `${secs}с`;
};

const formatPercentage = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const ContentInsights: React.FC<ContentInsightsProps> = ({
  mostWatched,
  dropOffPoints,
  averageCompletionRate,
  loading = false,
}) => {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-emerald-500/10 rounded-xl">
            <Film className="w-5 h-5 text-emerald-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Анализ контента
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
          ))}
        </div>
      </motion.div>
    );
  }

  if (!mostWatched.length && !dropOffPoints.length) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-emerald-500/10 rounded-xl">
            <Film className="w-5 h-5 text-emerald-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Анализ контента
          </h3>
        </div>
        <div className="h-48 flex items-center justify-center text-gray-500">
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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 rounded-xl">
            <Film className="w-5 h-5 text-emerald-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Анализ контента
          </h3>
        </div>
        {averageCompletionRate > 0 && (
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
              Завершение: {formatPercentage(averageCompletionRate)}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-6">
        {/* Most Watched Content */}
        {mostWatched.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <Eye className="w-4 h-4" />
              Самое просматриваемое
            </h4>
            <div className="space-y-2">
              {mostWatched.map((content, index) => (
                <motion.div
                  key={content.content_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="p-3 rounded-xl bg-gray-50 dark:bg-gray-700/30 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                          #{index + 1}
                        </span>
                        <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {content.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                        <span className="flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {content.total_views} просм.
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDuration(content.average_watch_duration_seconds)}
                        </span>
                        <span className="flex items-center gap-1">
                          {formatPercentage(content.average_completion_percentage)} досмотр.
                        </span>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${content.average_completion_percentage}%` }}
                          transition={{ duration: 0.5, delay: index * 0.05 }}
                          className={`h-full rounded-full ${
                            content.average_completion_percentage >= 70
                              ? 'bg-emerald-500'
                              : content.average_completion_percentage >= 40
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                        />
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 block text-right">
                        {formatPercentage(content.average_completion_percentage)}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Drop-off Points */}
        {dropOffPoints.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-rose-500" />
              Точки отказа
            </h4>
            <div className="space-y-2">
              {dropOffPoints.slice(0, 5).map((point, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-700/30 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatDuration(point.position_seconds)}
                      </span>
                      <span className="text-sm font-semibold text-rose-500 dark:text-rose-400">
                        {formatPercentage(point.percentage)}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(point.percentage, 100)}%` }}
                        transition={{ duration: 0.5, delay: index * 0.05 }}
                        className="h-full bg-gradient-to-r from-rose-500 to-orange-500 rounded-full"
                      />
                    </div>
                    <div className="flex items-center justify-between mt-1 text-xs text-gray-500 dark:text-gray-400">
                      <span>{point.viewers_count} зрителей</span>
                      <span>Кумулятивно: {formatPercentage(point.cumulative_drop_off)}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default ContentInsights;
