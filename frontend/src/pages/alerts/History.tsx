import React from 'react';
import { AppLayout } from '../../components/layout';
import { AlertsNav, AlertHistory } from '../../components/alerts';

const HistoryPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <AlertsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Alerts: History</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            View past alert instances with trigger values, timestamps, and resolution status.
          </p>
        </div>

        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Alert Instances</h2>
          <AlertHistory />
        </section>
      </div>
    </AppLayout>
  );
};

export default HistoryPage;
