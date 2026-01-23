import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/user';
import UserBadge from '../components/UserBadge';
import { ThemeToggle } from '../components/auth/ThemeToggle';
import { LanguageSwitcher } from '../components/auth/LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import { AdminDashboard } from '../components/dashboard/AdminDashboard';
import { UserDashboard } from '../components/dashboard/UserDashboard';

const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <header className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/50 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <h1 className="font-landing-serif text-2xl font-bold tracking-tight">Sattva Dashboard</h1>
            {user && <UserBadge role={user.role} />}
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitcher className="text-[color:var(--color-text)]" />
            <ThemeToggle className="text-[color:var(--color-text)]" />
            <button
              onClick={logout}
              className="rounded-lg bg-red-500/10 px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-500/20 transition-colors"
            >
              {t('Logout', 'Logout')}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {user?.role === UserRole.ADMIN ? <AdminDashboard /> : <UserDashboard />}
      </main>
    </div>
  );
};

export default DashboardPage;