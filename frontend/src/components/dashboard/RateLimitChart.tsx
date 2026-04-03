/**
 * Feature 005 Phase 6: Rate Limit Chart Component
 *
 * Отображает график использования rate limit с прогнозами и предсказанием времени превышения
 */

import { useEffect, useState } from 'react';

// TypeScript interfaces matching backend API responses
export interface RateLimitPrediction {
  account_id: string;
  endpoint_type: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  predicted_breach_time: string | null;
  time_until_breach_seconds: number | null;
  trend: 'increasing' | 'stable' | 'decreasing';
  confidence: number;
  status: 'healthy' | 'warning' | 'critical';
}

export interface RateLimitChartData {
  predictions: RateLimitPrediction[];
  summary: {
    total_predictions: number;
    approaching_limit: number;
    critical_predictions: number;
    overall_status: string;
  };
  timestamp: string;
}

interface RateLimitChartProps {
  accountId?: string;
  endpointType?: string;
  hours?: number;
  loading?: boolean;
  error?: string | null;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

/**
 * RateLimitChart - Компонент для отображения трендов использования rate limit
 *
 * Features:
 * - График использования за период
 * - Предсказанное время превышения лимита
 * - Тренды использования (increasing/stable/decreasing)
 * - Уровни доверия к прогнозам
 * - Статусы по каждому аккаунту и endpoint
 * - Real-time updates (опционально)
 * - Responsive design
 * - Loading/Error states
 *
 * Требует: Recharts library (npm install recharts)
 */
export default function RateLimitChart({
  accountId,
  endpointType,
  hours = 24,
  loading = false,
  error = null,
  autoRefresh = true,
  refreshInterval = 30000 // 30 seconds by default
}: RateLimitChartProps) {
  const [chartData, setChartData] = useState<RateLimitChartData | null>(null);
  const [isLoading, setIsLoading] = useState(loading);
  const [errorMsg, setErrorMsg] = useState<string | null>(error);

  // Sync loading state from parent
  useEffect(() => {
    setIsLoading(loading);
  }, [loading]);

  // Fetch chart data
  const fetchChartData = async () => {
    // Don't fetch if parent is controlling loading state
    if (loading) return;

    setIsLoading(true);
    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (accountId) params.append('account_id', accountId);
      if (endpointType) params.append('endpoint_type', endpointType);

      // TODO: Import rateLimitsApi when ready (subtask-6-5)
      // const data = await rateLimitsApi.getPredictions(accountId);
      // setChartData(data);
      // setErrorMsg(null);

      // For now, return placeholder data
      const placeholderData: RateLimitChartData = {
        predictions: [
          {
            account_id: accountId || 'account-1',
            endpoint_type: endpointType || 'messages',
            current_usage: 45,
            limit: 60,
            usage_percent: 75.0,
            predicted_breach_time: new Date(Date.now() + 1200 * 1000).toISOString(),
            time_until_breach_seconds: 1200,
            trend: 'increasing',
            confidence: 0.85,
            status: 'warning'
          }
        ],
        summary: {
          total_predictions: 1,
          approaching_limit: 1,
          critical_predictions: 0,
          overall_status: 'warning'
        },
        timestamp: new Date().toISOString()
      };

      setChartData(placeholderData);
      setErrorMsg(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(`Failed to fetch rate limit predictions: ${message}`);
      setChartData(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChartData();

    // Set up auto-refresh if enabled
    if (autoRefresh && !loading) {
      const intervalId = setInterval(fetchChartData, refreshInterval);
      return () => clearInterval(intervalId);
    }
  }, [accountId, endpointType, hours, autoRefresh, refreshInterval, loading]);

  // Helper function to format time until breach
  const formatTimeUntilBreach = (seconds: number | null): string => {
    if (!seconds) return 'Unknown';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m`;
    } else {
      return `${seconds}s`;
    }
  };

  // Helper function to get status color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'critical':
        return 'red';
      case 'warning':
        return 'yellow';
      case 'healthy':
      default:
        return 'green';
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading rate limit data...</p>
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
  if (!chartData || chartData.predictions.length === 0) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
        <p className="text-gray-500">No rate limit data available</p>
      </div>
    );
  }

  // Calculate statistics
  const avgUsage = chartData.predictions.length > 0
    ? chartData.predictions.reduce((sum, p) => sum + p.usage_percent, 0) / chartData.predictions.length
    : 0;
  const maxUsage = chartData.predictions.length > 0
    ? Math.max(...chartData.predictions.map(p => p.usage_percent))
    : 0;
  const minUsage = chartData.predictions.length > 0
    ? Math.min(...chartData.predictions.map(p => p.usage_percent))
    : 0;
  const avgConfidence = chartData.predictions.length > 0
    ? chartData.predictions.reduce((sum, p) => sum + p.confidence, 0) / chartData.predictions.length
    : 0;

  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-6 shadow">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Rate Limit Usage Trends
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {accountId ? `Account: ${accountId}` : 'All Accounts'}
            {endpointType && ` • Endpoint: ${endpointType}`}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium
            ${chartData.summary.overall_status === 'critical' ? 'bg-red-100 text-red-800' :
              chartData.summary.overall_status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
              'bg-green-100 text-green-800'}`}>
            {chartData.summary.overall_status}
          </span>
          {autoRefresh && (
            <span className="text-xs text-gray-500">Auto-refreshing</span>
          )}
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded p-4">
          <p className="text-xs font-medium text-blue-600 uppercase">Average Usage</p>
          <p className="text-2xl font-bold text-blue-700 mt-2">
            {avgUsage.toFixed(1)}%
          </p>
        </div>

        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded p-4">
          <p className="text-xs font-medium text-red-600 uppercase">Max Usage</p>
          <p className="text-2xl font-bold text-red-700 mt-2">
            {maxUsage.toFixed(1)}%
          </p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded p-4">
          <p className="text-xs font-medium text-green-600 uppercase">Min Usage</p>
          <p className="text-2xl font-bold text-green-700 mt-2">
            {minUsage.toFixed(1)}%
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded p-4">
          <p className="text-xs font-medium text-purple-600 uppercase">Prediction Confidence</p>
          <p className="text-2xl font-bold text-purple-700 mt-2">
            {(avgConfidence * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Chart Placeholder */}
      <div className="bg-gray-50 rounded border border-gray-200 p-12 mb-6">
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
              d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
            />
          </svg>
          <p className="text-gray-600 font-medium mb-1">Rate Limit Trend Chart</p>
          <p className="text-sm text-gray-500">
            Interactive chart will be displayed here using Recharts library
          </p>
          <p className="text-xs text-gray-400 mt-3">
            ({chartData.predictions.length} data points)
          </p>
        </div>
      </div>

      {/* Predictions Table */}
      <div className="mt-6">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Rate Limit Predictions</h4>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Account
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Endpoint
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usage
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trend
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time Until Breach
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {chartData.predictions.map((prediction, index) => (
                <tr key={`${prediction.account_id}-${prediction.endpoint_type}-${index}`}>
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {prediction.account_id}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    {prediction.endpoint_type}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center">
                      <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className={`h-2 rounded-full ${
                            prediction.usage_percent >= 90 ? 'bg-red-500' :
                            prediction.usage_percent >= 75 ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(prediction.usage_percent, 100)}%` }}
                        ></div>
                      </div>
                      <span>{prediction.usage_percent.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className={`inline-flex items-center ${
                      prediction.trend === 'increasing' ? 'text-red-600' :
                      prediction.trend === 'decreasing' ? 'text-green-600' :
                      'text-gray-600'
                    }`}>
                      {prediction.trend === 'increasing' && '↗'}
                      {prediction.trend === 'decreasing' && '↘'}
                      {prediction.trend === 'stable' && '→'}
                      <span className="ml-1 capitalize">{prediction.trend}</span>
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                    {prediction.time_until_breach_seconds ? (
                      <span className={prediction.time_until_breach_seconds < 600 ? 'text-red-600 font-medium' : ''}>
                        {formatTimeUntilBreach(prediction.time_until_breach_seconds)}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      prediction.status === 'critical' ? 'bg-red-100 text-red-800' :
                      prediction.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {prediction.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Data Summary */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Total Predictions:</span>
            <span className="ml-2 font-medium text-gray-900">{chartData.summary.total_predictions}</span>
          </div>
          <div>
            <span className="text-gray-600">Approaching Limit:</span>
            <span className="ml-2 font-medium text-yellow-600">{chartData.summary.approaching_limit}</span>
          </div>
          <div>
            <span className="text-gray-600">Critical:</span>
            <span className="ml-2 font-medium text-red-600">{chartData.summary.critical_predictions}</span>
          </div>
          <div>
            <span className="text-gray-600">Last Updated:</span>
            <span className="ml-2 font-medium text-gray-900">
              {new Date(chartData.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
