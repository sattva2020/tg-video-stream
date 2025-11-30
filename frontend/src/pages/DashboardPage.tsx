import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/user';
import UserBadge from '../components/UserBadge';
import { ThemeToggle } from '../components/auth/ThemeToggle';
import { ResponsiveHeader } from '../components/layout';
import { AdminDashboardV2 } from '../components/dashboard/AdminDashboardV2';
import { UserDashboard } from '../components/dashboard/UserDashboard';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      {/* Sub-header with user info and theme toggle */}
      <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-end gap-3">
            {user && <UserBadge role={user.role} />}
            <ThemeToggle className="text-[color:var(--color-text)]" />
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        {(user?.role === UserRole.ADMIN || user?.role === UserRole.SUPERADMIN) ? <AdminDashboardV2 /> : <UserDashboard />}
      </main>
    </div>
  );
};

export default DashboardPage;