import React from 'react';
import { AppLayout } from '@/components/layout';
import { TwoFactorPolicy } from '@/components/admin/TwoFactorPolicy';

export const TwoFactorPolicyPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl p-6">
        <TwoFactorPolicy />
      </div>
    </AppLayout>
  );
};

export default TwoFactorPolicyPage;
