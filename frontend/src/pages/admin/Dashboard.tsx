import React, { useState } from 'react';
import { adminApi } from '../../api/admin';
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
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">Admin Dashboard</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Control Panel */}
        <div className="bg-white p-6 rounded-lg shadow-md">
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
            <div className={`mt-4 p-3 rounded ${message.startsWith('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
              {message}
            </div>
          )}
        </div>

        {/* Metrics Panel */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <Metrics />
        </div>

        {/* Playlist Panel */}
        <div className="bg-white p-6 rounded-lg shadow-md lg:col-span-2">
          <Playlist />
        </div>

        {/* Logs Panel */}
        <div className="bg-white p-6 rounded-lg shadow-md lg:col-span-2">
          <Logs />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
