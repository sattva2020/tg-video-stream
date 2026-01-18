import React from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import { UserManagementPanel } from '../components/dashboard/UserManagementPanel';

const UsersPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
            {t('users.title', 'Управление пользователями')}
          </h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            {t('users.subtitle', 'Просмотр и управление доступом пользователей')}
          </p>
        </div>

        <UserManagementPanel />
      </div>
    </AppLayout>
  );
};

export default UsersPage;
