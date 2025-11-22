import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/user';
import { adminApi } from '../api/admin';
import UserBadge from '../components/UserBadge';

const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();

  const handleRestartStream = async () => {
    try {
      await adminApi.restartStream();
      alert('Stream restart initiated');
    } catch (error) {
      console.error('Failed to restart stream', error);
      alert('Failed to restart stream');
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      {user && (
        <div className="mb-4">
          <p className="flex items-center">
            Welcome, {user.full_name || user.email}!
            <UserBadge role={user.role} />
          </p>
        </div>
      )}
      
      {user?.role === UserRole.ADMIN && (
        <button
          onClick={handleRestartStream}
          className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded mr-2"
        >
          Restart Stream
        </button>
      )}

      <button
        onClick={logout}
        className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
      >
        Logout
      </button>
    </div>
  );
};

export default DashboardPage;