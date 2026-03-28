/**
 * RecommendationCard Component
 * Feature: 014-ai-powered-content-recommendations
 *
 * Карточка для отображения рекомендации с уверенностью, алгоритмом и причиной.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon, Music, Play, Sparkles } from 'lucide-react';
import type { RecommendationItem, RecommendationAlgorithm } from '../../types/recommendations';

interface RecommendationCardProps {
  recommendation: RecommendationItem;
  loading?: boolean;
  onPlay?: (playlistItemId: string) => void;
}

const algorithmConfig: Record<RecommendationAlgorithm, {
  label: string;
  color: 'violet' | 'blue' | 'emerald';
  icon: LucideIcon;
}> = {
  collaborative_filtering: {
    label: 'Коллаборативная фильтрация',
    color: 'violet',
    icon: Sparkles,
  },
  content_based: {
    label: 'По содержанию',
    color: 'blue',
    icon: Music,
  },
  hybrid: {
    label: 'Гибридный',
    color: 'emerald',
    icon: Play,
  },
};

const colorConfig = {
  violet: {
    gradient: 'from-violet-500 to-purple-600',
    bg: 'bg-violet-500/10',
    text: 'text-violet-600 dark:text-violet-400',
    border: 'border-violet-500/20',
  },
  blue: {
    gradient: 'from-blue-500 to-indigo-600',
    bg: 'bg-blue-500/10',
    text: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-500/20',
  },
  emerald: {
    gradient: 'from-emerald-500 to-green-600',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-500/20',
  },
};

const formatScore = (score: number): string => {
  return `${Math.round(score * 100)}%`;
};

const getScoreColor = (score: number): string => {
  if (score >= 0.8) return 'text-emerald-500';
  if (score >= 0.6) return 'text-amber-500';
  return 'text-rose-500';
};

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  loading = false,
  onPlay,
}) => {
  const config = algorithmConfig[recommendation.algorithm];
  const colorTheme = colorConfig[config.color];
  const Icon = config.icon;

  const handleClick = () => {
    if (onPlay && !loading) {
      onPlay(recommendation.playlist_item_id);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={onPlay ? { scale: 1.02 } : {}}
      whileTap={onPlay ? { scale: 0.98 } : {}}
      className={`
        relative overflow-hidden rounded-2xl p-5
        bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
        ${onPlay ? 'cursor-pointer' : ''}
        transition-all duration-300
      `}
      onClick={handleClick}
    >
      {/* Gradient Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${colorTheme.gradient} opacity-5`} />

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          {/* Icon */}
          <div className={`p-2.5 rounded-xl ${colorTheme.bg}`}>
            <Icon className={`w-5 h-5 ${colorTheme.text}`} />
          </div>

          {/* Score Badge */}
          <div className={`px-3 py-1.5 rounded-lg ${colorTheme.bg} border ${colorTheme.border}`}>
            <span className={`text-sm font-semibold ${getScoreColor(recommendation.score)}`}>
              {formatScore(recommendation.score)}
            </span>
          </div>
        </div>

        {/* Title and Artist */}
        <div className="space-y-1 mb-3">
          {loading ? (
            <>
              <div className="h-5 w-3/4 bg-[color:var(--color-border)] rounded animate-pulse" />
              <div className="h-4 w-1/2 bg-[color:var(--color-border)] rounded animate-pulse" />
            </>
          ) : (
            <>
              <h3 className="text-base font-semibold text-[color:var(--color-text)] line-clamp-2">
                {recommendation.title}
              </h3>
              {recommendation.artist && (
                <p className="text-sm text-[color:var(--color-text-muted)]">
                  {recommendation.artist}
                </p>
              )}
            </>
          )}
        </div>

        {/* Algorithm Badge */}
        <div className="flex items-center justify-between">
          <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${colorTheme.bg} border ${colorTheme.border}`}>
            <Icon className={`w-3.5 h-3.5 ${colorTheme.text}`} />
            <span className={`text-xs font-medium ${colorTheme.text}`}>
              {config.label}
            </span>
          </div>

          {/* Play Button (if callback provided) */}
          {onPlay && !loading && (
            <button
              className={`p-2 rounded-lg ${colorTheme.bg} hover:${colorTheme.bg.replace('/10', '/20')} ${colorTheme.text} transition-colors duration-300`}
              onClick={(e) => {
                e.stopPropagation();
                handleClick();
              }}
              title="Воспроизвести"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Reason (if available) */}
        {recommendation.reason && !loading && (
          <div className="mt-3 pt-3 border-t border-[color:var(--color-border)]">
            <p className="text-xs text-[color:var(--color-text-muted)] leading-relaxed">
              {recommendation.reason}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default RecommendationCard;
