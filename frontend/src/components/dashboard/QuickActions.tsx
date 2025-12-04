import React from 'react';
import { motion } from 'framer-motion';
import { 
  Play, 
  Square, 
  RefreshCw, 
  Users, 
  ListMusic, 
  Settings,
  Zap,
  LucideIcon
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { UserRole } from '../../types/user';

type QuickActionId = 'stream-toggle' | 'restart' | 'users' | 'playlist' | 'settings';

interface QuickAction {
  id: QuickActionId;
  icon: LucideIcon;
  label: string;
  description: string;
  color: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

interface QuickActionsProps {
  onStartStream: () => void;
  onStopStream: () => void;
  onRestartStream: () => void;
  onOpenUsers: () => void;
  onOpenPlaylist: () => void;
  onOpenSettings: () => void;
  streamStatus: 'running' | 'stopped' | 'error' | 'unknown';
  isLoading?: boolean;
  role?: UserRole;
}

const QUICK_ACTIONS_BY_ROLE: Record<UserRole, readonly QuickActionId[]> = {
  [UserRole.SUPERADMIN]: ['stream-toggle', 'restart', 'users', 'playlist', 'settings'],
  [UserRole.ADMIN]: ['stream-toggle', 'restart', 'users', 'playlist', 'settings'],
  [UserRole.MODERATOR]: ['stream-toggle', 'restart', 'playlist'],
  [UserRole.OPERATOR]: ['stream-toggle', 'restart'],
  [UserRole.USER]: ['stream-toggle', 'restart'],
};

export const QuickActions: React.FC<QuickActionsProps> = ({
  onStartStream,
  onStopStream,
  onRestartStream,
  onOpenUsers,
  onOpenPlaylist,
  onOpenSettings,
  streamStatus,
  isLoading = false,
  role,
}) => {
  const { t } = useTranslation();
  const isRunning = streamStatus === 'running';
  const resolvedRole = role ?? UserRole.ADMIN;
  const allowedActions = new Set(QUICK_ACTIONS_BY_ROLE[resolvedRole] ?? QUICK_ACTIONS_BY_ROLE[UserRole.USER]);

  const actions: QuickAction[] = [
    {
      id: 'stream-toggle',
      icon: isRunning ? Square : Play,
      label: isRunning 
        ? t('admin.stopStream', 'Остановить') 
        : t('admin.startStream', 'Запустить'),
      description: isRunning 
        ? t('admin.stopStreamDesc', 'Остановить трансляцию')
        : t('admin.startStreamDesc', 'Запустить трансляцию'),
      color: isRunning 
        ? 'from-rose-500 to-red-600' 
        : 'from-emerald-500 to-green-600',
      onClick: isRunning ? onStopStream : onStartStream,
      loading: isLoading,
    },
    {
      id: 'restart',
      icon: RefreshCw,
      label: t('admin.restart', 'Перезапуск'),
      description: t('admin.restartDesc', 'Перезапустить сервис'),
      color: 'from-blue-500 to-indigo-600',
      onClick: onRestartStream,
      disabled: !isRunning,
    },
    {
      id: 'users',
      icon: Users,
      label: t('admin.users', 'Пользователи'),
      description: t('admin.usersDesc', 'Управление доступом'),
      color: 'from-violet-500 to-purple-600',
      onClick: onOpenUsers,
    },
    {
      id: 'playlist',
      icon: ListMusic,
      label: t('admin.playlist', 'Плейлист'),
      description: t('admin.playlistDesc', 'Управление треками'),
      color: 'from-amber-500 to-orange-600',
      onClick: onOpenPlaylist,
    },
    {
      id: 'settings',
      icon: Settings,
      label: t('admin.settings', 'Настройки'),
      description: t('admin.settingsDesc', 'Конфигурация системы'),
      color: 'from-gray-500 to-slate-600',
      onClick: onOpenSettings,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-amber-500" />
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('admin.quickActions', 'Быстрые действия')}
        </h3>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {actions
          .filter((action) => allowedActions.has(action.id))
          .map((action, index) => (
          <motion.button
            key={action.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={action.onClick}
            disabled={action.disabled || action.loading}
            className={`
              relative overflow-hidden rounded-xl p-4 text-left
              bg-[color:var(--color-panel)] border border-[color:var(--color-border)]
              hover:shadow-lg transition-shadow duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              group
            `}
          >
            {/* Gradient overlay on hover */}
            <div className={`
              absolute inset-0 bg-gradient-to-br ${action.color} 
              opacity-0 group-hover:opacity-10 transition-opacity duration-200
            `} />
            
            {/* Icon */}
            <div className={`
              w-10 h-10 rounded-lg bg-gradient-to-br ${action.color}
              flex items-center justify-center mb-3 shadow-md
              ${action.loading ? 'animate-pulse' : ''}
            `}>
              <action.icon className={`w-5 h-5 text-white ${action.loading ? 'animate-spin' : ''}`} />
            </div>
            
            {/* Text */}
            <div className="relative z-10">
              <div className="font-medium text-sm text-[color:var(--color-text)]">
                {action.label}
              </div>
              <div className="text-xs text-[color:var(--color-text-muted)] mt-0.5 hidden sm:block">
                {action.description}
              </div>
            </div>
          </motion.button>
          ))}
      </div>
    </div>
  );
};
