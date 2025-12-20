import React, { useState } from 'react';
import { adminApi } from '../../api/admin';
import { ResponsiveHeader } from '../../components/layout';
import Metrics from './Metrics';
import Logs from './Logs';
import Playlist from './Playlist';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    setLoading(true);
    setMessage(null);
    try {
      let res;
      if (action === 'start') res = await adminApi.startStream();
      else if (action === 'stop') res = await adminApi.stopStream();
      else if (action === 'restart') res = await adminApi.restartStream();
      
      setMessage(`Success: ${res.message}`);
    } catch (err: any) {
      setMessage(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <ResponsiveHeader />
      <main className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Control Panel */}
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
              <h2 className="text-xl font-semibold mb-4">Stream Control</h2>
          
          <div className="flex space-x-4">
            <button
              onClick={() => handleAction('start')}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              Start Stream
            </button>
            <button
              onClick={() => handleAction('stop')}
              disabled={loading}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              Stop Stream
            </button>
            <button
              onClick={() => handleAction('restart')}
              disabled={loading}
              className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              Restart Stream
            </button>
          </div>

          {message && (
            <div
              className={`mt-4 p-3 rounded-xl border ${
                message.startsWith('Error')
                  ? 'bg-red-500/10 border-red-500/20 text-red-300'
                  : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              }`}
            >
              {message}
            </div>
          )}
            </div>

            {/* Metrics Panel */}
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
              <Metrics />
            </div>

            {/* Playlist Panel */}
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6 lg:col-span-2">
              <Playlist />
            </div>

            {/* Logs Panel */}
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6 lg:col-span-2">
              <Logs />
            </div>
          </div>
        </div>
      </main>
    </>
  );
};

export default Dashboard;
