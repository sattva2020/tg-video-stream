import React from 'react';
import { useAuth } from '../context/AuthContext';
import { AppLayout } from '../components/layout';
import { AdminDashboardV2 } from '../components/dashboard/AdminDashboardV2';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <AdminDashboardV2 role={user?.role} />
      </div>
    </AppLayout>
  );
};

export default DashboardPage;