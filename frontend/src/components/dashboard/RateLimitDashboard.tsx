import React, { useState, useCallback } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Progress,
  Tabs,
  Tab,
} from '@heroui/react';
import { useToast } from '../../hooks/useToast';
import { Skeleton } from '../ui/Skeleton';
import { client } from '../../api/client';
import {
  AlertCircle,
  CheckCircle,
  RefreshCw,
  TrendingUp,
  Users,
  Activity,
  Clock,
  Zap,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

// Types based on backend API responses
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

export const RateLimitDashboard: React.FC = () => {
  const { t } = useTranslation();
  const toast = useToast();

  // State for API data
  const [rateLimitStatus, setRateLimitStatus] = useState<RateLimitStatusResponse | null>(null);
  const [queueStats, setQueueStats] = useState<QueueStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch data from API
  const fetchData = useCallback(async (showRefreshing = false) => {
    try {
      if (showRefreshing) {
        setRefreshing(true);
      }

      // Fetch rate limit status
      const statusResponse = await client.get('/api/v1/rate-limits/status');
      setRateLimitStatus(statusResponse.data);

      // Fetch queue stats
      const queueResponse = await client.get('/api/v1/rate-limits/queue');
      setQueueStats(queueResponse.data);
    } catch (error) {
      console.error('Failed to fetch rate limit data:', error);
      toast.error('Failed to load rate limit data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  // Initial fetch
  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle refresh
  const handleRefresh = () => {
    fetchData(true);
    toast.info('Refreshing rate limit data...');
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
        return 'danger';
      default:
        return 'default';
    }
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return CheckCircle;
      case 'warning':
      case 'critical':
        return AlertCircle;
      default:
        return Activity;
    }
  };

  // Format time until breach
  const formatTimeUntilBreach = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      return `${mins}m`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  // Overview cards skeleton
  const renderSkeletonCards = () => (
    <>
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="col-span-1">
          <CardBody className="gap-2 p-4">
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-8 w-16 mb-1" />
            <Skeleton className="h-3 w-20" />
          </CardBody>
        </Card>
      ))}
    </>
  );

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Rate Limits</h2>
          <p className="text-sm text-default-500 mt-1">
            Monitor API rate limits and queue status
          </p>
        </div>
        <Button
          size="sm"
          color="primary"
          variant="flat"
          onPress={handleRefresh}
          isLoading={refreshing}
          startContent={<RefreshCw className="w-4 h-4" />}
        >
          Refresh
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {loading ? (
          renderSkeletonCards()
        ) : (
          <>
            {/* Overall Status */}
            <Card className="col-span-1">
              <CardBody className="gap-2 p-3 sm:p-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs sm:text-sm text-default-500">Status</div>
                  <Chip
                    color={getStatusColor(rateLimitStatus?.overall_status || 'healthy') as any}
                    size="sm"
                    variant="flat"
                  >
                    {rateLimitStatus?.overall_status || 'Unknown'}
                  </Chip>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {React.createElement(
                    getStatusIcon(rateLimitStatus?.overall_status || 'healthy'),
                    {
                      className: `w-5 h-5 ${
                        rateLimitStatus?.overall_status === 'healthy'
                          ? 'text-success'
                          : rateLimitStatus?.overall_status === 'warning'
                          ? 'text-warning'
                          : 'text-danger'
                      }`,
                    }
                  )}
                  <div className="text-lg sm:text-xl font-semibold">
                    {rateLimitStatus?.overall_status === 'healthy'
                      ? 'All Good'
                      : rateLimitStatus?.overall_status === 'warning'
                      ? 'Warning'
                      : 'Critical'}
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Total Accounts */}
            <Card className="col-span-1">
              <CardBody className="gap-2 p-3 sm:p-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs sm:text-sm text-default-500">Accounts</div>
                  <Users className="w-4 h-4 text-default-400" />
                </div>
                <div className="text-xl sm:text-2xl font-semibold">
                  {rateLimitStatus?.total_accounts || 0}
                </div>
                <div className="text-xs text-default-500">
                  {rateLimitStatus?.active_accounts || 0} active
                </div>
              </CardBody>
            </Card>

            {/* Rate Limited Accounts */}
            <Card className="col-span-1">
              <CardBody className="gap-2 p-3 sm:p-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs sm:text-sm text-default-500">Rate Limited</div>
                  <AlertCircle className="w-4 h-4 text-warning" />
                </div>
                <div className="text-xl sm:text-2xl font-semibold text-warning">
                  {rateLimitStatus?.rate_limited_accounts || 0}
                </div>
                <div className="text-xs text-default-500">
                  {rateLimitStatus?.total_accounts
                    ? `${((rateLimitStatus.rate_limited_accounts / rateLimitStatus.total_accounts) * 100).toFixed(0)}% of total`
                    : '0%'}
                </div>
              </CardBody>
            </Card>

            {/* Queue Size */}
            <Card className="col-span-1">
              <CardBody className="gap-2 p-3 sm:p-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs sm:text-sm text-default-500">Queue</div>
                  <Activity className="w-4 h-4 text-default-400" />
                </div>
                <div className="text-xl sm:text-2xl font-semibold">
                  {queueStats?.total_pending || 0}
                </div>
                <div className="text-xs text-default-500">
                  {queueStats?.total_processing || 0} processing
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="flex w-full flex-col">
        <Tabs
          aria-label="Rate Limit Options"
          classNames={{
            tabList: 'gap-2 flex-wrap sm:flex-nowrap',
            tab: 'text-xs sm:text-sm px-2 sm:px-4',
          }}
        >
          {/* Overview Tab */}
          <Tab key="overview" title="Overview">
            <Card>
              <CardBody className="p-4 sm:p-6">
                <h3 className="text-base sm:text-lg font-medium mb-4">System Overview</h3>

                {loading ? (
                  <div className="space-y-4">
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                  </div>
                ) : rateLimitStatus && rateLimitStatus.accounts.length > 0 ? (
                  <div className="space-y-4">
                    {/* Account Status List */}
                    {rateLimitStatus.accounts.map((account) => (
                      <div
                        key={`${account.account_id}-${account.endpoint_type}`}
                        className="p-4 rounded-lg bg-default-50 border border-default-200"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-medium text-sm">{account.account_id}</h4>
                              <Chip
                                size="sm"
                                variant="flat"
                                color={getStatusColor(account.status) as any}
                              >
                                {account.endpoint_type}
                              </Chip>
                            </div>
                            <div className="text-xs text-default-500 mt-1">
                              {account.current_usage} / {account.limit} requests
                            </div>
                          </div>
                          <div className="text-right">
                            <div
                              className={`text-sm font-semibold ${
                                account.status === 'critical'
                                  ? 'text-danger'
                                  : account.status === 'warning'
                                  ? 'text-warning'
                                  : 'text-success'
                              }`}
                            >
                              {account.usage_percent.toFixed(0)}%
                            </div>
                            {account.time_until_breach_seconds && (
                              <div className="text-xs text-default-500 flex items-center justify-end gap-1">
                                <Clock className="w-3 h-3" />
                                {formatTimeUntilBreach(account.time_until_breach_seconds)} until
                                breach
                              </div>
                            )}
                          </div>
                        </div>
                        <Progress
                          value={account.usage_percent}
                          color={getStatusColor(account.status) as any}
                          size="sm"
                          className="mt-2"
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-default-500">
                    No rate limit data available
                  </div>
                )}
              </CardBody>
            </Card>
          </Tab>

          {/* Queue Tab */}
          <Tab key="queue" title="Queue">
            <Card>
              <CardBody className="p-4 sm:p-6">
                <h3 className="text-base sm:text-lg font-medium mb-4">Queue Statistics</h3>

                {loading ? (
                  <div className="space-y-4">
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                  </div>
                ) : queueStats ? (
                  <div className="space-y-4">
                    {/* Priority Levels */}
                    {queueStats.stats_by_priority.map((stat) => (
                      <div
                        key={stat.priority_level}
                        className="p-4 rounded-lg bg-default-50 border border-default-200"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <Chip
                                size="sm"
                                variant="solid"
                                color={
                                  stat.priority_level === 'HIGH'
                                    ? 'danger'
                                    : stat.priority_level === 'MEDIUM'
                                    ? 'warning'
                                    : 'default'
                                }
                              >
                                {stat.priority_level}
                              </Chip>
                              <h4 className="font-medium text-sm">Priority</h4>
                            </div>
                            <div className="text-xs text-default-500 mt-1">
                              {stat.pending_requests} pending · {stat.processing_requests}{' '}
                              processing
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-semibold">
                              {stat.completed_last_minute}/min
                            </div>
                            {stat.average_wait_time_seconds > 0 && (
                              <div className="text-xs text-default-500 flex items-center justify-end gap-1">
                                <Clock className="w-3 h-3" />
                                {stat.average_wait_time_seconds.toFixed(1)}s avg wait
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Batch Configuration */}
                    <div className="p-4 rounded-lg bg-default-100 border border-default-200">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-xs text-default-500">Batch Size</div>
                          <div className="text-lg font-semibold">{queueStats.batch_size}</div>
                        </div>
                        <div>
                          <div className="text-xs text-default-500">Batch Timeout</div>
                          <div className="text-lg font-semibold">
                            {queueStats.batch_timeout_seconds}s
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-default-500">No queue data available</div>
                )}
              </CardBody>
            </Card>
          </Tab>

          {/* Settings Tab (placeholder for future implementation) */}
          <Tab key="settings" title="Settings">
            <Card>
              <CardBody className="p-4 sm:p-6">
                <h3 className="text-base sm:text-lg font-medium mb-4">Settings</h3>
                <div className="text-center py-8 text-default-500">
                  <div className="flex flex-col items-center gap-4">
                    <Zap className="w-12 h-12 text-default-300" />
                    <p>Rate limit settings management coming soon</p>
                    <p className="text-xs">
                      Configure alert thresholds and notification preferences
                    </p>
                  </div>
                </div>
              </CardBody>
            </Card>
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};

export default RateLimitDashboard;
