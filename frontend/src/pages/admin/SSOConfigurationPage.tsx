import React from 'react';
import { AppLayout } from '@/components/layout';
import { SSOConfiguration } from '@/components/admin/SSOConfiguration';

export const SSOConfigurationPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl p-6">
        <SSOConfiguration />
      </div>
    </AppLayout>
  );
};

export default SSOConfigurationPage;
