import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Activity, 
  UserPlus, 
  UserCheck, 
  UserX, 
  Play, 
  Square, 
  RefreshCw,
  Music,
  Trash2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  LucideIcon,
  Search,
  Filter,
  X
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { ru, enUS } from 'date-fns/locale';
import { useActivityEvents } from '../../hooks/useActivityEvents';
import type { ActivityEvent as ApiActivityEvent } from '../../types/system';

interface ActivityEvent {
  id: string;
  type: 'user_registered' | 'user_approved' | 'user_rejected' | 'stream_started' | 'stream_stopped' | 'stream_restarted' | 'track_added' | 'error' | 'success';
  message: string;
  timestamp: Date;
  user?: string;
  details?: string;
}

interface ActivityTimelineProps {
  events: ActivityEvent[];
  loading?: boolean;
  maxItems?: number;
}

const eventConfig: Record<string, { icon: LucideIcon; color: string; bgColor: string }> = {
  user_registered: {
    icon: UserPlus,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
  user_approved: {
    icon: UserCheck,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
  },
  user_rejected: {
    icon: UserX,
    color: 'text-rose-500',
    bgColor: 'bg-rose-500/10',
  },
  stream_started: {
    icon: Play,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
  },
  stream_stopped: {
    icon: Square,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
  },
  stream_restarted: {
    icon: RefreshCw,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
  track_added: {
    icon: Music,
    color: 'text-violet-500',
    bgColor: 'bg-violet-500/10',
  },
  track_removed: {
    icon: Trash2,
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
  },
  stream_error: {
    icon: AlertTriangle,
    color: 'text-rose-500',
    bgColor: 'bg-rose-500/10',
  },
  system_warning: {
    icon: AlertTriangle,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
  },
  system_error: {
    icon: XCircle,
    color: 'text-rose-500',
    bgColor: 'bg-rose-500/10',
  },
  error: {
    icon: AlertTriangle,
    color: 'text-rose-500',
    bgColor: 'bg-rose-500/10',
  },
  success: {
    icon: CheckCircle,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
  },
};

const SkeletonEvent: React.FC = () => (
  <div className="flex gap-3 animate-pulse">
    <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700" />
    <div className="flex-1 space-y-2">
      <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-3 w-1/2 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  </div>
);

/** Типы событий для фильтра */
const eventTypeOptions: { value: string; label: string; labelRu: string }[] = [
  { value: '', label: 'All events', labelRu: 'Все события' },
  { value: 'user_registered', label: 'Registration', labelRu: 'Регистрации' },
  { value: 'user_approved', label: 'Approvals', labelRu: 'Одобрения' },
  { value: 'user_rejected', label: 'Rejections', labelRu: 'Отклонения' },
  { value: 'stream_started', label: 'Stream started', labelRu: 'Запуск стрима' },
  { value: 'stream_stopped', label: 'Stream stopped', labelRu: 'Остановка стрима' },
  { value: 'stream_error', label: 'Stream errors', labelRu: 'Ошибки стрима' },
  { value: 'track_added', label: 'Tracks added', labelRu: 'Добавление треков' },
  { value: 'track_removed', label: 'Tracks removed', labelRu: 'Удаление треков' },
];

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  events,
  loading = false,
  maxItems = 10,
}) => {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'ru' ? ru : enUS;

  const displayEvents = events.slice(0, maxItems);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('admin.recentActivity', 'Последняя активность')}
          </h3>
        </div>
        <div className="space-y-4 p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonEvent key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('admin.recentActivity', 'Последняя активность')}
          </h3>
        </div>
        <div className="p-8 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center">
          <Clock className="w-12 h-12 mx-auto mb-3 text-[color:var(--color-text-muted)]" />
          <p className="text-[color:var(--color-text-muted)]">
            {t('admin.noActivity', 'Нет недавней активности')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('admin.recentActivity', 'Последняя активность')}
          </h3>
        </div>
        <span className="text-xs text-[color:var(--color-text-muted)] px-2 py-1 rounded-full bg-[color:var(--color-surface-muted)]">
          {events.length} {t('admin.events', 'событий')}
        </span>
      </div>
      
      <div className="relative rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] overflow-hidden">
        {/* Timeline line */}
        <div className="absolute left-[1.125rem] top-0 bottom-0 w-px bg-[color:var(--color-border)]" />
        
        <div className="divide-y divide-[color:var(--color-border)]">
          {displayEvents.map((event, index) => {
            const config = eventConfig[event.type] || eventConfig.success;
            const Icon = config.icon;
            
            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="relative flex gap-3 p-4 hover:bg-[color:var(--color-surface-muted)]/50 transition-colors"
              >
                {/* Icon */}
                <div className={`
                  relative z-10 flex-shrink-0 w-9 h-9 rounded-full 
                  ${config.bgColor} flex items-center justify-center
                  ring-4 ring-[color:var(--color-panel)]
                `}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[color:var(--color-text)]">
                    {event.message}
                    {event.user && (
                      <span className="font-medium"> — {event.user}</span>
                    )}
                  </p>
                  {event.details && (
                    <p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 truncate">
                      {event.details}
                    </p>
                  )}
                  <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                    {formatDistanceToNow(event.timestamp, { addSuffix: true, locale })}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
        
        {events.length > maxItems && (
          <div className="p-3 text-center border-t border-[color:var(--color-border)]">
            <button className="text-sm text-[color:var(--color-accent)] hover:underline">
              {t('admin.viewAll', 'Показать все')} ({events.length - maxItems} {t('admin.more', 'ещё')})
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * ActivityTimelineLive — компонент с реальными данными через useActivityEvents.
 * Spec: 015-real-system-monitoring
 * 
 * Автоматически обновляется каждые 30 секунд.
 * Показывает индикатор загрузки и обработку ошибок.
 * Поддерживает фильтрацию по типу события и поиск по тексту (US4).
 */
export const ActivityTimelineLive: React.FC<{ maxItems?: number }> = ({ maxItems = 10 }) => {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'ru' ? ru : enUS;
  
  // Состояние фильтров (US4: T036-T038)
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);
  
  const { 
    events, 
    total,
    isLoading, 
    isError, 
    error,
    refetch,
    isFetching,
  } = useActivityEvents({ 
    limit: maxItems,
    type: typeFilter || undefined,
    search: searchQuery || undefined,
  });
  
  // Обработчик поиска с debounce-like поведением
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
  };
  
  const clearFilters = () => {
    setTypeFilter('');
    setSearchQuery('');
    setSearchInput('');
  };
  
  const hasActiveFilters = typeFilter || searchQuery;

  // Состояние ошибки
  if (isError) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.activity.title', 'Последняя активность')}
          </h3>
        </div>
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
              <XCircle className="w-5 h-5" />
              <span className="text-sm font-medium">
                {t('dashboard.activity.unavailable', 'Данные временно недоступны')}
              </span>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-lg hover:bg-rose-500/10 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-rose-500 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
            {error instanceof Error ? error.message : t('dashboard.activity.tryAgain', 'Попробуйте обновить страницу')}
          </p>
        </div>
      </div>
    );
  }

  // Состояние загрузки
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.activity.title', 'Последняя активность')}
          </h3>
        </div>
        <div className="space-y-4 p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonEvent key={i} />
          ))}
        </div>
      </div>
    );
  }

  // Пустой список
  if (events.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.activity.title', 'Последняя активность')}
          </h3>
        </div>
        <div className="p-8 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center">
          <Clock className="w-12 h-12 mx-auto mb-3 text-[color:var(--color-text-muted)]" />
          <p className="text-[color:var(--color-text-muted)]">
            {t('dashboard.activity.noActivity', 'Нет недавней активности')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-violet-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.activity.title', 'Последняя активность')}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-2 py-1 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg transition-colors"
            >
              <X className="w-3 h-3" />
              {t('dashboard.activity.clearFilters', 'Сбросить')}
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters || hasActiveFilters
                ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400'
                : 'hover:bg-[color:var(--color-surface-muted)]'
            }`}
            title={t('dashboard.activity.filters', 'Фильтры')}
          >
            <Filter className="w-4 h-4" />
          </button>
          <span className="text-xs text-[color:var(--color-text-muted)] px-2 py-1 rounded-full bg-[color:var(--color-surface-muted)]">
            {total} {t('dashboard.activity.events', 'событий')}
          </span>
        </div>
      </div>
      
      {/* Фильтры (US4: T036-T037) */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="flex flex-col sm:flex-row gap-3 p-3 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
        >
          {/* Фильтр по типу */}
          <div className="flex-1">
            <label className="block text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('dashboard.activity.filterByType', 'Тип события')}
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
              {eventTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {i18n.language === 'ru' ? opt.labelRu : opt.label}
                </option>
              ))}
            </select>
          </div>
          
          {/* Поиск по тексту */}
          <div className="flex-1">
            <label className="block text-xs text-[color:var(--color-text-muted)] mb-1">
              {t('dashboard.activity.search', 'Поиск')}
            </label>
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder={t('dashboard.activity.searchPlaceholder', 'Поиск по сообщению...')}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-panel)] text-[color:var(--color-text)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-2 text-sm font-medium text-white bg-violet-500 hover:bg-violet-600 rounded-lg transition-colors"
              >
                {t('dashboard.activity.searchBtn', 'Найти')}
              </button>
            </form>
          </div>
        </motion.div>
      )}
      
      <div className="relative rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] overflow-hidden">
        {/* Timeline line */}
        <div className="absolute left-[1.125rem] top-0 bottom-0 w-px bg-[color:var(--color-border)]" />
        
        <div className="divide-y divide-[color:var(--color-border)]">
          {events.map((event: ApiActivityEvent, index: number) => {
            const config = eventConfig[event.type] || eventConfig.success;
            const Icon = config.icon;
            const timestamp = parseISO(event.created_at);
            
            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="relative flex gap-3 p-4 hover:bg-[color:var(--color-surface-muted)]/50 transition-colors"
              >
                {/* Icon */}
                <div className={`
                  relative z-10 flex-shrink-0 w-9 h-9 rounded-full 
                  ${config.bgColor} flex items-center justify-center
                  ring-4 ring-[color:var(--color-panel)]
                `}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[color:var(--color-text)]">
                    {event.message}
                    {event.user_email && (
                      <span className="font-medium"> — {event.user_email}</span>
                    )}
                  </p>
                  {event.details && (
                    <p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 truncate">
                      {typeof event.details === 'object' 
                        ? JSON.stringify(event.details) 
                        : String(event.details)}
                    </p>
                  )}
                  <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                    {formatDistanceToNow(timestamp, { addSuffix: true, locale })}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
        
        {total > maxItems && (
          <div className="p-3 text-center border-t border-[color:var(--color-border)]">
            <button className="text-sm text-[color:var(--color-accent)] hover:underline">
              {t('dashboard.activity.viewAll', 'Показать все')} ({total - maxItems} {t('dashboard.activity.more', 'ещё')})
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
