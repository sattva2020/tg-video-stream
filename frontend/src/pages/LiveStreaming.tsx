import React, { useState } from 'react';
import { Broadcast, Radio, UserPlus, Settings, Eye, AlertCircle } from 'lucide-react';
import { AppLayout } from '../components/layout';
import { useTranslation } from 'react-i18next';
import { LatencyMonitor } from '../components/live';

interface LiveStream {
  id: string;
  title: string;
  status: 'idle' | 'active' | 'paused' | 'stopped' | 'error';
  ingestion_type: 'rtmp' | 'srt' | 'webrtc_camera' | 'webrtc_screen';
  viewer_count: number;
  latency_ms: number;
  chat_id: number;
  created_at: string;
}

const LiveStreaming: React.FC = () => {
  const { t } = useTranslation();
  const [streams, setStreams] = useState<LiveStream[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Placeholder data - will be replaced with API calls in subtask 6-7
  const placeholderStreams: LiveStream[] = [];

  const handleCreateStream = () => {
    // TODO: Implement in subtask 6-2 (CameraCapture) and 6-7 (API client)
    console.log('Create stream clicked');
  };

  const handleInviteGuest = () => {
    // TODO: Implement in subtask 6-3 (GuestManager)
    console.log('Invite guest clicked');
  };

  const getStatusColor = (status: LiveStream['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      default:
        return 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]';
    }
  };

  const getIngestionIcon = (type: LiveStream['ingestion_type']) => {
    switch (type) {
      case 'rtmp':
      case 'srt':
        return <Radio className="w-4 h-4" />;
      case 'webrtc_camera':
      case 'webrtc_screen':
        return <Broadcast className="w-4 h-4" />;
      default:
        return <Radio className="w-4 h-4" />;
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header with actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
            <Broadcast className="w-6 h-6 sm:w-8 sm:h-8 text-red-500" />
            {t('live.title', 'Live Streaming')}
          </h1>

          {/* Action buttons - stack on mobile */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full sm:w-auto">
            <button
              onClick={handleInviteGuest}
              className="bg-[color:var(--color-surface-muted)] hover:bg-[color:var(--color-border)] text-[color:var(--color-text)] px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm sm:text-base"
            >
              <UserPlus className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('live.inviteGuest', 'Invite Guest')}
            </button>
            <button
              onClick={handleCreateStream}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm sm:text-base"
            >
              <Broadcast className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('live.goLive', 'Go Live')}
            </button>
          </div>
        </div>

        {/* Loading state */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-[color:var(--color-panel)] rounded-xl shadow-sm border border-[color:var(--color-border)] overflow-hidden animate-pulse"
              >
                <div className="p-4 sm:p-5">
                  <div className="h-6 bg-[color:var(--color-surface-muted)] rounded mb-3"></div>
                  <div className="h-4 bg-[color:var(--color-surface-muted)] rounded mb-2 w-2/3"></div>
                  <div className="h-4 bg-[color:var(--color-surface-muted)] rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : streams.length === 0 ? (
          /* Empty state */
          <div className="text-center py-8 sm:py-12 bg-[color:var(--color-surface-muted)] rounded-xl border border-dashed border-[color:var(--color-border)]">
            <Broadcast className="w-12 h-12 mx-auto mb-4 text-[color:var(--color-text-muted)]" />
            <p className="text-[color:var(--color-text-muted)] text-base sm:text-lg mb-4">
              {t('live.noStreams', 'No active live streams')}
            </p>
            <p className="text-sm text-[color:var(--color-text-muted)] mb-6 max-w-md mx-auto">
              {t('live.noStreamsHint', 'Start a live stream to broadcast real-time content to your Telegram channels.')}
            </p>
            <button
              onClick={handleCreateStream}
              className="mt-4 bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg inline-flex items-center justify-center gap-2 transition-colors"
            >
              <Broadcast className="w-5 h-5" />
              {t('live.startFirstStream', 'Start Your First Stream')}
            </button>
          </div>
        ) : (
          /* Streams grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {streams.map((stream) => (
              <div
                key={stream.id}
                className="bg-[color:var(--color-panel)] rounded-xl shadow-sm border border-[color:var(--color-border)] overflow-hidden"
              >
                <div className="p-4 sm:p-5">
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="min-w-0 flex-1 mr-3">
                      <div className="flex items-center gap-2 mb-1">
                        {getIngestionIcon(stream.ingestion_type)}
                        <h3 className="text-lg sm:text-xl font-semibold text-[color:var(--color-text)] truncate">
                          {stream.title}
                        </h3>
                      </div>
                      <p className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                        ID: {stream.chat_id}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span
                        className={`px-2 sm:px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(
                          stream.status
                        )}`}
                      >
                        {stream.status.toUpperCase()}
                      </span>
                      {stream.status === 'error' && (
                        <div className="flex items-center gap-1 text-xs text-red-500">
                          <AlertCircle className="w-3 h-3" />
                          <span>Connection lost</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Stream metrics */}
                  <div className="space-y-1.5 sm:space-y-2 text-xs sm:text-sm text-[color:var(--color-text-muted)] mb-4 sm:mb-6">
                    <div className="flex justify-between">
                      <span className="flex items-center gap-1.5">
                        <Eye className="w-4 h-4" />
                        {t('live.viewers', 'Viewers')}:
                      </span>
                      <span className="font-medium text-[color:var(--color-text)]">
                        {stream.viewer_count}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>{t('live.latency', 'Latency')}:</span>
                      <span className="font-medium text-[color:var(--color-text)]">
                        {stream.latency_ms}ms
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>{t('live.source', 'Source')}:</span>
                      <span className="font-medium text-[color:var(--color-text)] uppercase">
                        {stream.ingestion_type}
                      </span>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 sm:gap-3">
                    {stream.status === 'active' ? (
                      <button
                        className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 transition-colors text-sm"
                      >
                        <Settings className="w-4 h-4" />
                        <span className="hidden xs:inline">{t('live.stop', 'Stop')}</span>
                      </button>
                    ) : (
                      <button
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 transition-colors text-sm"
                      >
                        <Broadcast className="w-4 h-4" />
                        <span className="hidden xs:inline">{t('live.start', 'Start')}</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info section */}
        <div className="mt-8 bg-[color:var(--color-surface-muted)] rounded-xl p-6 border border-[color:var(--color-border)]">
          <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            {t('live.gettingStarted', 'Getting Started with Live Streaming')}
          </h2>
          <div className="space-y-3 text-sm text-[color:var(--color-text-muted)]">
            <p>
              <strong className="text-[color:var(--color-text)]">{t('live.rtmpTitle', 'RTMP/SRT Ingestion:')}</strong> {t('live.rtmpDesc', 'Stream from OBS, VLC, or any RTMP-compatible software to your Telegram channels.')}
            </p>
            <p>
              <strong className="text-[color:var(--color-text)]">{t('live.webrtcTitle', 'Browser Capture:')}</strong> {t('live.webrtcDesc', 'Go live directly from your browser using your camera and microphone.')}
            </p>
            <p>
              <strong className="text-[color:var(--color-text)]">{t('live.guestsTitle', 'Guest Co-Hosting:')}</strong> {t('live.guestsDesc', 'Invite guests to join your live stream with camera, microphone, and screen sharing.')}
            </p>
            <p>
              <strong className="text-[color:var(--color-text)]">{t('live.switchingTitle', 'Stream Switching:')}</strong> {t('live.switchingDesc', 'Seamlessly switch between live and pre-recorded content without interrupting your broadcast.')}
            </p>
          </div>
        </div>

        {/* Latency Monitor Demo */}
        <div className="mt-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <LatencyMonitor
              currentLatency={120}
              history={[100, 110, 105, 120, 115, 130, 125, 118, 122, 119, 121, 117, 123, 120, 118, 122, 120, 119, 121, 120]}
              thresholdWarning={200}
              thresholdCritical={500}
              updateInterval={1000}
            />
            <LatencyMonitor
              currentLatency={350}
              history={[300, 310, 320, 330, 340, 350, 360, 355, 350, 345, 350, 355, 350, 348, 352, 350, 349, 351, 350, 350]}
              thresholdWarning={200}
              thresholdCritical={500}
              updateInterval={1000}
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default LiveStreaming;
