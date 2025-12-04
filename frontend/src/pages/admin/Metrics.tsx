import React, { useEffect, useState } from 'react';
import { adminApi, StreamMetrics } from '../../api/admin';

const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<StreamMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (error) return <div className="text-red-500">{error}</div>;
  if (!metrics) return <div>Loading metrics...</div>;

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
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {isOnline ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>

      {metrics.metrics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border p-4 rounded">
            <h3 className="font-medium text-gray-500 mb-2">System</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>CPU Usage:</span>
                <span className="font-mono">{formatPercent(systemCpuPercent)}</span>
              </div>
              <div className="flex justify-between">
                <span>Memory Usage:</span>
                <span className="font-mono">{formatPercent(systemMemoryPercent)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${systemCpuPercent ?? 0}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="border p-4 rounded">
            <h3 className="font-medium text-gray-500 mb-2">Streamer Process</h3>
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
        <div className="text-gray-500 italic">No metrics available (Streamer might be stopped)</div>
      )}
    </div>
  );
};

export default Metrics;
