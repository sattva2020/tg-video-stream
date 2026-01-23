/**
 * InteractionMetrics Component
 * Feature: 020-viewer-interaction-engagement-features
 *
 * Панель метрик интерактивных функций зрителей.
 * Отображает статистику по голосованиям, вопросам, реакциям и CTA.
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  MessageSquare,
  BarChart3,
  Smile,
  Megaphone,
  MousePointerClick,
  Users,
  TrendingUp,
} from 'lucide-react';
import type { InteractionAnalytics } from '../../types/interactions';

interface InteractionMetricsProps {
  data: InteractionAnalytics | null;
  loading?: boolean;
}

const StatCard: React.FC<{
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  subtitle?: string;
}> = ({ label, value, icon: Icon, color, subtitle }) => {
  const colorConfig: Record<string, { bg: string; text: string; gradient: string }> = {
    violet: {
      bg: 'bg-violet-500/10',
      text: 'text-violet-600 dark:text-violet-400',
      gradient: 'from-violet-500 to-purple-600',
    },
    emerald: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-600 dark:text-emerald-400',
      gradient: 'from-emerald-500 to-green-600',
    },
    amber: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-600 dark:text-amber-400',
      gradient: 'from-amber-500 to-orange-600',
    },
    rose: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-600 dark:text-rose-400',
      gradient: 'from-rose-500 to-pink-600',
    },
    blue: {
      bg: 'bg-blue-500/10',
      text: 'text-blue-600 dark:text-blue-400',
      gradient: 'from-blue-500 to-indigo-600',
    },
    cyan: {
      bg: 'bg-cyan-500/10',
      text: 'text-cyan-600 dark:text-cyan-400',
      gradient: 'from-cyan-500 to-teal-600',
    },
  };

  const config = colorConfig[color];

  return (
    <div className="relative overflow-hidden rounded-xl p-4 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]">
      <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-5`} />
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-2">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <Icon className={`w-4 h-4 ${config.text}`} />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xs font-medium text-[color:var(--color-text-muted)]">
            {label}
          </p>
          <p className="text-lg font-bold text-[color:var(--color-text)]">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-[color:var(--color-text-muted)]">
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

const BreakdownSection: React.FC<{
  title: string;
  icon: React.ElementType;
  color: string;
  children: React.ReactNode;
}> = ({ title, icon: Icon, color, children }) => {
  const colorConfig: Record<string, { bg: string; text: string }> = {
    violet: {
      bg: 'bg-violet-500/10',
      text: 'text-violet-600 dark:text-violet-400',
    },
    emerald: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-600 dark:text-emerald-400',
    },
    amber: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-600 dark:text-amber-400',
    },
    rose: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-600 dark:text-rose-400',
    },
    blue: {
      bg: 'bg-blue-500/10',
      text: 'text-blue-600 dark:text-blue-400',
    },
    cyan: {
      bg: 'bg-cyan-500/10',
      text: 'text-cyan-600 dark:text-cyan-400',
    },
  };

  const config = colorConfig[color];

  return (
    <div className="rounded-xl p-4 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]">
      <div className="flex items-center gap-2 mb-3">
        <div className={`p-1.5 rounded-lg ${config.bg}`}>
          <Icon className={`w-4 h-4 ${config.text}`} />
        </div>
        <h4 className="text-sm font-semibold text-[color:var(--color-text)]">
          {title}
        </h4>
      </div>
      {children}
    </div>
  );
};

export const InteractionMetrics: React.FC<InteractionMetricsProps> = ({
  data,
  loading = false,
}) => {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-violet-500/10 rounded-xl">
            <MessageSquare className="w-5 h-5 text-violet-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              Интерактивы
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              Вовлечение зрителей
            </p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="h-24 bg-[color:var(--color-surface)] rounded-xl animate-pulse" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-20 bg-[color:var(--color-surface)] rounded-xl animate-pulse" />
            <div className="h-20 bg-[color:var(--color-surface)] rounded-xl animate-pulse" />
          </div>
        </div>
      </motion.div>
    );
  }

  if (!data) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-violet-500/10 rounded-xl">
            <MessageSquare className="w-5 h-5 text-violet-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              Интерактивы
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              Вовлечение зрителей
            </p>
          </div>
        </div>
        <div className="h-48 flex items-center justify-center text-[color:var(--color-text-muted)]">
          Нет данных об интерактивах
        </div>
      </motion.div>
    );
  }

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[color:var(--color-panel)] rounded-2xl p-6 border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-violet-500/10 rounded-xl">
            <MessageSquare className="w-5 h-5 text-violet-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              Интерактивы
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              Вовлечение зрителей
            </p>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatCard
          label="Всего взаимодействий"
          value={data.total_interactions}
          icon={TrendingUp}
          color="violet"
          subtitle="За период"
        />
        <StatCard
          label="Участников"
          value={data.unique_participants}
          icon={Users}
          color="blue"
          subtitle="Уникальных"
        />
      </div>

      {/* Detailed Breakdown */}
      <div className="space-y-3">
        {/* Polls */}
        <BreakdownSection title="Голосования" icon={BarChart3} color="emerald">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.polls.created}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Создано</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.polls.total_votes}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Голосов</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {formatPercentage(data.breakdown.polls.avg_participation_rate)}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Явка</p>
            </div>
          </div>
        </BreakdownSection>

        {/* Questions */}
        <BreakdownSection title="Вопросы" icon={MessageSquare} color="blue">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.questions.submitted}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Отправлено</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.questions.answered}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Отвечено</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.questions.total_upvotes}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">↑ ↑ ↑</p>
            </div>
          </div>
        </BreakdownSection>

        {/* Reactions */}
        <BreakdownSection title="Реакции" icon={Smile} color="amber">
          <div className="grid grid-cols-2 gap-2">
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.reactions.total_reactions}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Всего</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.reactions.unique_emojis_used}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Уникальных</p>
            </div>
          </div>
        </BreakdownSection>

        {/* Shoutouts */}
        <BreakdownSection title="Шшэутауты" icon={Megaphone} color="rose">
          <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
            <p className="text-lg font-bold text-[color:var(--color-text)]">
              {data.breakdown.shoutouts.displayed}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)]">Показано</p>
          </div>
        </BreakdownSection>

        {/* CTAs */}
        <BreakdownSection title="Призывы к действию" icon={MousePointerClick} color="cyan">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.ctas.displayed}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Показано</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {data.breakdown.ctas.clicked}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">Кликов</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[color:var(--color-surface)]">
              <p className="text-lg font-bold text-[color:var(--color-text)]">
                {formatPercentage(data.breakdown.ctas.click_rate)}
              </p>
              <p className="text-xs text-[color:var(--color-text-muted)]">CTR</p>
            </div>
          </div>
        </BreakdownSection>
      </div>
    </motion.div>
  );
};

export default InteractionMetrics;
