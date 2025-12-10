import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
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

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color,
  loading = false,
}) => {
  const colors = colorConfig[color];

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <TrendingUp className="w-3 h-3" />;
    if (trend.value < 0) return <TrendingDown className="w-3 h-3" />;
    return <Minus className="w-3 h-3" />;
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) return 'text-emerald-500';
    if (trend.value < 0) return 'text-rose-500';
    return 'text-gray-500';
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] p-4 sm:p-5 shadow-md shadow-[color:var(--color-border)]/60"
      >
        <div className="animate-pulse space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          </div>
          <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-3 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
      className={`relative overflow-hidden rounded-3xl bg-[color:var(--color-panel)] border ${colors.border} p-5 sm:p-6 group cursor-default shadow-lg shadow-[color:var(--color-border)]/50`}
    >
      {/* Gradient glow on hover */}
      <div className={`absolute inset-0 bg-gradient-to-br ${colors.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />
      
      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs sm:text-sm font-medium text-[color:var(--color-text-muted)] uppercase tracking-wide">
            {title}
          </span>
          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${colors.gradient} shadow-lg ${colors.glow}`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
        
        <div className="flex items-end justify-between">
          <div>
            <motion.div 
              key={value}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-2xl sm:text-3xl font-bold text-[color:var(--color-text)]"
            >
              {value}
            </motion.div>
            {subtitle && (
              <div className="text-xs text-[color:var(--color-text-muted)] mt-1">
                {subtitle}
              </div>
            )}
          </div>
          
          {trend && (
            <div className={`flex items-center gap-1 text-xs font-medium ${getTrendColor()}`}>
              {getTrendIcon()}
              <span>{Math.abs(trend.value)}%</span>
              <span className="text-[color:var(--color-text-muted)] hidden sm:inline">
                {trend.label}
              </span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
