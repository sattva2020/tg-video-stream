/**
 * StreamPreview Component
 * Feature: 019-real-time-live-streaming-capabilities
 *
 * Компонент предпросмотра прямого эфира с видеоэлементом и метаданными.
 */

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Video,
  VideoOff,
  Loader2,
  AlertCircle,
  Eye,
  Clock,
  Settings
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface StreamPreviewProps {
  streamId: string;
  previewUrl?: string;
  thumbnailUrl?: string;
  isLoading?: boolean;
  error?: string;
  className?: string;
  onStreamClick?: () => void;
}

type StreamStatus = 'idle' | 'loading' | 'ready' | 'error';

export const StreamPreview: React.FC<StreamPreviewProps> = ({
  streamId,
  previewUrl,
  thumbnailUrl,
  isLoading = false,
  error,
  className = '',
  onStreamClick,
}) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [hasError, setHasError] = useState(false);
  const [playbackAttempted, setPlaybackAttempted] = useState(false);

  useEffect(() => {
    if (error) {
      setHasError(true);
      setStatus('error');
    } else if (isLoading) {
      setStatus('loading');
      setHasError(false);
    } else if (previewUrl) {
      setStatus('ready');
      setHasError(false);
    } else {
      setStatus('idle');
      setHasError(false);
    }
  }, [error, isLoading, previewUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !previewUrl || status !== 'ready') {
      return;
    }

    const attemptPlayback = async () => {
      if (playbackAttempted) {
        return;
      }

      setPlaybackAttempted(true);

      try {
        video.src = previewUrl;

        await new Promise<void>((resolve, reject) => {
          video.addEventListener('loadeddata', () => resolve(), { once: true });
          video.addEventListener('error', () => reject(), { once: true });

          setTimeout(() => reject(new Error('Video load timeout')), 10000);
        });

        await video.play().catch(() => {
          // Auto-play might be blocked, that's okay
        });
      } catch (err) {
        setHasError(true);
      }
    };

    attemptPlayback();

    return () => {
      if (video.src) {
        URL.revokeObjectURL(video.src);
        video.src = '';
      }
    };
  }, [previewUrl, status, playbackAttempted]);

  const handleClick = () => {
    if (status === 'ready' && onStreamClick) {
      onStreamClick();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-[color:var(--color-surface)] dark:bg-gray-800/50 rounded-2xl overflow-hidden border border-[color:var(--color-border)] dark:border-gray-700 shadow-lg ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[color:var(--color-border)] dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/10 rounded-xl">
            <Video className="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)] dark:text-white">
              {t('live.preview.title', 'Stream Preview')}
            </h3>
            {streamId && (
              <p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
                ID: {streamId}
              </p>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          {status === 'loading' && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-500/10 text-yellow-600 rounded-lg">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-xs font-medium">
                {t('live.preview.loading', 'Loading...')}
              </span>
            </div>
          )}

          {status === 'ready' && !hasError && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 text-green-600 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs font-medium">
                {t('live.preview.live', 'LIVE')}
              </span>
            </div>
          )}

          {(status === 'error' || hasError) && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-600 rounded-lg">
              <AlertCircle className="w-4 h-4" />
              <span className="text-xs font-medium">
                {t('live.preview.error', 'Error')}
              </span>
            </div>
          )}

          {status === 'idle' && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-500/10 text-gray-600 rounded-lg">
              <VideoOff className="w-4 h-4" />
              <span className="text-xs font-medium">
                {t('live.preview.offline', 'Offline')}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Video preview */}
      <div
        className={`relative bg-black aspect-video cursor-pointer ${status === 'ready' && !hasError ? 'group' : ''}`}
        onClick={handleClick}
      >
        {/* Thumbnail placeholder */}
        {thumbnailUrl && status === 'idle' && (
          <img
            src={thumbnailUrl}
            alt="Stream thumbnail"
            className="w-full h-full object-cover opacity-50"
          />
        )}

        {/* Loading state */}
        {status === 'loading' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-[color:var(--color-text-muted)]">
            <Loader2 className="w-12 h-12 mb-3 animate-spin text-blue-500" />
            <p className="text-sm">
              {t('live.preview.loadingStream', 'Loading stream preview...')}
            </p>
          </div>
        )}

        {/* Error state */}
        {(status === 'error' || hasError) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400">
            <AlertCircle className="w-12 h-12 mb-3" />
            <p className="text-sm font-medium">
              {t('live.preview.loadError', 'Failed to load stream preview')}
            </p>
            {error && (
              <p className="text-xs mt-2 text-center px-8 text-red-300">
                {error}
              </p>
            )}
          </div>
        )}

        {/* Idle state */}
        {status === 'idle' && !thumbnailUrl && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-[color:var(--color-text-muted)]">
            <VideoOff className="w-12 h-12 mb-3" />
            <p className="text-sm">
              {t('live.preview.noStream', 'No stream preview available')}
            </p>
          </div>
        )}

        {/* Video element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-full object-cover ${
            status !== 'ready' || hasError ? 'hidden' : ''
          }`}
        />

        {/* Overlay on hover */}
        {status === 'ready' && !hasError && (
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <div className="flex items-center gap-2 px-6 py-3 bg-white/90 dark:bg-gray-800/90 rounded-full">
              <Play className="w-5 h-5" />
              <span className="text-sm font-medium">
                {t('live.preview.viewFull', 'View Full Stream')}
              </span>
            </div>
          </div>
        )}

        {/* Live badge */}
        {status === 'ready' && !hasError && (
          <div className="absolute top-4 left-4 flex items-center gap-1.5 px-2 py-1 bg-red-600 rounded-full">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
            <span className="text-xs text-white font-medium">
              {t('live.preview.live', 'LIVE')}
            </span>
          </div>
        )}
      </div>

      {/* Metadata bar */}
      {status === 'ready' && !hasError && (
        <div className="flex items-center justify-between px-6 py-3 bg-[color:var(--color-surface-muted)] border-t border-[color:var(--color-border)] dark:border-gray-700">
          <div className="flex items-center gap-4 text-sm text-[color:var(--color-text-muted)]">
            <div className="flex items-center gap-1.5">
              <Eye className="w-4 h-4" />
              <span>
                {t('live.preview.viewers', '{{count}} viewers', { count: 0 })}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              <span>
                {t('live.preview.latency', '{{latency}}ms latency', { latency: 0 })}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="p-2 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
            title={t('live.preview.settings', 'Stream settings')}
          >
            <Settings className="w-4 h-4 text-[color:var(--color-text-muted)]" />
          </button>
        </div>
      )}
    </motion.div>
  );
};

const Play = ({ className }: { className?: string }) => (
  <svg
    className={className}
    fill="currentColor"
    viewBox="0 0 24 24"
  >
    <path d="M8 5v14l11-7z" />
  </svg>
);

export default StreamPreview;
