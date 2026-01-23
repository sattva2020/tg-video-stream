import React from 'react';
import { AppLayout } from '@/components/layout';
import { SecurityDashboard } from '@/components/admin/SecurityDashboard';

export const SecurityDashboardPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl p-6">
        <SecurityDashboard />
      </div>
    </AppLayout>
  );
};

export default SecurityDashboardPage;
