import React, { useCallback, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Chip } from '@heroui/react';
import type { ChipProps } from '@heroui/react';
import {
  ShieldCheck,
  Play,
  Square,
  RefreshCw,
  ListMusic,
  SignalHigh,
  LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import { QuickActions } from './QuickActions';
import { StreamStatusCard } from './StreamStatusCard';
import { ActivityTimelineLive } from './ActivityTimeline';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { queryKeys } from '../../lib/queryClient';
import { useStreamStatus } from '../../hooks/useChannelsQuery';
import { usePlaylistWebSocket } from '../../hooks/usePlaylistWebSocket';
import { UserRole } from '../../types/user';

type StreamState = 'running' | 'stopped' | 'error' | 'unknown';

const normalizeStreamStatus = (status?: string): StreamState => {
  if (!status) return 'unknown';
  if (status === 'running' || status === 'online') return 'running';
  if (status === 'stopped' || status === 'offline') return 'stopped';
  if (status === 'error' || status === 'failed') return 'error';
  return 'unknown';
};

interface StreamControlActionsProps {
  isStreamOnline: boolean;
  status: StreamState;
  isLoading: boolean;
  onStart: () => Promise<void> | void;
  onStop: () => Promise<void> | void;
  onRestart: () => Promise<void> | void;
}

const StreamControlActions: React.FC<StreamControlActionsProps> = ({
  isStreamOnline,
  status,
  isLoading,
  onStart,
  onStop,
  onRestart,
}) => {
  const { t } = useTranslation();

  const actions: Array<{
    key: string;
    icon: LucideIcon;
    label: string;
    description: string;
    gradient: string;
    onClick: () => Promise<void> | void;
    disabled: boolean;
  }> = useMemo(() => (
    [
      {
        key: 'start',
        icon: Play,
        label: t('operator.startAction', 'Запуск'),
        description: t('operator.startActionDesc', 'Запустить эфир'),
        gradient: 'from-emerald-500 to-green-600',
        onClick: onStart,
        disabled: isStreamOnline,
      },
      {
        key: 'stop',
        icon: Square,
        label: t('operator.stopAction', 'Остановить'),
        description: t('operator.stopActionDesc', 'Остановить трансляцию'),
        gradient: 'from-rose-500 to-red-600',
        onClick: onStop,
        disabled: !isStreamOnline,
      },
      {
        key: 'restart',
        icon: RefreshCw,
        label: t('operator.restartAction', 'Перезапуск'),
        description: t('operator.restartActionDesc', 'Перезапустить сервис'),
        gradient: 'from-blue-500 to-indigo-600',
        onClick: onRestart,
        disabled: !isStreamOnline,
      },
    ]
  ), [t, isStreamOnline, onStart, onStop, onRestart]);

  const statusLabel = useMemo(() => {
    if (status === 'running') return t('operator.status.online', 'В эфире');
    if (status === 'stopped') return t('operator.status.offline', 'Офлайн');
    if (status === 'error') return t('operator.status.error', 'Ошибка');
    return t('operator.status.unknown', 'Статус неизвестен');
  }, [status, t]);

  const statusColor: ChipProps['color'] = status === 'running'
    ? 'success'
    : status === 'stopped'
      ? 'default'
      : status === 'error'
        ? 'danger'
        : 'warning';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]"
    >
      <div className="flex items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('operator.controlsTitle', 'Управление эфиром')}
          </h3>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            {t('operator.controlsSubtitle', 'Запускайте, останавливайте или перезапускайте эфир из одного места')}
          </p>
        </div>
        <Chip color={statusColor} variant="flat" radius="lg">
          {isLoading ? '...' : statusLabel}
        </Chip>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {actions.map((action) => {
          const Icon = action.icon;
          const disabled = action.disabled || isLoading;

          return (
            <button
              key={action.key}
              onClick={action.onClick}
              disabled={disabled}
              className={`
                relative overflow-hidden rounded-2xl p-4 text-left
                bg-[color:var(--color-surface)] border border-[color:var(--color-border)]
                hover:shadow-lg transition-shadow duration-200
                disabled:opacity-60 disabled:cursor-not-allowed
                group
              `}
            >
              <div className={`
                absolute inset-0 bg-gradient-to-br ${action.gradient}
                opacity-0 group-hover:opacity-10 transition-opacity duration-200
              `}
              />
              <div className="flex items-center gap-3">
                <div className={`
                  w-12 h-12 rounded-xl bg-gradient-to-br ${action.gradient}
                  flex items-center justify-center shadow-md
                  ${isLoading ? 'animate-pulse' : ''}
                `}
                >
                  <Icon className={`w-5 h-5 text-white ${isLoading ? 'animate-spin' : ''}`} />
                </div>
                <div className="relative z-10">
                  <div className="font-semibold text-[color:var(--color-text)]">
                    {action.label}
                  </div>
                  <p className="text-sm text-[color:var(--color-text-muted)]">
                    {action.description}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
};

const QueueOverviewCard: React.FC = () => {
  const { t } = useTranslation();
  const { items, isConnected, refresh } = usePlaylistWebSocket({ enabled: true });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const playingTrack = useMemo(() => items.find((item) => item.status === 'playing'), [items]);
  const queuedItems = useMemo(() => items.filter((item) => item.status === 'queued'), [items]);
  const upcoming = useMemo(() => queuedItems.slice(0, 3), [queuedItems]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    refresh();
    setTimeout(() => setIsRefreshing(false), 800);
  }, [refresh]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-muted)] mb-1">
            <ListMusic className="w-4 h-4" />
            {t('operator.queueTitle', 'Очередь трансляции')}
          </div>
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('operator.queueSubtitle', 'Следите за текущими и следующими треками')}
          </h3>
        </div>
        <button
          onClick={handleRefresh}
          className="p-2 rounded-xl border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
          title={t('operator.refreshQueue', 'Обновить очередь')}
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex items-center justify-between mt-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-[color:var(--color-text-muted)]">
            {t('operator.currentTrack', 'Сейчас играет')}
          </p>
          <p className="text-lg font-semibold text-[color:var(--color-text)] mt-1 truncate max-w-[240px]">
            {playingTrack?.title || t('operator.noTrackPlaying', 'Нет активного трека')}
          </p>
        </div>
        <Chip
          color={isConnected ? 'success' : 'default'}
          variant="flat"
          className="min-w-[140px] justify-center"
          startContent={<SignalHigh className={`w-4 h-4 ${isConnected ? 'text-emerald-500' : 'text-gray-400'}`} />}
        >
          {isConnected
            ? t('operator.queueConnected', 'WebSocket подключен')
            : t('operator.queueDisconnected', 'Нет соединения')}
        </Chip>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-[color:var(--color-text)]">
            {t('operator.upNext', 'Далее')}
          </span>
          <span className="text-xs text-[color:var(--color-text-muted)]">
            {t('operator.waitingCount', '{{count}} трек(ов) в очереди', { count: queuedItems.length })}
          </span>
        </div>
        {upcoming.length === 0 ? (
          <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] text-sm text-[color:var(--color-text-muted)]">
            {t('operator.noQueuedItems', 'Очередь пуста')}
          </div>
        ) : (
          <div className="space-y-3">
            {upcoming.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-3 p-3 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
              >
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                  <ListMusic className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[color:var(--color-text)] truncate">{item.title || item.url}</p>
                  <p className="text-xs text-[color:var(--color-text-muted)]">
                    {t('operator.position', 'Позиция')} #{item.position}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export const OperatorDashboard: React.FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: streamData } = useStreamStatus();
  const [isStreamLoading, setIsStreamLoading] = useState(false);

  const streamStatus = normalizeStreamStatus(streamData?.status);
  const isStreamOnline = Boolean(streamData?.online || streamStatus === 'running');

  const handleStartStream = useCallback(async () => {
    setIsStreamLoading(true);
    try {
      await adminApi.startStream();
      toast.success(t('admin.streamStarted', 'Трансляция запущена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch {
      toast.error(t('admin.streamStartError', 'Не удалось запустить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  const handleStopStream = useCallback(async () => {
    if (!confirm(t('admin.confirmStop', 'Вы уверены, что хотите остановить трансляцию?'))) {
      return;
    }
    setIsStreamLoading(true);
    try {
      await adminApi.stopStream();
      toast.success(t('admin.streamStopped', 'Трансляция остановлена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch {
      toast.error(t('admin.streamStopError', 'Не удалось остановить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  const handleRestartStream = useCallback(async () => {
    if (!confirm(t('admin.confirmRestart', 'Перезапустить трансляцию? Это прервёт текущее воспроизведение.'))) {
      return;
    }
    setIsStreamLoading(true);
    try {
      await adminApi.restartStream();
      toast.success(t('admin.streamRestarted', 'Трансляция перезапущена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch {
      toast.error(t('admin.streamRestartError', 'Не удалось перезапустить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  const handleRestricted = useCallback(() => {
    toast.warning(t('operator.noAccess', 'Нет доступа к этому разделу'));
  }, [toast, t]);

  const handleOpenPlaylist = useCallback(() => navigate('/playlist'), [navigate]);
  const handleOpenSettings = useCallback(() => navigate('/settings'), [navigate]);

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 shadow-lg shadow-emerald-500/30">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[color:var(--color-text)]">
              {t('operator.title', 'Панель оператора')}
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('operator.subtitle', 'Управляйте эфиром и очередью в реальном времени')}
            </p>
          </div>
        </div>
        <Chip color={isStreamOnline ? 'success' : 'default'} variant="flat" className="w-fit">
          {isStreamOnline
            ? t('operator.status.online', 'В эфире')
            : t('operator.status.offline', 'Офлайн')}
        </Chip>
      </motion.div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <StreamStatusCard refreshInterval={5000} useWebSocket />
          <StreamControlActions
            isStreamOnline={!!isStreamOnline}
            status={streamStatus}
            isLoading={isStreamLoading}
            onStart={handleStartStream}
            onStop={handleStopStream}
            onRestart={handleRestartStream}
          />
          <QuickActions
            onStartStream={handleStartStream}
            onStopStream={handleStopStream}
            onRestartStream={handleRestartStream}
            onOpenUsers={handleRestricted}
            onOpenPlaylist={handleOpenPlaylist}
            onOpenSettings={handleOpenSettings}
            streamStatus={streamStatus}
            isLoading={isStreamLoading}
            role={UserRole.OPERATOR}
          />
        </div>
        <div className="space-y-6">
          <ActivityTimelineLive maxItems={5} />
          <QueueOverviewCard />
        </div>
      </div>
    </div>
  );
};
