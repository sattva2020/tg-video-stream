/**
 * MetricCard Component
 * Feature: 021-admin-analytics-menu
 * 
 * Карточка для отображения метрики с иконкой и описанием.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
  color: 'violet' | 'amber' | 'emerald' | 'rose' | 'blue' | 'cyan';
  loading?: boolean;
}

const colorConfig = {
  violet: {
    gradient: 'from-violet-500 to-purple-600',
    bg: 'bg-violet-500/10',
    text: 'text-violet-600 dark:text-violet-400',
    border: 'border-violet-500/20',
    glow: 'shadow-violet-500/25',
  },
  amber: {
    gradient: 'from-amber-500 to-orange-600',
    bg: 'bg-amber-500/10',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-500/20',
    glow: 'shadow-amber-500/25',
  },
  emerald: {
    gradient: 'from-emerald-500 to-green-600',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-500/20',
    glow: 'shadow-emerald-500/25',
  },
  rose: {
    gradient: 'from-rose-500 to-pink-600',
    bg: 'bg-rose-500/10',
    text: 'text-rose-600 dark:text-rose-400',
    border: 'border-rose-500/20',
    glow: 'shadow-rose-500/25',
  },
  blue: {
    gradient: 'from-blue-500 to-indigo-600',
    bg: 'bg-blue-500/10',
    text: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-500/20',
    glow: 'shadow-blue-500/25',
  },
  cyan: {
    gradient: 'from-cyan-500 to-teal-600',
    bg: 'bg-cyan-500/10',
    text: 'text-cyan-600 dark:text-cyan-400',
    border: 'border-cyan-500/20',
    glow: 'shadow-cyan-500/25',
  },
};

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color,
  loading = false,
}) => {
  const config = colorConfig[color];

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <TrendingUp className="w-4 h-4 text-emerald-500" />;
    if (trend.value < 0) return <TrendingDown className="w-4 h-4 text-rose-500" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) return 'text-emerald-500';
    if (trend.value < 0) return 'text-rose-500';
    return 'text-gray-400';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative overflow-hidden rounded-2xl p-6
        bg-white dark:bg-gray-800/50
        border ${config.border}
        shadow-lg ${config.glow}
        backdrop-blur-sm
      `}
    >
      {/* Gradient Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-5`} />

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl ${config.bg}`}>
            <Icon className={`w-6 h-6 ${config.text}`} />
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
              {getTrendIcon()}
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </h3>
          {loading ? (
            <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          ) : (
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {value}
            </p>
          )}
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {subtitle}
            </p>
          )}
          {trend && (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {trend.label}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default MetricCard;
