/**
 * Monitoring Page
 * 
 * Real-time мониторинг стримов с WebSocket обновлениями.
 * Показывает системные метрики, активные стримы и предупреждения.
 * 
 * Требует роль: admin, moderator
 */

import React, { useMemo } from 'react';
import { ResponsiveHeader } from '../components/layout';
import { useMonitoringWebSocket } from '../hooks/useMonitoringWebSocket';
import { StreamCard } from '../components/StreamCard';
import type { StreamState, AutoEndWarning } from '../hooks/useMonitoringWebSocket';

// === Types ===

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: string;
  color?: 'green' | 'blue' | 'yellow' | 'red' | 'gray';
}

// === Metric Card Component ===

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'blue',
}) => {
  const dotClasses: Record<NonNullable<MetricCardProps['color']>, string> = {
    green: 'bg-emerald-500',
    blue: 'bg-blue-500',
    yellow: 'bg-amber-500',
    red: 'bg-rose-500',
    gray: 'bg-[color:var(--color-text-muted)]',
  };

  return (
    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2 w-2 rounded-full ${dotClasses[color]}`} />
            <p className="text-sm font-medium text-[color:var(--color-text-muted)]">{title}</p>
          </div>
          <p className="text-2xl font-bold text-[color:var(--color-text)]">{value}</p>
          {subtitle && <p className="text-xs text-[color:var(--color-text-muted)] mt-1">{subtitle}</p>}
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
};

// === Connection Status Badge ===

const ConnectionStatus: React.FC<{ isConnected: boolean; error: string | null }> = ({
  isConnected,
  error,
}) => {
  if (error) {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-rose-500/10 border border-rose-500/20 text-rose-400">
        <span className="w-2 h-2 mr-2 rounded-full bg-rose-500 animate-pulse" />
        Error: {error}
      </span>
    );
  }

  if (!isConnected) {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-500/10 border border-amber-500/20 text-amber-400">
        <span className="w-2 h-2 mr-2 rounded-full bg-amber-500 animate-pulse" />
        Connecting...
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
      <span className="w-2 h-2 mr-2 rounded-full bg-emerald-500" />
      Connected
    </span>
  );
};

// === Main Monitoring Page ===

export const Monitoring: React.FC = () => {
  const {
    metrics,
    isConnected,
    error,
    streams: streamMap,
    autoEndWarnings,
    lastUpdate,
  } = useMonitoringWebSocket({
    autoReconnect: true,
    reconnectDelay: 3000,
  });

  // Convert streamStates Map to array
  const streams = useMemo((): StreamState[] => {
    return Array.from(streamMap.values());
  }, [streamMap]);

  // Get active streams only
  const activeStreams = useMemo(() => {
    return streams.filter(s => s.status !== 'stopped');
  }, [streams]);

  // Get warnings Map as array with channel IDs
  const warnings = useMemo((): Array<[number, AutoEndWarning]> => {
    return Array.from(autoEndWarnings.entries());
  }, [autoEndWarnings]);

  // Format last update time
  const lastUpdateFormatted = useMemo(() => {
    if (!lastUpdate) return 'Never';
    return new Date(lastUpdate).toLocaleTimeString();
  }, [lastUpdate]);

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Stream Monitoring</h1>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Real-time system metrics and stream status
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[color:var(--color-text-muted)]">
              Last update: {lastUpdateFormatted}
            </span>
            <ConnectionStatus isConnected={isConnected} error={error} />
          </div>
        </div>

      {/* System Metrics */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">System Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Active Streams"
            value={metrics?.streams?.active ?? 0}
            icon="📺"
            color={metrics?.streams?.active ? 'green' : 'gray'}
          />
          <MetricCard
            title="Total Listeners"
            value={metrics?.streams?.total_listeners ?? 0}
            icon="👥"
            color={metrics?.streams?.total_listeners ? 'blue' : 'gray'}
          />
          <MetricCard
            title="Queue Items"
            value={metrics?.queue?.total_items ?? 0}
            icon="📋"
            color="yellow"
          />
          <MetricCard
            title="WebSocket Connections"
            value={metrics?.websocket?.connections ?? 0}
            icon="🔌"
            color="blue"
          />
        </div>
      </div>

      {/* Auto-End Warnings */}
      {warnings.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-rose-400 mb-3">
            ⚠️ Auto-End Warnings ({warnings.length})
          </h2>
          <div className="rounded-2xl bg-rose-500/10 border border-rose-500/20 p-4">
            {warnings.map(([channelId, warning]) => (
              <div key={channelId} className="flex items-center justify-between py-2 border-b border-rose-500/20 last:border-0">
                <div>
                  <span className="font-medium text-rose-300">Channel {channelId}</span>
                  <p className="text-sm text-rose-300/90">
                    Stream will auto-end in {Math.floor(warning.remaining_seconds / 60)}m {warning.remaining_seconds % 60}s
                  </p>
                </div>
                <span className="text-2xl">⏱️</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Streams */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">
          Active Streams ({activeStreams.length})
        </h2>
        {activeStreams.length === 0 ? (
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-8 text-center">
            <span className="text-4xl mb-4 block">📺</span>
            <p className="text-[color:var(--color-text-muted)]">No active streams</p>
            <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
              Streams will appear here when they start playing
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeStreams.map(stream => (
              <StreamCard
                key={stream.channel_id}
                channelId={stream.channel_id}
                streamState={stream}
                autoEndWarning={autoEndWarnings.get(stream.channel_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* All Streams (including stopped) */}
      {streams.length > activeStreams.length && (
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--color-text-muted)] mb-3">
            Stopped Streams ({streams.length - activeStreams.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 opacity-60">
            {streams
              .filter(s => s.status === 'stopped')
              .map(stream => (
                <StreamCard
                  key={stream.channel_id}
                  channelId={stream.channel_id}
                  streamState={stream}
                />
              ))}
          </div>
        </div>
      )}

      {/* Debug Info (only in dev) */}
      {import.meta.env.DEV && (
        <div className="mt-8 p-4 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 text-xs font-mono text-[color:var(--color-text)]">
          <details>
            <summary className="cursor-pointer hover:text-white">Debug Info</summary>
            <pre className="mt-2 overflow-auto max-h-64">
              {JSON.stringify({ metrics, streamStates: Object.fromEntries(streamMap), autoEndWarnings: Object.fromEntries(autoEndWarnings) }, null, 2)}
            </pre>
          </details>
        </div>
      )}
      </main>
    </div>
  );
};

export default Monitoring;
