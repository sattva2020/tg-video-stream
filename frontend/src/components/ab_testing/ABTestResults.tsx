/**
 * ABTestResults Component
 * Feature: 016-a-b-testing-framework-for-content
 *
 * Отображение результатов A/B теста с графиками, доверительными интервалами и рекомендацией победителя.
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ErrorBar,
  Cell,
} from 'recharts';
import { motion } from 'framer-motion';
import { Trophy, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';
import type { ABTestAnalysisResponse, ABTestStatistics } from '../../types/ab_testing';

export interface ABTestResultsProps {
  analysis: ABTestAnalysisResponse;
  loading?: boolean;
}

const formatPercent = (value: number) => {
  return `${(value * 100).toFixed(2)}%`;
};

const formatConfidence = (value?: number) => {
  if (value === undefined) return 'N/A';
  return `${value.toFixed(2)}%`;
};

export const ABTestResults: React.FC<ABTestResultsProps> = ({
  analysis,
  loading = false,
}) => {
  // Transform data for Recharts
  const chartData = analysis.variants.map((variant) => ({
    name: variant.variant_name,
    conversion: variant.conversion_rate * 100,
    confidence: [
      (variant.confidence_interval_lower ?? 0) * 100,
      (variant.confidence_interval_upper ?? 0) * 100,
    ],
    isWinner: variant.variant_id === analysis.winner_variant_id,
  }));

  const getBarColor = (isWinner: boolean) => {
    return isWinner ? '#10B981' : '#3B82F6';
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-500/10 rounded-xl">
            <TrendingUp className="w-5 h-5 text-purple-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Результаты A/B теста
          </h3>
        </div>
        <div className="h-64 flex items-center justify-center">
          <div className="w-full h-full bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
        </div>
      </motion.div>
    );
  }

  if (!analysis.variants.length) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-500/10 rounded-xl">
            <TrendingUp className="w-5 h-5 text-purple-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Результаты A/B теста
          </h3>
        </div>
        <div className="h-64 flex items-center justify-center text-gray-500">
          Нет данных для анализа
        </div>
      </motion.div>
    );
  }

  const winnerVariant = analysis.variants.find(
    (v) => v.variant_id === analysis.winner_variant_id
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-lg"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10 rounded-xl">
            <TrendingUp className="w-5 h-5 text-purple-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Результаты A/B теста
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {analysis.is_significant ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 rounded-lg">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Статистически значимый
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-500/10 rounded-lg">
              <AlertCircle className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                Требуется больше данных
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Winner Recommendation */}
      {winnerVariant && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-6 p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-xl border border-green-500/20"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Trophy className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div className="flex-1">
              <h4 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
                Рекомендуемый победитель: {winnerVariant.variant_name}
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Конверсия: {formatPercent(winnerVariant.conversion_rate)}
                {analysis.recommended_action && (
                  <span className="ml-2">• {analysis.recommended_action}</span>
                )}
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Statistics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Уровень доверия</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {analysis.confidence_level}%
          </p>
        </div>
        {analysis.p_value !== undefined && (
          <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">P-value</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {analysis.p_value < 0.001 ? '<0.001' : analysis.p_value.toFixed(4)}
            </p>
          </div>
        )}
        <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Вариантов</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {analysis.variants.length}
          </p>
        </div>
      </div>

      {/* Bar Chart with Confidence Intervals */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
            <XAxis
              dataKey="name"
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              axisLine={{ stroke: '#E5E7EB' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              axisLine={{ stroke: '#E5E7EB' }}
              tickLine={false}
              width={50}
              label={{
                value: 'Конверсия (%)',
                angle: -90,
                position: 'insideLeft',
                fill: '#9CA3AF',
                fontSize: 11,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(17, 24, 39, 0.9)',
                border: 'none',
                borderRadius: '0.75rem',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              labelStyle={{ color: '#9CA3AF' }}
              formatter={(value: number, name: string, props: any) => {
                if (name === 'confidence') {
                  const [lower, upper] = value;
                  return [`[${lower.toFixed(2)}% - ${upper.toFixed(2)}%]`, 'Доверительный интервал'];
                }
                return [`${value.toFixed(2)}%`, 'Конверсия'];
              }}
            />
            <Bar
              dataKey="conversion"
              radius={[8, 8, 0, 0]}
              animationDuration={1000}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.isWinner)} />
              ))}
              <ErrorBar
                dataKey="confidence"
                width={4}
                stroke="#4B5563"
                strokeWidth={2}
                direction="y"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span className="text-gray-600 dark:text-gray-400">Победитель</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-blue-500" />
          <span className="text-gray-600 dark:text-gray-400">Вариант</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-gray-600 relative">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 border-t-2 border-b-2 border-gray-600" />
          </div>
          <span className="text-gray-600 dark:text-gray-400">95% доверительный интервал</span>
        </div>
      </div>

      {/* Detailed Statistics Table */}
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-3 px-4 font-semibold text-gray-900 dark:text-white">Вариант</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-900 dark:text-white">Показы</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-900 dark:text-white">Конверсии</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-900 dark:text-white">Конверсия</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-900 dark:text-white">95% ДИ</th>
            </tr>
          </thead>
          <tbody>
            {analysis.variants.map((variant) => (
              <tr
                key={variant.variant_id}
                className={`border-b border-gray-100 dark:border-gray-800 ${
                  variant.variant_id === analysis.winner_variant_id
                    ? 'bg-green-50/50 dark:bg-green-900/10'
                    : ''
                }`}
              >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {variant.variant_id === analysis.winner_variant_id && (
                      <Trophy className="w-4 h-4 text-green-500" />
                    )}
                    <span className="font-medium text-gray-900 dark:text-white">
                      {variant.variant_name}
                    </span>
                  </div>
                </td>
                <td className="text-right py-3 px-4 text-gray-600 dark:text-gray-400">
                  {variant.impressions.toLocaleString('ru-RU')}
                </td>
                <td className="text-right py-3 px-4 text-gray-600 dark:text-gray-400">
                  {variant.conversions.toLocaleString('ru-RU')}
                </td>
                <td className="text-right py-3 px-4 font-medium text-gray-900 dark:text-white">
                  {formatPercent(variant.conversion_rate)}
                </td>
                <td className="text-right py-3 px-4 text-gray-600 dark:text-gray-400">
                  {variant.confidence_interval_lower !== undefined &&
                  variant.confidence_interval_upper !== undefined
                    ? `${formatConfidence(variant.confidence_interval_lower)} - ${formatConfidence(
                        variant.confidence_interval_upper
                      )}`
                    : 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default ABTestResults;
