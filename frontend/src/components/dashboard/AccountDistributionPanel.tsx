import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  Power,
  PowerOff,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Skeleton,
  Chip,
  Progress,
} from '@heroui/react';
import { useToast } from '../../hooks/useToast';
import { client } from '../../api/client';

// Types matching backend API responses
interface AccountInfo {
  account_id: string;
  status: 'active' | 'rate_limited' | 'disabled' | 'failed' | 'banned';
  health: 'healthy' | 'degraded' | 'failed' | 'disabled';
  usage_percent: number;
  success_count: number;
  failure_count: number;
  last_used?: string;
}

interface AccountDistributionResponse {
  total_accounts: number;
  active_accounts: number;
  rate_limited_accounts: number;
  disabled_accounts: number;
  failed_accounts: number;
  accounts: AccountInfo[];
  selection_strategy: string;
  timestamp: string;
}

interface AccountCardProps {
  account: AccountInfo;
  onToggleStatus: (accountId: string, currentStatus: string) => void;
  isUpdating: boolean;
}

const AccountCard: React.FC<AccountCardProps> = ({ account, onToggleStatus, isUpdating }) => {
  const { t } = useTranslation();

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return {
          color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
          label: t('rateLimits.active', 'Активен'),
          icon: CheckCircle,
        };
      case 'rate_limited':
        return {
          color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
          label: t('rateLimits.rateLimited', 'Лимит'),
          icon: AlertCircle,
        };
      case 'disabled':
        return {
          color: 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20',
          label: t('rateLimits.disabled', 'Отключен'),
          icon: PowerOff,
        };
      case 'failed':
        return {
          color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
          label: t('rateLimits.failed', 'Ошибка'),
          icon: XCircle,
        };
      case 'banned':
        return {
          color: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
          label: t('rateLimits.banned', 'Заблокирован'),
          icon: XCircle,
        };
      default:
        return {
          color: 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20',
          label: status,
          icon: Activity,
        };
    }
  };

  const getHealthConfig = (health: string) => {
    switch (health) {
      case 'healthy':
        return { color: 'success', label: t('rateLimits.healthy', 'Здоров') };
      case 'degraded':
        return { color: 'warning', label: t('rateLimits.degraded', 'Деградирован') };
      case 'failed':
        return { color: 'danger', label: t('rateLimits.failed', 'Сбой') };
      case 'disabled':
        return { color: 'default', label: t('rateLimits.disabled', 'Отключен') };
      default:
        return { color: 'default', label: health };
    }
  };

  const statusConfig = getStatusConfig(account.status);
  const healthConfig = getHealthConfig(account.health);
  const StatusIcon = statusConfig.icon;

  const isDisabled = account.status === 'disabled' || account.status === 'banned' || account.status === 'failed';
  const successRate =
    account.success_count + account.failure_count > 0
      ? (account.success_count / (account.success_count + account.failure_count)) * 100
      : 100;

  const lastUsed = account.last_used
    ? new Date(account.last_used).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      layout
      className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:border-[color:var(--color-border-hover)] transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-4">
        {/* Account Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="font-semibold text-[color:var(--color-text)] truncate">
                  {account.account_id}
                </h4>
                <StatusIcon className={`w-4 h-4 ${statusConfig.color.split(' ')[1]}`} />
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-1 text-xs font-medium rounded-lg border ${statusConfig.color}`}
                >
                  {statusConfig.label}
                </span>
                <Chip size="sm" color={healthConfig.color as any} variant="flat">
                  {healthConfig.label}
                </Chip>
              </div>
            </div>

            {/* Toggle Button */}
            <Button
              size="sm"
              variant={isDisabled ? 'solid' : 'flat'}
              color={isDisabled ? 'success' : 'default'}
              onPress={() => onToggleStatus(account.account_id, account.status)}
              isDisabled={isUpdating || account.status === 'banned' || account.status === 'failed'}
              className="shrink-0"
              startContent={isDisabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
            >
              {isDisabled
                ? t('rateLimits.enable', 'Включить')
                : t('rateLimits.disable', 'Отключить')}
            </Button>
          </div>

          {/* Usage Progress */}
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-[color:var(--color-text-muted)] mb-1">
              <span>{t('rateLimits.usage', 'Использование')}</span>
              <span className="font-medium">{account.usage_percent.toFixed(1)}%</span>
            </div>
            <Progress
              value={account.usage_percent}
              color={
                account.usage_percent >= 90
                  ? 'danger'
                  : account.usage_percent >= 75
                  ? 'warning'
                  : 'success'
              }
              size="sm"
              className="w-full"
              showValueLabel={false}
            />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <div className="text-[color:var(--color-text-muted)] mb-0.5">
                {t('rateLimits.successes', 'Успешно')}
              </div>
              <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                {account.success_count.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[color:var(--color-text-muted)] mb-0.5">
                {t('rateLimits.failures', 'Ошибки')}
              </div>
              <div className="font-semibold text-rose-600 dark:text-rose-400">
                {account.failure_count.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[color:var(--color-text-muted)] mb-0.5">
                {t('rateLimits.successRate', 'Успех %')}
              </div>
              <div className="font-semibold text-[color:var(--color-text)]">
                {successRate.toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Last Used */}
          {lastUsed && (
            <div className="mt-3 text-xs text-[color:var(--color-text-muted)]">
              {t('rateLimits.lastUsed', 'Последнее использование')}: {lastUsed}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const AccountCardSkeleton: React.FC = () => (
  <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
    <div className="flex items-start gap-4">
      <div className="flex-1 space-y-3">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-32 rounded-lg" />
          <Skeleton className="h-6 w-16 rounded-lg" />
        </div>
        <Skeleton className="h-2 w-full rounded-lg" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-3 w-16 rounded-lg" />
          <Skeleton className="h-3 w-16 rounded-lg" />
          <Skeleton className="h-3 w-16 rounded-lg" />
        </div>
      </div>
    </div>
  </div>
);

export const AccountDistributionPanel: React.FC = () => {
  const { t } = useTranslation();
  const toast = useToast();

  // State
  const [accountData, setAccountData] = useState<AccountDistributionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingAccount, setUpdatingAccount] = useState<string | null>(null);

  // Fetch account distribution data
  const fetchAccounts = useCallback(async (showRefreshing = false) => {
    try {
      if (showRefreshing) {
        setRefreshing(true);
      }

      const response = await client.get('/api/v1/rate-limits/accounts');
      setAccountData(response.data);
    } catch (error) {
      console.error('Failed to fetch account distribution:', error);
      toast.error(t('rateLimits.fetchError', 'Ошибка загрузки данных аккаунтов'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast, t]);

  // Initial fetch
  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Handle refresh
  const handleRefresh = () => {
    fetchAccounts(true);
    toast.info(t('rateLimits.refreshing', 'Обновление данных...'));
  };

  // Handle account status toggle
  const handleToggleStatus = useCallback(
    async (accountId: string, currentStatus: string) => {
      try {
        setUpdatingAccount(accountId);

        // Determine new status
        const newStatus = currentStatus === 'disabled' ? 'active' : 'disabled';

        // Update account status
        await client.put(`/api/v1/rate-limits/accounts/${accountId}`, {
          status: newStatus,
        });

        toast.success(
          t(
            'rateLimits.statusUpdated',
            `Статус аккаунта обновлен: ${newStatus === 'active' ? 'включен' : 'отключен'}`
          )
        );

        // Refetch data to get updated state
        await fetchAccounts();
      } catch (error) {
        console.error('Failed to update account status:', error);
        toast.error(t('rateLimits.updateError', 'Ошибка обновления статуса'));
      } finally {
        setUpdatingAccount(null);
      }
    },
    [fetchAccounts, toast, t]
  );

  // Overview cards skeleton
  const renderSkeletonCards = () => (
    <>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-16 mb-1" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </>
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('rateLimits.accounts', 'Аккаунты')}</h2>
          <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
            {t('rateLimits.accountsDesc', 'Управление распределением нагрузки по аккаунтам')}
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
          {t('rateLimits.refresh', 'Обновить')}
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {loading ? (
          renderSkeletonCards()
        ) : (
          <>
            {/* Total Accounts */}
            <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between">
                <div className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                  {t('rateLimits.totalAccounts', 'Всего')}
                </div>
                <Users className="w-4 h-4 text-[color:var(--color-text-muted)]" />
              </div>
              <div className="text-xl sm:text-2xl font-semibold mt-1">
                {accountData?.total_accounts || 0}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)]">
                {accountData?.selection_strategy || 'N/A'}
              </div>
            </div>

            {/* Active Accounts */}
            <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between">
                <div className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                  {t('rateLimits.active', 'Активных')}
                </div>
                <CheckCircle className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-xl sm:text-2xl font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
                {accountData?.active_accounts || 0}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)]">
                {accountData?.total_accounts
                  ? `${((accountData.active_accounts / accountData.total_accounts) * 100).toFixed(0)}%`
                  : '0%'}
              </div>
            </div>

            {/* Rate Limited */}
            <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between">
                <div className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                  {t('rateLimits.rateLimited', 'Лимит')}
                </div>
                <AlertCircle className="w-4 h-4 text-amber-500" />
              </div>
              <div className="text-xl sm:text-2xl font-semibold text-amber-600 dark:text-amber-400 mt-1">
                {accountData?.rate_limited_accounts || 0}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)]">
                {t('rateLimits.throttled', 'Дросселируются')}
              </div>
            </div>

            {/* Disabled/Failed */}
            <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between">
                <div className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                  {t('rateLimits.inactive', 'Неактивных')}
                </div>
                <XCircle className="w-4 h-4 text-rose-500" />
              </div>
              <div className="text-xl sm:text-2xl font-semibold text-rose-600 dark:text-rose-400 mt-1">
                {(accountData?.disabled_accounts || 0) + (accountData?.failed_accounts || 0)}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)]">
                {t('rateLimits.unavailable', 'Недоступны')}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Accounts Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          // Skeleton loading
          Array.from({ length: 6 }).map((_, i) => <AccountCardSkeleton key={i} />)
        ) : !accountData || accountData.accounts.length === 0 ? (
          // Empty state
          <div className="col-span-full py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[color:var(--color-surface-muted)] flex items-center justify-center">
              <Users className="w-8 h-8 text-[color:var(--color-text-muted)]" />
            </div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('rateLimits.noAccounts', 'Нет аккаунтов')}
            </h3>
            <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
              {t('rateLimits.noAccountsDesc', 'В пуле пока нет аккаунтов')}
            </p>
          </div>
        ) : (
          // Account cards
          <AnimatePresence mode="popLayout">
            {accountData.accounts.map((account) => (
              <AccountCard
                key={account.account_id}
                account={account}
                onToggleStatus={handleToggleStatus}
                isUpdating={updatingAccount === account.account_id}
              />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
};
