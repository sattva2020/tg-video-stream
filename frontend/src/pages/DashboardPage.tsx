import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/user';
import { ResponsiveHeader } from '../components/layout';
import { AdminDashboardV2 } from '../components/dashboard/AdminDashboardV2';
import { UserDashboard } from '../components/dashboard/UserDashboard';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        {(user?.role === UserRole.ADMIN || user?.role === UserRole.SUPERADMIN) ? <AdminDashboardV2 /> : <UserDashboard />}
      </main>
    </div>
  );
};

export default DashboardPage;