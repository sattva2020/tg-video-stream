import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardBody, Chip, Button } from '@heroui/react';
import { Play, Pause, Radio, AlertCircle, RefreshCw, Clock, Video, Youtube as YoutubeIcon, Gamepad2 } from 'lucide-react';
import { streamingPlatformsApi, BroadcastDestination, PlatformType, DestinationStatus } from '../../api/streaming_platforms';
import { useToast } from '../../hooks/useToast';
import { Skeleton } from '../ui/Skeleton';
import { useTranslation } from 'react-i18next';

interface PlatformStatusProps {
  /** Channel ID to fetch platform statuses for */
  channelId: string;
  /** Auto-refresh interval in milliseconds. Set to 0 to disable. */
  refreshInterval?: number;
  /** Callback when platform is started */
  onPlatformStart?: (destinationId: string) => void;
  /** Callback when platform is stopped */
  onPlatformStop?: (destinationId: string) => void;
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

// Get platform icon component
function getPlatformIcon(platformType: PlatformType) {
  switch (platformType) {
    case 'youtube':
      return YoutubeIcon;
    case 'twitch':
      return Gamepad2;
    case 'twitter':
      return Video;
    case 'discord':
      return Video;
    default:
      return Radio;
  }
}

// Get platform color class
function getPlatformColor(platformType: PlatformType): string {
  switch (platformType) {
    case 'youtube':
      return 'bg-red-500/10 text-red-500';
    case 'twitch':
      return 'bg-purple-500/10 text-purple-500';
    case 'twitter':
      return 'bg-sky-500/10 text-sky-500';
    case 'discord':
      return 'bg-indigo-500/10 text-indigo-500';
    default:
      return 'bg-gray-500/10 text-gray-500';
  }
}

// Get status configuration
function getStatusConfig(status: DestinationStatus, enabled: boolean, hasError: boolean) {
  if (!enabled) {
    return {
      color: 'default' as const,
      icon: Pause,
      label: 'Отключено',
      bgClass: 'bg-gray-500/10',
      textClass: 'text-gray-500',
      pulseClass: '',
    };
  }

  if (hasError) {
    return {
      color: 'danger' as const,
      icon: AlertCircle,
      label: 'Ошибка',
      bgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      pulseClass: '',
    };
  }

  if (status === 'streaming') {
    return {
      color: 'success' as const,
      icon: Radio,
      label: 'В эфире',
      bgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      pulseClass: 'animate-pulse',
    };
  }

  return {
    color: 'default' as const,
    icon: Pause,
    label: 'Ожидание',
    bgClass: 'bg-gray-500/10',
    textClass: 'text-gray-500',
    pulseClass: '',
  };
}

interface PlatformStatusCardProps {
  destination: BroadcastDestination;
  platformName: string;
  platformType: PlatformType;
  onStart: () => void;
  onStop: () => void;
  isLoading?: boolean;
}

const PlatformStatusCard: React.FC<PlatformStatusCardProps> = ({
  destination,
  platformName,
  platformType,
  onStart,
  onStop,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const statusConfig = getStatusConfig(destination.status, destination.enabled, !!destination.last_error);
  const StatusIcon = statusConfig.icon;
  const PlatformIcon = getPlatformIcon(platformType);
  const platformColor = getPlatformColor(platformType);
  const isStreaming = destination.enabled && destination.status === 'streaming';

  return (
    <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        {/* Platform info */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={`p-2 rounded-lg ${platformColor} flex-shrink-0`}>
            <PlatformIcon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-[color:var(--color-text)] truncate">
                {platformName}
              </h4>
              <Chip
                color={statusConfig.color}
                size="sm"
                variant="flat"
                startContent={<span className={`w-2 h-2 rounded-full ${statusConfig.textClass} ${statusConfig.pulseClass}`} style={{ backgroundColor: 'currentColor' }} />}
              >
                {statusConfig.label}
              </Chip>
            </div>
            {destination.last_error && (
              <p className="text-sm text-red-500 mt-1 truncate">{destination.last_error}</p>
            )}
            {isStreaming && destination.platform_settings && typeof destination.platform_settings === 'object' && 'uptime_seconds' in destination.platform_settings && (
              <div className="flex items-center gap-1 mt-1 text-xs text-[color:var(--color-text-muted)]">
                <Clock className="w-3 h-3" />
                {formatUptime(Number(destination.platform_settings.uptime_seconds) || 0)}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {destination.enabled && destination.status !== 'streaming' && (
            <Button
              isIconOnly
              size="sm"
              color="success"
              variant="flat"
              onPress={onStart}
              isLoading={isLoading}
              isDisabled={isLoading}
            >
              <Play className="w-4 h-4" />
            </Button>
          )}
          {destination.status === 'streaming' && (
            <Button
              isIconOnly
              size="sm"
              color="danger"
              variant="flat"
              onPress={onStop}
              isLoading={isLoading}
              isDisabled={isLoading}
            >
              <Pause className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export const PlatformStatus: React.FC<PlatformStatusProps> = ({
  channelId,
  refreshInterval = 10000,
  onPlatformStart,
  onPlatformStop,
}) => {
  const { t } = useTranslation();
  const [destinations, setDestinations] = useState<BroadcastDestination[]>([]);
  const [platformNames, setPlatformNames] = useState<Record<string, { name: string; type: PlatformType }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const toast = useToast();

  // Fetch destinations for channel
  const fetchDestinations = useCallback(async () => {
    try {
      const data = await streamingPlatformsApi.listDestinations(channelId);
      setDestinations(data.destinations);
      setError(null);

      // Fetch platform details for each destination
      const platformDetails: Record<string, { name: string; type: PlatformType }> = {};
      await Promise.all(
        data.destinations.map(async (dest) => {
          try {
            const platform = await streamingPlatformsApi.getPlatform(dest.platform_id);
            platformDetails[dest.platform_id] = {
              name: platform.platform_name,
              type: platform.platform_type,
            };
          } catch {
            // If platform fetch fails, use fallback
            platformDetails[dest.platform_id] = {
              name: 'Unknown Platform',
              type: 'custom_rtmp',
            };
          }
        })
      );
      setPlatformNames(platformDetails);
    } catch (err) {
      console.error('Failed to fetch platform destinations:', err);
      setError('Не удалось получить статусы платформ');
      setDestinations([]);
    } finally {
      setLoading(false);
    }
  }, [channelId]);

  // Initial fetch
  useEffect(() => {
    fetchDestinations();
  }, [fetchDestinations]);

  // Polling for updates
  useEffect(() => {
    if (refreshInterval <= 0) return;

    const interval = setInterval(fetchDestinations, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval, fetchDestinations]);

  const handleRefresh = () => {
    setLoading(true);
    fetchDestinations();
    toast.info('Обновление статусов...');
  };

  const handleStartPlatform = async (destinationId: string) => {
    setActionLoading(prev => ({ ...prev, [destinationId]: true }));
    try {
      // Call the platform streamer service to start the platform
      // This would call the API endpoint to start the platform stream
      await streamingPlatformsApi.enableDestination(destinationId);
      toast.success('Трансляция на платформу запущена');
      await fetchDestinations();
      onPlatformStart?.(destinationId);
    } catch (err) {
      console.error('Failed to start platform stream:', err);
      toast.error('Не удалось запустить трансляцию');
    } finally {
      setActionLoading(prev => ({ ...prev, [destinationId]: false }));
    }
  };

  const handleStopPlatform = async (destinationId: string) => {
    setActionLoading(prev => ({ ...prev, [destinationId]: true }));
    try {
      // Call the platform streamer service to stop the platform
      // This would call the API endpoint to stop the platform stream
      await streamingPlatformsApi.disableDestination(destinationId);
      toast.success('Трансляция на платформу остановлена');
      await fetchDestinations();
      onPlatformStop?.(destinationId);
    } catch (err) {
      console.error('Failed to stop platform stream:', err);
      toast.error('Не удалось остановить трансляцию');
    } finally {
      setActionLoading(prev => ({ ...prev, [destinationId]: false }));
    }
  };

  // Loading skeleton
  if (loading && destinations.length === 0) {
    return (
      <div className="w-full rounded-3xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
        <Card shadow="none" className="bg-transparent">
          <CardBody className="gap-4 p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="w-8 h-8 rounded-lg" />
            </div>
            <div className="space-y-3">
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full rounded-3xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
      <Card shadow="none" className="bg-transparent">
        <CardBody className="gap-4 p-4 sm:p-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                {t('user.streaming.platformStatusTitle', 'Статусы платформ')}
              </h3>
              <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                {destinations.length} {t('user.streaming.platformsConnected', 'платформ подключено')}
              </p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors disabled:opacity-50"
              title="Обновить"
            >
              <RefreshCw className={`w-4 h-4 text-[color:var(--color-text-muted)] ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Error message */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Platform status cards */}
          {destinations.length === 0 ? (
            <div className="p-8 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] text-center">
              <Radio className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
              <p className="text-[color:var(--color-text-muted)]">
                {t('user.streaming.noPlatforms', 'Нет подключенных платформ')}
              </p>
              <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                {t('user.streaming.addPlatformsHint', 'Добавьте платформы для трансляции')}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {destinations.map((destination) => {
                const platformInfo = platformNames[destination.platform_id];
                if (!platformInfo) return null;

                return (
                  <PlatformStatusCard
                    key={destination.id}
                    destination={destination}
                    platformName={platformInfo.name}
                    platformType={platformInfo.type}
                    onStart={() => handleStartPlatform(destination.id)}
                    onStop={() => handleStopPlatform(destination.id)}
                    isLoading={actionLoading[destination.id]}
                  />
                );
              })}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default PlatformStatus;
