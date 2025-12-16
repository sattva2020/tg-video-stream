/**
 * Feature 022 Phase 3: Stream Quality Trend Chart Component
 * 
 * Отображает график качества потока за 24 часа с использованием Recharts
 */

import { useEffect, useState } from 'react';
import { QualityTrendData } from '../../api/admin';

interface StreamQualityChartProps {
  streamUrl: string;
  streamName?: string;
  hours?: number;
  loading?: boolean;
  error?: string | null;
}

/**
 * StreamQualityChart - Компонент для отображения тренда качества
 * 
 * Features:
 * - Линейный график качества за период
 * - Минимальное/максимальное/среднее качество
 * - Bitrate overlay
 * - Разные цвета для разных уровней качества
 * - Responsive design
 * - Loading/Error states
 * 
 * Требует: Recharts library (npm install recharts)
 */
export default function StreamQualityChart({
  streamUrl,
  streamName,
  hours = 24,
  loading = false,
  error = null 
}: StreamQualityChartProps) {
  const [trendData, setTrendData] = useState<QualityTrendData | null>(null);
  const [isLoading, setIsLoading] = useState(loading);
  const [errorMsg, setErrorMsg] = useState<string | null>(error);

  useEffect(() => {
    const fetchTrendData = async () => {
      setIsLoading(true);
      try {
        // TODO: Import adminApi when ready
        // const data = await adminApi.getQualityTrend(streamUrl, hours);
        // setTrendData(data);
        // setErrorMsg(null);
        // if (onDataLoaded) onDataLoaded(data);
        
        // For now, return placeholder
        console.log(`Fetching trend data for ${streamUrl} (${hours}h)`);
        setIsLoading(false);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setErrorMsg(`Failed to fetch trend data: ${message}`);
        setTrendData(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTrendData();
  }, [streamUrl, hours]);

  // Loading state
  if (isLoading) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading trend data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (errorMsg) {
    return (
      <div className="w-full bg-red-50 rounded-lg border border-red-200 p-6">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">{errorMsg}</h3>
          </div>
        </div>
      </div>
    );
  }

  // No data state
  if (!trendData || trendData.history.length === 0) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
        <p className="text-gray-500">No quality data available for this period</p>
      </div>
    );
  }

  // Placeholder chart content
  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-6 shadow">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {streamName || streamUrl}
        </h3>
        <p className="text-sm text-gray-600 mt-1">Last {hours} hours quality trend</p>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded p-4">
          <p className="text-xs font-medium text-green-600 uppercase">Average Quality</p>
          <p className="text-2xl font-bold text-green-700 mt-2">
            {trendData.average_quality}
          </p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded p-4">
          <p className="text-xs font-medium text-blue-600 uppercase">Max Quality</p>
          <p className="text-2xl font-bold text-blue-700 mt-2">
            {trendData.max_quality}
          </p>
        </div>

        <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded p-4">
          <p className="text-xs font-medium text-yellow-600 uppercase">Min Quality</p>
          <p className="text-2xl font-bold text-yellow-700 mt-2">
            {trendData.min_quality}
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded p-4">
          <p className="text-xs font-medium text-purple-600 uppercase">Success Rate</p>
          <p className="text-2xl font-bold text-purple-700 mt-2">
            {(trendData.success_rate * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="bg-gray-50 rounded border border-gray-200 p-12">
        <div className="text-center">
          <svg
            className="h-12 w-12 text-gray-400 mx-auto mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-gray-600 font-medium mb-1">Interactive Chart</p>
          <p className="text-sm text-gray-500">
            Chart will be displayed here using Recharts library
          </p>
          <p className="text-xs text-gray-400 mt-3">
            ({trendData.samples_count} data points)
          </p>
        </div>
      </div>

      {/* Data Points Summary */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Data Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Total Samples:</span>
            <span className="ml-2 font-medium text-gray-900">{trendData.samples_count}</span>
          </div>
          <div>
            <span className="text-gray-600">Avg Audio Bitrate:</span>
            <span className="ml-2 font-medium text-gray-900">
              {trendData.audio_avg_bitrate_kbps ? `${trendData.audio_avg_bitrate_kbps} kbps` : '—'}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Avg Video Bitrate:</span>
            <span className="ml-2 font-medium text-gray-900">
              {trendData.video_avg_bitrate_kbps ? `${trendData.video_avg_bitrate_kbps} kbps` : '—'}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Period Start:</span>
            <span className="ml-2 font-medium text-gray-900">
              {new Date(trendData.period_start).toLocaleTimeString()}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Period End:</span>
            <span className="ml-2 font-medium text-gray-900">
              {new Date(trendData.period_end).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
