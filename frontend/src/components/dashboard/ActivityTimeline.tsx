import React from 'react';
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
  LucideIcon
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { ru, enUS } from 'date-fns/locale';

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
