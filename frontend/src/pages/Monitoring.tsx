/**
 * Monitoring Page
 * 
 * Real-time мониторинг стримов с WebSocket обновлениями.
 * Показывает системные метрики, активные стримы и предупреждения.
 * 
 * Требует роль: admin, moderator
 */

import React, { useMemo } from 'react';
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
  const colorClasses = {
    green: 'bg-green-50 border-green-200 text-green-800',
    blue: 'bg-blue-50 border-blue-200 text-blue-800',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    red: 'bg-red-50 border-red-200 text-red-800',
    gray: 'bg-gray-50 border-gray-200 text-gray-800',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium opacity-75">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {subtitle && <p className="text-xs opacity-60 mt-1">{subtitle}</p>}
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
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
        <span className="w-2 h-2 mr-2 rounded-full bg-red-500 animate-pulse" />
        Error: {error}
      </span>
    );
  }

  if (!isConnected) {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
        <span className="w-2 h-2 mr-2 rounded-full bg-yellow-500 animate-pulse" />
        Connecting...
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
      <span className="w-2 h-2 mr-2 rounded-full bg-green-500" />
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
    <div className="min-h-screen bg-gray-100 p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stream Monitoring</h1>
          <p className="text-sm text-gray-500">
            Real-time system metrics and stream status
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            Last update: {lastUpdateFormatted}
          </span>
          <ConnectionStatus isConnected={isConnected} error={error} />
        </div>
      </div>

      {/* System Metrics */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">System Metrics</h2>
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
          <h2 className="text-lg font-semibold text-red-700 mb-3">
            ⚠️ Auto-End Warnings ({warnings.length})
          </h2>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            {warnings.map(([channelId, warning]) => (
              <div key={channelId} className="flex items-center justify-between py-2 border-b border-red-100 last:border-0">
                <div>
                  <span className="font-medium text-red-800">Channel {channelId}</span>
                  <p className="text-sm text-red-600">
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
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          Active Streams ({activeStreams.length})
        </h2>
        {activeStreams.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <span className="text-4xl mb-4 block">📺</span>
            <p className="text-gray-500">No active streams</p>
            <p className="text-sm text-gray-400 mt-1">
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
          <h2 className="text-lg font-semibold text-gray-500 mb-3">
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
        <div className="mt-8 p-4 bg-gray-800 text-gray-300 rounded-lg text-xs font-mono">
          <details>
            <summary className="cursor-pointer hover:text-white">Debug Info</summary>
            <pre className="mt-2 overflow-auto max-h-64">
              {JSON.stringify({ metrics, streamStates: Object.fromEntries(streamMap), autoEndWarnings: Object.fromEntries(autoEndWarnings) }, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

export default Monitoring;
