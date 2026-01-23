import React from 'react';
import { AppLayout } from '../../components/layout';
import { AlertsNav, AlertGroups } from '../../components/alerts';

const GroupsPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <AlertsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Alerts: Groups</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            View grouped alerts that prevent notification spam for related issues.
          </p>
        </div>

        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Alert Groups</h2>
          <AlertGroups />
        </section>
      </div>
    </AppLayout>
  );
};

export default GroupsPage;
