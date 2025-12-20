import React, { useEffect, useState } from 'react';
import { Card, CardBody, Chip, Skeleton, Button } from '@heroui/react';
import { Activity, Music, Video, RefreshCw, AlertTriangle, Gauge } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi, StreamQualityResponse } from '../../api/admin';
import { useToast } from '../../hooks/useToast';

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
  const [loading, setLoading] = useState(false);
  const [analyzedUrl, setAnalyzedUrl] = useState<string | null>(null);

  const analyzeStream = async (force = false) => {
    if (!streamUrl) return;
    
    setLoading(true);
    try {
      // If we have a new URL, we might want to force analysis or use cache
      // For now, we default to use_cache=true unless forced
      const data = await adminApi.getStreamQuality(streamUrl, 10, !force);
      setQuality(data);
      setAnalyzedUrl(streamUrl);
      
      if (force) {
        toast.success(t('quality.analysisComplete', 'Анализ завершен'));
      }
    } catch (error) {
      console.error('Quality analysis failed:', error);
      // Don't show toast on auto-analyze to avoid spam
      if (force) {
        toast.error(t('quality.analysisFailed', 'Не удалось проанализировать поток'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoAnalyze && streamUrl && streamUrl !== analyzedUrl) {
      analyzeStream(false);
    }
  }, [streamUrl, autoAnalyze, analyzedUrl]);

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
      <Card className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
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
    );
  }

  return (
    <Card className="h-full rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
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
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                {quality?.overall_quality ? (
                  <span className={`text-${getQualityColor(quality.overall_quality)} capitalize`}>
                    {quality.overall_quality} Quality
                  </span>
                ) : (
                  t('quality.analyzing', 'Анализ...')
                )}
              </p>
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
  );
};
