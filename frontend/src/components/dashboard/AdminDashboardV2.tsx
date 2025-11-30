import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, 
  UserCheck, 
  Clock, 
  Radio,
  LayoutDashboard
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Tabs, Tab } from '@heroui/react';
import { useNavigate } from 'react-router-dom';

// Components
import { StatCard } from './StatCard';
import { QuickActions } from './QuickActions';
import { ActivityTimeline } from './ActivityTimeline';
import { SystemHealth } from './SystemHealth';
import { StreamStatusCard } from './StreamStatusCard';
import { UserManagementPanel } from './UserManagementPanel';

// Hooks & API
import { useUserStats } from '../../hooks/useUsersQuery';
import { useStreamStatus } from '../../hooks/useChannelsQuery';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/queryClient';

// Mock activity data (would come from API in real implementation)
const mockActivityEvents = [
  {
    id: '1',
    type: 'user_registered' as const,
    message: 'Новый пользователь зарегистрировался',
    user: 'user@example.com',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
  },
  {
    id: '2',
    type: 'stream_started' as const,
    message: 'Трансляция запущена',
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
  },
  {
    id: '3',
    type: 'user_approved' as const,
    message: 'Пользователь одобрен',
    user: 'newuser@test.com',
    timestamp: new Date(Date.now() - 1000 * 60 * 60),
  },
  {
    id: '4',
    type: 'track_added' as const,
    message: 'Добавлен новый трек',
    details: 'Lofi Hip Hop Radio - Beats to Relax',
    timestamp: new Date(Date.now() - 1000 * 60 * 120),
  },
];

export const AdminDashboardV2: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  
  // State
  const [activeTab, setActiveTab] = useState('overview');
  const [isStreamLoading, setIsStreamLoading] = useState(false);

  // Data hooks
  const { stats, isLoading: statsLoading } = useUserStats();
  const { data: streamData } = useStreamStatus();
  
  const streamStatus = streamData?.status || 'unknown';
  const isStreamOnline = streamData?.online || false;

  // Stream control handlers
  const handleStartStream = useCallback(async () => {
    setIsStreamLoading(true);
    try {
      await adminApi.startStream();
      toast.success(t('admin.streamStarted', 'Трансляция запущена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      toast.error(t('admin.streamStartError', 'Не удалось запустить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  const handleStopStream = useCallback(async () => {
    if (!confirm(t('admin.confirmStop', 'Вы уверены, что хотите остановить трансляцию?'))) return;
    setIsStreamLoading(true);
    try {
      await adminApi.stopStream();
      toast.success(t('admin.streamStopped', 'Трансляция остановлена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      toast.error(t('admin.streamStopError', 'Не удалось остановить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  const handleRestartStream = useCallback(async () => {
    if (!confirm(t('admin.confirmRestart', 'Перезапустить трансляцию? Это прервёт текущее воспроизведение.'))) return;
    setIsStreamLoading(true);
    try {
      await adminApi.restartStream();
      toast.success(t('admin.streamRestarted', 'Трансляция перезапущена'));
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      toast.error(t('admin.streamRestartError', 'Не удалось перезапустить трансляцию'));
    } finally {
      setIsStreamLoading(false);
    }
  }, [toast, t, queryClient]);

  // Navigation handlers
  const handleOpenUsers = useCallback(() => setActiveTab('users'), []);
  const handleOpenPlaylist = useCallback(() => navigate('/playlist'), [navigate]);
  const handleOpenSettings = useCallback(() => navigate('/settings'), [navigate]);

  // Stats for cards
  const statCards = useMemo(() => [
    {
      title: t('admin.totalUsers', 'Всего пользователей'),
      value: stats.total,
      icon: Users,
      color: 'violet' as const,
      trend: { value: 12, label: t('admin.thisWeek', 'за неделю') },
    },
    {
      title: t('admin.pendingApproval', 'Ожидают одобрения'),
      value: stats.pending,
      icon: Clock,
      color: 'amber' as const,
      subtitle: stats.pending > 0 ? t('admin.requiresAction', 'Требует действия') : undefined,
    },
    {
      title: t('admin.approvedUsers', 'Активных'),
      value: stats.approved,
      icon: UserCheck,
      color: 'emerald' as const,
      trend: { value: 8, label: t('admin.thisMonth', 'за месяц') },
    },
    {
      title: t('admin.streamStatus', 'Трансляция'),
      value: isStreamOnline ? t('admin.online', 'В эфире') : t('admin.offline', 'Офлайн'),
      icon: Radio,
      color: isStreamOnline ? 'emerald' as const : 'rose' as const,
      subtitle: streamData?.uptime_seconds 
        ? `${t('admin.uptime', 'Аптайм')}: ${Math.floor(streamData.uptime_seconds / 3600)}h`
        : undefined,
    },
  ], [stats, isStreamOnline, streamData, t]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <LayoutDashboard className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[color:var(--color-text)]">
              {t('admin.dashboard', 'Панель управления')}
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('admin.welcomeBack', 'С возвращением, администратор')}
            </p>
          </div>
        </div>
        
        {/* Live indicator */}
        {isStreamOnline && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
              {t('admin.liveNow', 'В эфире')}
            </span>
          </motion.div>
        )}
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {statCards.map((card) => (
          <StatCard
            key={card.title}
            {...card}
            loading={statsLoading}
          />
        ))}
      </div>

      {/* Quick Actions */}
      <QuickActions
        onStartStream={handleStartStream}
        onStopStream={handleStopStream}
        onRestartStream={handleRestartStream}
        onOpenUsers={handleOpenUsers}
        onOpenPlaylist={handleOpenPlaylist}
        onOpenSettings={handleOpenSettings}
        streamStatus={streamStatus}
        isLoading={isStreamLoading}
      />

      {/* Main Content Tabs */}
      <Tabs
        aria-label="Admin sections"
        selectedKey={activeTab}
        onSelectionChange={(key) => setActiveTab(key as string)}
        classNames={{
          tabList: "gap-2 flex-wrap",
          tab: "text-sm",
        }}
      >
        <Tab key="overview" title={t('admin.overview', 'Обзор')}>
          <div className="grid lg:grid-cols-2 gap-6 mt-4">
            {/* Left Column */}
            <div className="space-y-6">
              <StreamStatusCard refreshInterval={10000} useWebSocket={true} />
              <SystemHealth
                cpuUsage={45}
                memoryUsage={62}
                diskUsage={38}
                networkLatency={24}
                dbConnections={12}
                maxDbConnections={100}
              />
            </div>
            
            {/* Right Column */}
            <div>
              <ActivityTimeline events={mockActivityEvents} />
            </div>
          </div>
        </Tab>

        <Tab key="users" title={t('admin.users', 'Пользователи')}>
          <div className="mt-4">
            <UserManagementPanel />
          </div>
        </Tab>

        <Tab key="stream" title={t('admin.stream', 'Трансляция')}>
          <div className="grid lg:grid-cols-2 gap-6 mt-4">
            <StreamStatusCard refreshInterval={5000} useWebSocket={true} />
            
            {/* Stream Controls Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-6 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]"
            >
              <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-6">
                {t('admin.streamControls', 'Управление трансляцией')}
              </h3>
              
              <div className="space-y-4">
                {/* Start/Stop Toggle */}
                <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-[color:var(--color-text)]">
                        {isStreamOnline ? t('admin.stopBroadcast', 'Остановить вещание') : t('admin.startBroadcast', 'Начать вещание')}
                      </h4>
                      <p className="text-sm text-[color:var(--color-text-muted)]">
                        {isStreamOnline 
                          ? t('admin.stopBroadcastDesc', 'Немедленно прекратить трансляцию')
                          : t('admin.startBroadcastDesc', 'Запустить видеотрансляцию')}
                      </p>
                    </div>
                    <button
                      onClick={isStreamOnline ? handleStopStream : handleStartStream}
                      disabled={isStreamLoading}
                      className={`
                        px-6 py-2.5 rounded-xl font-medium text-white
                        transition-all duration-200
                        disabled:opacity-50 disabled:cursor-not-allowed
                        ${isStreamOnline 
                          ? 'bg-gradient-to-r from-rose-500 to-red-600 hover:shadow-lg hover:shadow-rose-500/25' 
                          : 'bg-gradient-to-r from-emerald-500 to-green-600 hover:shadow-lg hover:shadow-emerald-500/25'}
                      `}
                    >
                      {isStreamLoading ? '...' : (isStreamOnline ? t('admin.stop', 'Стоп') : t('admin.start', 'Старт'))}
                    </button>
                  </div>
                </div>

                {/* Restart */}
                <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-[color:var(--color-text)]">
                        {t('admin.restartStream', 'Перезапуск трансляции')}
                      </h4>
                      <p className="text-sm text-[color:var(--color-text-muted)]">
                        {t('admin.restartStreamDesc', 'Перезапустить сервис вещания')}
                      </p>
                    </div>
                    <button
                      onClick={handleRestartStream}
                      disabled={!isStreamOnline || isStreamLoading}
                      className="px-6 py-2.5 rounded-xl font-medium text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {t('admin.restart', 'Перезапуск')}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </Tab>
      </Tabs>
    </div>
  );
};
