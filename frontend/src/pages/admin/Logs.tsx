import React, { useEffect, useState, useRef } from 'react';
import { adminApi } from '../../api/admin';

const Logs: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getLogs(100);
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Failed to fetch logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    // Optional: Auto-refresh logs
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Scroll to bottom when logs update
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">System Logs</h2>
        <button 
          onClick={fetchLogs} 
          disabled={loading}
          className="text-sm text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>
      
      <div className="logs-container bg-gray-900 text-gray-100 p-4 rounded h-64 overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-gray-500">No logs available.</div>
        ) : (
          logs.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap border-b border-gray-800 py-0.5">
              {line}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
};

export default Logs;
