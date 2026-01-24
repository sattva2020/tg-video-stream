/**
 * Страница управления rate limits.
 *
 * Позволяет администраторам:
 * - Мониторить текущее состояние rate limits
 * - Просматривать статистику очередей
 * - Анализировать тренды использования
 * - Настраивать параметры rate limiting
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Settings,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Activity,
  Users,
  Clock,
  TrendingUp,
  Zap,
  Gauge,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout';
import { client as api } from '../../api/client';
import { RateLimitDashboard } from '../../components/dashboard/RateLimitDashboard';
import RateLimitChart from '../../components/dashboard/RateLimitChart';

// === Types ===

interface AccountLimitStatus {
  account_id: string;
  endpoint_type: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  status: 'healthy' | 'warning' | 'critical';
  predicted_breach_time?: string;
  time_until_breach_seconds?: number;
}

interface RateLimitStatusResponse {
  overall_status: 'healthy' | 'warning' | 'critical';
  total_accounts: number;
  active_accounts: number;
  rate_limited_accounts: number;
  accounts: AccountLimitStatus[];
  timestamp: string;
}

interface QueueStatsResponse {
  total_pending: number;
  total_processing: number;
  stats_by_priority: {
    priority_level: 'HIGH' | 'MEDIUM' | 'LOW';
    pending_requests: number;
    processing_requests: number;
    completed_last_minute: number;
    average_wait_time_seconds: number;
  }[];
  batch_size: number;
  batch_timeout_seconds: number;
  timestamp: string;
}

// === Component ===

const RateLimitsPage: React.FC = () => {
  const { user } = useAuth();

  // State
  const [activeTab, setActiveTab] = useState<'dashboard' | 'trends' | 'settings'>('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // === Data fetching ===

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    // Force refresh of child components by setting a timeout
    setTimeout(() => {
      setRefreshing(false);
      setSuccessMessage('Data refreshed successfully');
      setTimeout(() => setSuccessMessage(null), 2000);
    }, 500);
  }, []);

  useEffect(() => {
    setLoading(false);
  }, []);

  // === Render ===

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Gauge className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Rate Limits
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Monitor and manage API rate limits and queue performance
              </p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-500 hover:text-red-700"
            >
              ×
            </button>
          </div>
        )}

        {successMessage && (
          <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 text-green-700 dark:text-green-400">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            {successMessage}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'dashboard'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <Activity className="w-4 h-4" />
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('trends')}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'trends'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                Trends
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'settings'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {activeTab === 'dashboard' && (
            <div key={refreshing ? 'refreshing' : 'dashboard'}>
              <RateLimitDashboard />
            </div>
          )}

          {activeTab === 'trends' && (
            <div key={refreshing ? 'refreshing' : 'trends'}>
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Rate Limit Trends
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Historical data and predictions for rate limit usage
                  </p>
                </div>
                <RateLimitChart
                  autoRefresh={true}
                  refreshInterval={30000}
                />
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div key={refreshing ? 'refreshing' : 'settings'}>
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Zap className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Rate Limit Settings
                  </h2>
                  <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md">
                    Configure rate limit thresholds, alert preferences, and notification rules for rate limit events.
                  </p>
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 max-w-md">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                          Coming Soon
                        </p>
                        <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">
                          Rate limit configuration and alert settings will be available in a future update.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Stats Footer */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-medium text-blue-800 dark:text-blue-300 uppercase">
                Real-time Monitoring
              </span>
            </div>
            <p className="text-xs text-blue-700 dark:text-blue-400">
              Track rate limit usage across all accounts and endpoints in real-time
            </p>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span className="text-xs font-medium text-purple-800 dark:text-purple-300 uppercase">
                Predictive Analytics
              </span>
            </div>
            <p className="text-xs text-purple-700 dark:text-purple-400">
              AI-powered predictions help you anticipate rate limit breaches before they happen
            </p>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-green-600 dark:text-green-400" />
              <span className="text-xs font-medium text-green-800 dark:text-green-300 uppercase">
                Queue Management
              </span>
            </div>
            <p className="text-xs text-green-700 dark:text-green-400">
              Intelligent batching and priority queues optimize API request efficiency
            </p>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default RateLimitsPage;
