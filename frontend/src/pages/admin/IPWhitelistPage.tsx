import React from 'react';
import { AppLayout } from '@/components/layout';
import { IPWhitelistManager } from '@/components/admin/IPWhitelistManager';

export const IPWhitelistPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl p-6">
        <IPWhitelistManager />
      </div>
    </AppLayout>
  );
};

export default IPWhitelistPage;
