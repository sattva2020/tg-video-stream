/**
 * EngagementMetrics Component
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * Карточка для отображения метрик вовлеченности аудитории.
 * Показывает активность в чате, реакции и активных пользователей.
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  MessageCircle,
  Heart,
  Users,
  TrendingUp,
  Award,
} from 'lucide-react';
import { EngagementMetricsResponse } from '@/types/analytics';

interface EngagementMetricsProps {
  /** Данные метрик вовлеченности */
  data: EngagementMetricsResponse | null;
  /** Загрузка данных */
  loading?: boolean;
}

export const EngagementMetrics: React.FC<EngagementMetricsProps> = ({
  data,
  loading = false,
}) => {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`
          relative overflow-hidden rounded-2xl p-6
          bg-[color:var(--color-panel)]
          border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
          shadow-md shadow-black/5
        `}
      >
        <div className="space-y-6">
          <div className="h-6 w-48 bg-[color:var(--color-border)] rounded animate-pulse" />
          <div className="grid grid-cols-3 gap-4">
            <div className="h-20 bg-[color:var(--color-border)] rounded animate-pulse" />
            <div className="h-20 bg-[color:var(--color-border)] rounded animate-pulse" />
            <div className="h-20 bg-[color:var(--color-border)] rounded animate-pulse" />
          </div>
          <div className="h-24 bg-[color:var(--color-border)] rounded animate-pulse" />
        </div>
      </motion.div>
    );
  }

  if (!data) {
    return null;
  }

  // Calculate totals for chat activity
  const totalChatActivity = data.total_messages + data.total_comments;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative overflow-hidden rounded-2xl p-6
        bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
      `}
    >
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-1">
          Вовлеченность аудитории
        </h3>
        <p className="text-sm text-[color:var(--color-text-muted)]">
          Активность в чате и реакции
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="space-y-4">
        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-3">
          {/* Chat Activity */}
          <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-violet-500/5 border border-violet-500/20">
            <div className="p-2 rounded-lg bg-violet-500/10 mb-2">
              <MessageCircle className="w-5 h-5 text-violet-600 dark:text-violet-400" />
            </div>
            <p className="text-2xl font-bold text-[color:var(--color-text)]">
              {totalChatActivity.toLocaleString()}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              Чат
            </p>
          </div>

          {/* Reactions */}
          <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-rose-500/5 border border-rose-500/20">
            <div className="p-2 rounded-lg bg-rose-500/10 mb-2">
              <Heart className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            </div>
            <p className="text-2xl font-bold text-[color:var(--color-text)]">
              {data.total_reactions.toLocaleString()}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              Реакции
            </p>
          </div>

          {/* Active Users */}
          <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
            <div className="p-2 rounded-lg bg-emerald-500/10 mb-2">
              <Users className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-[color:var(--color-text)]">
              {data.unique_users.toLocaleString()}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              Пользователи
            </p>
          </div>
        </div>

        {/* Detailed Breakdown */}
        <div className="p-4 rounded-xl bg-[color:var(--color-border-secondary)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                Сообщений
              </p>
              <p className="text-lg font-semibold text-[color:var(--color-text)]">
                {data.total_messages.toLocaleString()}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                Комментариев
              </p>
              <p className="text-lg font-semibold text-[color:var(--color-text)]">
                {data.total_comments.toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                Среднее в день
              </p>
              <p className="text-lg font-semibold text-[color:var(--color-text)]">
                {data.average_daily.toFixed(0)}
              </p>
            </div>
          </div>
        </div>

        {/* Top Active Users */}
        {data.top_active_users && data.top_active_users.length > 0 && (
          <div className="pt-2">
            <div className="flex items-center gap-2 mb-3">
              <Award className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <p className="text-sm font-medium text-[color:var(--color-text-muted)]">
                Топ активных пользователей
              </p>
            </div>
            <div className="space-y-2">
              {data.top_active_users.slice(0, 5).map((user, index) => (
                <div
                  key={user.user_id || index}
                  className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-border-secondary)] hover:bg-[color:var(--color-border)] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      index === 0 ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400' :
                      index === 1 ? 'bg-slate-500/20 text-slate-600 dark:text-slate-400' :
                      index === 2 ? 'bg-orange-500/20 text-orange-600 dark:text-orange-400' :
                      'bg-[color:var(--color-border)] text-[color:var(--color-text-muted)]'
                    }`}>
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[color:var(--color-text)]">
                        {user.username || 'Аноним'}
                      </p>
                      <p className="text-xs text-[color:var(--color-text-muted)]">
                        {new Date(user.last_activity).toLocaleDateString('ru-RU', {
                          day: 'numeric',
                          month: 'short',
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="text-center">
                      <p className="text-[color:var(--color-text-muted)] text-xs">💬</p>
                      <p className="font-medium text-[color:var(--color-text)]">{user.message_count}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[color:var(--color-text-muted)] text-xs">❤️</p>
                      <p className="font-medium text-[color:var(--color-text)]">{user.reaction_count}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default EngagementMetrics;
