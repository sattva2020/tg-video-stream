import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ResponsiveHeader } from '../components/layout';
import { AdminDashboardV2 } from '../components/dashboard/AdminDashboardV2';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        <AdminDashboardV2 role={user?.role} />
      </main>
    </div>
  );
};

export default DashboardPage;