import React, { useEffect, useState } from 'react';
import { adminApi, StreamMetrics, StreamQualityResponse } from '../../api/admin';
import StreamQualityBadge from '../../components/dashboard/StreamQualityBadge';
import StreamQualityChart from '../../components/dashboard/StreamQualityChart';
import StreamQualityAlertSettings from '../../components/dashboard/StreamQualityAlertSettings';

const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<StreamMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quality, setQuality] = useState<StreamQualityResponse | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState<string | null>(null);
  
  // Phase 3 tabs
  const [activeTab, setActiveTab] = useState<'quality' | 'trends' | 'alerts'>('quality');

  // Fetch system metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await adminApi.getMetrics();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch metrics');
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  // Fetch stream quality
  useEffect(() => {
    const fetchQuality = async () => {
      try {
        setQualityLoading(true);
        // Get current streaming URL from metrics if available
        const streamUrl = metrics?.current_stream_url || 'http://localhost:8081/stream';
        const data = await adminApi.getStreamQuality(streamUrl, 10, true);
        setQuality(data);
        setQualityError(null);
      } catch (err) {
        setQualityError('Failed to fetch stream quality');
        setQuality(null);
      } finally {
        setQualityLoading(false);
      }
    };

    if (metrics?.online) {
      fetchQuality();
      const interval = setInterval(fetchQuality, 15000); // Poll every 15s
      return () => clearInterval(interval);
    }
  }, [metrics?.online, metrics?.current_stream_url]);

  if (error) return <div className="text-red-500">{error}</div>;
  if (!metrics) return <div className="text-[color:var(--color-text-muted)]">Loading metrics...</div>;

  const isOnline = metrics.online;
  const sys = metrics.metrics?.system;
  const proc = metrics.metrics?.process;

  const systemCpuPercent = typeof sys?.cpu_percent === 'number' ? sys.cpu_percent : null;
  const systemMemoryPercent = typeof sys?.memory_percent === 'number' ? sys.memory_percent : null;
  const processCpuPercent = typeof proc?.cpu_percent === 'number' ? proc.cpu_percent : null;
  const processMemoryMb = ((proc?.memory_rss ?? 0) / 1024 / 1024).toFixed(0);

  const formatPercent = (value: number | null) => (value === null ? '—' : `${value.toFixed(1)}%`);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">System Metrics</h2>
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold border ${
            isOnline
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-red-500/10 border-red-500/20 text-red-300'
          }`}
        >
          {isOnline ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>

      {metrics.metrics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
            <h3 className="font-medium text-[color:var(--color-text-muted)] mb-2">System</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>CPU Usage:</span>
                <span className="font-mono">{formatPercent(systemCpuPercent)}</span>
              </div>
              <div className="flex justify-between">
                <span>Memory Usage:</span>
                <span className="font-mono">{formatPercent(systemMemoryPercent)}</span>
              </div>
              <div className="w-full bg-[color:var(--color-border)] rounded-full h-2.5">
                <div
                  className="bg-[color:var(--color-accent)] h-2.5 rounded-full"
                  style={{ width: `${systemCpuPercent ?? 0}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
            <h3 className="font-medium text-[color:var(--color-text-muted)] mb-2">Streamer Process</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>CPU Usage:</span>
                <span className="font-mono">{formatPercent(processCpuPercent)}</span>
              </div>
              <div className="flex justify-between">
                <span>Memory (RSS):</span>
                <span className="font-mono">{processMemoryMb} MB</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-[color:var(--color-text-muted)] italic">No metrics available (Streamer might be stopped)</div>
      )}

      {/* Feature 022 Phase 2 & 3: Stream Quality Monitoring */}
      {isOnline && (
        <div className="mt-6 border-t border-[color:var(--color-border)] pt-6">
          <h2 className="text-xl font-semibold mb-4">Stream Quality</h2>
          
          {/* Tab Navigation */}
          <div className="flex gap-4 mb-6 border-b border-[color:var(--color-border)]">
            <button
              onClick={() => setActiveTab('quality')}
              className={`px-4 py-2 font-medium border-b-2 transition ${
                activeTab === 'quality'
                  ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                  : 'border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]'
              }`}
            >
              Current Quality (Phase 2)
            </button>
            <button
              onClick={() => setActiveTab('trends')}
              className={`px-4 py-2 font-medium border-b-2 transition ${
                activeTab === 'trends'
                  ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                  : 'border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]'
              }`}
            >
              Trend Analysis (Phase 3)
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`px-4 py-2 font-medium border-b-2 transition ${
                activeTab === 'alerts'
                  ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                  : 'border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]'
              }`}
            >
              Alert Settings (Phase 3)
            </button>
          </div>

          {/* Quality Badge - Phase 2 */}
          {activeTab === 'quality' && (
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
              <StreamQualityBadge 
                quality={quality} 
                loading={qualityLoading}
                error={qualityError}
                compact={false}
              />
            </div>
          )}

          {/* Trend Chart - Phase 3 */}
          {activeTab === 'trends' && (
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
              <StreamQualityChart 
                streamUrl={metrics?.current_stream_url || 'http://localhost:8081/stream'}
                streamName={metrics?.current_stream_name || undefined}
                hours={24}
              />
            </div>
          )}

          {/* Alert Settings - Phase 3 */}
          {activeTab === 'alerts' && (
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
              <StreamQualityAlertSettings 
                streamUrl={metrics?.current_stream_url || 'http://localhost:8081/stream'}
                streamName={metrics?.current_stream_name || undefined}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Metrics;
