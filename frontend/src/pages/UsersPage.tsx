import React from 'react';
import { useTranslation } from 'react-i18next';
import { ResponsiveHeader } from '../components/layout';
import UserManagementPanel from '../components/dashboard/UserManagementPanel';

const UsersPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
            {t('users.title', 'Управление пользователями')}
          </h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            {t('users.subtitle', 'Просмотр и управление доступом пользователей')}
          </p>
        </div>

        <UserManagementPanel />
      </main>
    </div>
  );
};

export default UsersPage;
