import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardBody, Progress, Chip } from '@heroui/react';
import { Play, Pause, Radio, Clock, Music, AlertCircle, RefreshCw, HelpCircle } from 'lucide-react';
import { adminApi, StreamStatus } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { usePlaylistWebSocket } from '../../hooks/usePlaylistWebSocket';
import { Skeleton } from '../ui/Skeleton';

interface StreamStatusCardProps {
  /** Auto-refresh interval in milliseconds. Set to 0 to disable. */
  refreshInterval?: number;
  /** Whether to use WebSocket for real-time updates */
  useWebSocket?: boolean;
  /** Channel ID for WebSocket subscription */
  channelId?: string;
}

// Format uptime to human-readable string
function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

// Format duration to MM:SS
function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

export const StreamStatusCard: React.FC<StreamStatusCardProps> = ({
  refreshInterval = 10000,
  useWebSocket = true,
  channelId,
}) => {
  const [status, setStatus] = useState<StreamStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  // WebSocket integration for real-time updates
  const { streamStatus: wsStreamStatus, lastEvent } = usePlaylistWebSocket({
    channelId,
    enabled: useWebSocket,
  });

  // Fetch status from API
  const fetchStatus = useCallback(async () => {
    try {
      const data = await adminApi.getStreamStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch stream status:', err);
      setError('Не удалось получить статус стрима');
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Polling (fallback or supplement to WebSocket)
  useEffect(() => {
    if (refreshInterval <= 0) return;
    
    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval, fetchStatus]);

  // React to WebSocket events
  useEffect(() => {
    if (!lastEvent) return;
    
    // Refresh status on significant events
    if (['stream_started', 'stream_stopped', 'track_playing'].includes(lastEvent.type)) {
      fetchStatus();
    }
  }, [lastEvent, fetchStatus]);

  // Update status from WebSocket if available
  useEffect(() => {
    if (wsStreamStatus && wsStreamStatus !== 'unknown') {
      setStatus(prev => prev ? {
        ...prev,
        online: wsStreamStatus === 'online' || wsStreamStatus === 'running',
        status: wsStreamStatus as StreamStatus['status'],
      } : null);
    }
  }, [wsStreamStatus]);

  const handleRefresh = () => {
    setLoading(true);
    fetchStatus();
    toast.info('Обновление статуса...');
  };

  // Status indicator
  const getStatusConfig = () => {
    if (error || !status) {
      return {
        color: 'danger' as const,
        icon: AlertCircle,
        label: 'Ошибка',
        bgClass: 'bg-red-500/10',
        textClass: 'text-red-500',
        pulseClass: '',
      };
    }
    
    if (status.online && status.status === 'running') {
      return {
        color: 'success' as const,
        icon: Radio,
        label: 'В эфире',
        bgClass: 'bg-green-500/10',
        textClass: 'text-green-500',
        pulseClass: 'animate-pulse',
      };
    }
    
    if (status.status === 'stopped') {
      return {
        color: 'default' as const,
        icon: Pause,
        label: 'Остановлен',
        bgClass: 'bg-gray-500/10',
        textClass: 'text-gray-500',
        pulseClass: '',
      };
    }
    
    return {
      color: 'default' as const,
      icon: HelpCircle,
      label: 'Неизвестно',
      bgClass: 'bg-slate-500/10',
      textClass: 'text-slate-500',
      pulseClass: '',
    };
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  // Loading skeleton
  if (loading && !status) {
    return (
      <Card className="w-full">
        <CardBody className="gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Skeleton className="w-10 h-10 rounded-lg" />
              <div>
                <Skeleton className="h-5 w-40 mb-2" />
                <Skeleton className="h-4 w-24" />
              </div>
            </div>
            <Skeleton className="w-8 h-8 rounded-lg" />
          </div>
          
          <div className="p-3 rounded-lg bg-default-50 border border-default-200">
            <div className="flex items-start gap-3">
              <Skeleton className="w-10 h-10 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-3 w-20 mb-2" />
                <Skeleton className="h-5 w-48 mb-1" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-default-50">
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-6 w-8" />
            </div>
            <div className="p-3 rounded-lg bg-default-50">
              <Skeleton className="h-3 w-16 mb-2" />
              <Skeleton className="h-6 w-8" />
            </div>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardBody className="gap-4">
        {/* Header with status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${statusConfig.bgClass}`}>
              <StatusIcon className={`w-5 h-5 ${statusConfig.textClass} ${statusConfig.pulseClass}`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Статус трансляции</h3>
              <div className="flex items-center gap-2 mt-1">
                <Chip 
                  color={statusConfig.color} 
                  size="sm" 
                  variant="flat"
                  startContent={<span className={`w-2 h-2 rounded-full ${statusConfig.textClass} ${statusConfig.pulseClass}`} style={{ backgroundColor: 'currentColor' }} />}
                >
                  {statusConfig.label}
                </Chip>
                {status?.uptime_seconds ? (
                  <span className="text-xs text-default-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatUptime(status.uptime_seconds)}
                  </span>
                ) : null}
              </div>
            </div>
          </div>
          
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-default-100 transition-colors disabled:opacity-50"
            title="Обновить"
          >
            <RefreshCw className={`w-4 h-4 text-default-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Current track */}
        {status?.current_track && (
          <div className="p-3 rounded-lg bg-default-50 border border-default-200">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Music className="w-4 h-4 text-blue-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Play className="w-3 h-3 text-green-500" />
                  <span className="text-xs text-default-400">Сейчас играет</span>
                </div>
                <p className="font-medium truncate mt-1" title={status.current_track.title || undefined}>
                  {status.current_track.title || 'Без названия'}
                </p>
                <div className="flex items-center gap-3 mt-1 text-xs text-default-400">
                  <span className="uppercase">{status.current_track.type}</span>
                  <span>{formatDuration(status.current_track.duration)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Queue stats */}
        {status?.queue && (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-default-50">
              <div className="text-xs text-default-400">Всего в очереди</div>
              <div className="text-xl font-semibold mt-1">{status.queue.total}</div>
            </div>
            <div className="p-3 rounded-lg bg-default-50">
              <div className="text-xs text-default-400">Ожидает</div>
              <div className="text-xl font-semibold mt-1">{status.queue.queued}</div>
            </div>
          </div>
        )}

        {/* System metrics (if available) */}
        {status?.metrics && (
          <div className="space-y-3">
            <div className="text-xs text-default-400 uppercase tracking-wide">Система</div>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>CPU</span>
                  <span>{status.metrics.system.cpu_percent.toFixed(1)}%</span>
                </div>
                <Progress 
                  value={status.metrics.system.cpu_percent} 
                  size="sm" 
                  color={status.metrics.system.cpu_percent > 80 ? 'danger' : status.metrics.system.cpu_percent > 50 ? 'warning' : 'success'}
                />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Memory</span>
                  <span>{status.metrics.system.memory_percent.toFixed(1)}%</span>
                </div>
                <Progress 
                  value={status.metrics.system.memory_percent} 
                  size="sm" 
                  color={status.metrics.system.memory_percent > 80 ? 'danger' : status.metrics.system.memory_percent > 50 ? 'warning' : 'success'}
                />
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {(error || status?.error) && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error || status?.error}</span>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default StreamStatusCard;
