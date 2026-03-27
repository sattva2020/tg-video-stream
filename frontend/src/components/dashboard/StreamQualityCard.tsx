import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardBody, Chip, Skeleton, Button } from '@heroui/react';
import { Activity, Music, Video, RefreshCw, AlertTriangle, Gauge, Zap, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi, StreamQualityResponse } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { useAdaptiveStreamingWebSocket } from '../../hooks/useAdaptiveStreamingWebSocket';
import { AdaptiveStreamingStatus, QualityChangeEvent } from '../../types/adaptive-streaming';

interface StreamQualityCardProps {
  streamUrl?: string | null;
  title?: string;
  autoAnalyze?: boolean;
}

export const StreamQualityCard: React.FC<StreamQualityCardProps> = ({
  streamUrl,
  title,
  autoAnalyze = true
}) => {
  const { t } = useTranslation();
  const toast = useToast();
  const [quality, setQuality] = useState<StreamQualityResponse | null>(null);
  const [adaptiveStatus, setAdaptiveStatus] = useState<AdaptiveStreamingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [adaptiveLoading, setAdaptiveLoading] = useState(false);
  const [analyzedUrl, setAnalyzedUrl] = useState<string | null>(null);
  const [lastQualityChange, setLastQualityChange] = useState<QualityChangeEvent | null>(null);

  // WebSocket integration for real-time quality updates
  const {
    qualityChange: wsQualityChange,
    status: wsStatus,
    isConnected: wsConnected
  } = useAdaptiveStreamingWebSocket({
    streamId: streamUrl || undefined,
    enabled: !!streamUrl,
    onQualityChange: (event) => {
      setLastQualityChange(event);
      // Refresh adaptive status when quality changes
      if (streamUrl) {
        refreshAdaptiveStatus();
      }
    },
    onStatusUpdate: (statusData) => {
      // Update adaptive status when WebSocket sends status update
      if (adaptiveStatus) {
        setAdaptiveStatus({
          ...adaptiveStatus,
          current_quality: statusData.current_quality as any,
          current_bandwidth_kbps: statusData.current_bandwidth_kbps,
          smoothed_bandwidth_kbps: statusData.smoothed_bandwidth_kbps,
          is_adapting: statusData.is_adapting,
        });
      }
    }
  });

  const analyzeStream = useCallback(async (force = false) => {
    if (!streamUrl) return;

    setLoading(true);
    setAdaptiveLoading(true);
    try {
      // If we have a new URL, we might want to force analysis or use cache
      // For now, we default to use_cache=true unless forced
      const data = await adminApi.getStreamQuality(streamUrl, 10, !force);
      setQuality(data);
      setAnalyzedUrl(streamUrl);

      // Try to fetch adaptive streaming status (may fail if not configured)
      await refreshAdaptiveStatus();
    } catch (error) {
      // Don't show toast on auto-analyze to avoid spam
      if (force) {
        toast.error(t('quality.analysisFailed', 'Не удалось проанализировать поток'));
      }
    } finally {
      setLoading(false);
      setAdaptiveLoading(false);
    }
  }, [streamUrl, toast, t]);

  const refreshAdaptiveStatus = useCallback(async () => {
    if (!streamUrl) return;

    try {
      const encodedStreamId = encodeURIComponent(streamUrl);
      const adaptiveData = await adminApi.getAdaptiveStatus(encodedStreamId, 'desktop');
      setAdaptiveStatus(adaptiveData);
    } catch (adaptiveError) {
      // Adaptive streaming might not be configured for this stream
      setAdaptiveStatus(null);
    }
  }, [streamUrl]);

  useEffect(() => {
    if (autoAnalyze && streamUrl && streamUrl !== analyzedUrl) {
      analyzeStream(false);
    }
  }, [streamUrl, autoAnalyze, analyzedUrl, analyzeStream]);

  const getQualityColor = (q: string) => {
    switch (q?.toLowerCase()) {
      case 'ultra':
      case 'lossless':
      case 'high':
        return 'success';
      case 'medium':
        return 'warning';
      case 'low':
        return 'danger';
      default:
        return 'default';
    }
  };

  const formatBitrate = (kbps?: number) => {
    if (!kbps) return 'N/A';
    return `${kbps} kbps`;
  };

  if (!streamUrl) {
    return (
      <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
        <Card className="bg-transparent shadow-none border-none">
          <CardBody className="p-4 flex flex-row items-center gap-4">
            <div className="p-2 rounded-full bg-[color:var(--color-surface-muted)]">
              <Activity size={20} className="text-[color:var(--color-text-muted)]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[color:var(--color-text)]">
                {title || t('quality.title', 'Качество потока')}
              </h3>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                {t('quality.noStream', 'Нет активного потока для анализа')}
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
      <Card className="h-full bg-transparent shadow-none border-none">
        <CardBody className="p-6">
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Activity size={20} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                {title || t('quality.title', 'Качество потока')}
              </h3>
              <div className="flex items-center gap-2">
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  {quality?.overall_quality ? (
                    <span className={`text-${getQualityColor(quality.overall_quality)} capitalize`}>
                      {quality.overall_quality} Quality
                    </span>
                  ) : (
                    t('quality.analyzing', 'Анализ...')
                  )}
                </p>
                {wsConnected && (
                  <Chip size="sm" variant="flat" color="success" className="text-xs">
                    Live
                  </Chip>
                )}
              </div>
            </div>
          </div>
          <Button
            isIconOnly
            variant="light"
            onPress={() => analyzeStream(true)}
            isLoading={loading}
            className="text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)]"
          >
            <RefreshCw size={20} />
          </Button>
        </div>

        {loading && !quality ? (
          <div className="space-y-4">
            <Skeleton className="rounded-lg w-full h-12" />
            <Skeleton className="rounded-lg w-full h-24" />
            <Skeleton className="rounded-lg w-full h-24" />
          </div>
        ) : quality ? (
          <div className="space-y-6">
            {/* Quality Change Notification */}
            {lastQualityChange && (
              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 animate-pulse">
                <div className="flex items-center gap-2 text-sm">
                  <TrendingUp size={16} className="text-primary" />
                  <span className="font-medium text-[color:var(--color-text)]">
                    {t('quality.qualityChanged', 'Качество изменено')}
                  </span>
                  <Chip size="sm" variant="flat" color={getQualityColor(lastQualityChange.previous_quality || 'medium')}>
                    {lastQualityChange.previous_quality || 'N/A'}
                  </Chip>
                  <span className="text-[color:var(--color-text-secondary)]">→</span>
                  <Chip size="sm" variant="flat" color={getQualityColor(lastQualityChange.new_quality)}>
                    {lastQualityChange.new_quality}
                  </Chip>
                </div>
                {lastQualityChange.reason && (
                  <p className="text-xs text-[color:var(--color-text-secondary)] mt-1">
                    {t('quality.reason', 'Причина')}: {lastQualityChange.reason}
                  </p>
                )}
              </div>
            )}

            {/* Audio Metrics */}
            {quality.audio && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
                  <Music size={16} />
                  <span>{t('quality.audio', 'Аудио')}</span>
                  <Chip size="sm" variant="flat" color={getQualityColor(quality.audio.quality || 'medium')}>
                    {quality.audio.quality}
                  </Chip>
                </div>
                <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Codec</p>
                    <p className="font-mono text-sm">{quality.audio.codec || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Bitrate</p>
                    <p className="font-mono text-sm">{formatBitrate(quality.audio.bitrate_kbps)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Sample Rate</p>
                    <p className="font-mono text-sm">{quality.audio.sample_rate_hz ? `${quality.audio.sample_rate_hz} Hz` : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Channels</p>
                    <p className="font-mono text-sm">{quality.audio.channels || 'N/A'}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Video Metrics */}
            {quality.video && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
                  <Video size={16} />
                  <span>{t('quality.video', 'Видео')}</span>
                  <Chip size="sm" variant="flat" color={getQualityColor(quality.video.quality || 'medium')}>
                    {quality.video.quality}
                  </Chip>
                </div>
                <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Codec</p>
                    <p className="font-mono text-sm">{quality.video.codec || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Bitrate</p>
                    <p className="font-mono text-sm">{formatBitrate(quality.video.bitrate_kbps)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Resolution</p>
                    <p className="font-mono text-sm">{quality.video.resolution || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">FPS</p>
                    <p className="font-mono text-sm">{quality.video.fps || 'N/A'}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Performance Metrics */}
            <div className="space-y-3">
               <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
                  <Gauge size={16} />
                  <span>{t('quality.performance', 'Производительность')}</span>
               </div>
               <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Dropped Frames</p>
                    <p className={`font-mono text-sm ${quality.performance?.dropped_frames && quality.performance.dropped_frames > 0 ? 'text-danger' : ''}`}>
                        {quality.performance?.dropped_frames ?? 'N/A'}
                    </p>
                  </div>
                  <div>
                     <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">Speed</p>
                     <p className="font-mono text-sm">
                        {quality.performance?.speed ? `${quality.performance.speed}x` : 'N/A'}
                     </p>
                  </div>
               </div>
            </div>

            {/* Adaptive Streaming Status */}
            {adaptiveStatus && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
                    <Zap size={16} />
                    <span>{t('quality.adaptiveStreaming', 'Адаптивный стриминг')}</span>
                    {adaptiveStatus.adaptive_enabled && (
                      <Chip size="sm" variant="flat" color="success">
                        {t('quality.enabled', 'Включен')}
                      </Chip>
                    )}
                  </div>
                  {adaptiveStatus.is_adapting && (
                    <div className="flex items-center gap-1 text-xs text-primary animate-pulse">
                      <TrendingUp size={12} />
                      <span>{t('quality.adapting', 'Адаптация...')}</span>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.currentQuality', 'Текущее качество')}</p>
                    <p className="font-mono text-sm capitalize">{adaptiveStatus.current_quality}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.bandwidth', 'Пропускная способность')}</p>
                    <p className="font-mono text-sm">
                      {adaptiveStatus.current_bandwidth_kbps
                        ? `${Math.round(adaptiveStatus.current_bandwidth_kbps)} Kbps`
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.smoothedBandwidth', 'Сглаженная пропускная способность')}</p>
                    <p className="font-mono text-sm">
                      {adaptiveStatus.smoothed_bandwidth_kbps
                        ? `${Math.round(adaptiveStatus.smoothed_bandwidth_kbps)} Kbps`
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.qualityChanges', 'Изменения качества')}</p>
                    <p className="font-mono text-sm">{adaptiveStatus.total_quality_changes}</p>
                  </div>
                  {adaptiveStatus.recommended_quality && (
                    <>
                      <div>
                        <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.recommendedQuality', 'Рекомендуемое качество')}</p>
                        <p className="font-mono text-sm capitalize text-warning">{adaptiveStatus.recommended_quality}</p>
                      </div>
                      {adaptiveStatus.recommended_action && (
                        <div className="col-span-2">
                          <p className="text-xs text-[color:var(--color-text-secondary)] mb-1">{t('quality.recommendedAction', 'Рекомендуемое действие')}</p>
                          <p className="text-xs text-[color:var(--color-text)]">{adaptiveStatus.recommended_action}</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}

            {!quality.audio && !quality.video && (
              <div className="flex flex-col items-center justify-center py-8 text-[color:var(--color-text-secondary)]">
                <AlertTriangle size={32} className="mb-2 opacity-50" />
                <p>{t('quality.noData', 'Нет данных о потоке')}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-[color:var(--color-text-secondary)]">
            <p>{t('quality.waiting', 'Ожидание анализа...')}</p>
            <Button 
              size="sm" 
              variant="flat" 
              className="mt-4"
              onPress={() => analyzeStream(true)}
            >
              {t('quality.analyzeNow', 'Анализировать сейчас')}
            </Button>
          </div>
        )}
        </CardBody>
      </Card>
    </div>
  );
};
