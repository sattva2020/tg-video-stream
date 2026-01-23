import React from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import { WebhookList } from '../components/webhooks/WebhookList';
import { Webhook, Bell } from 'lucide-react';

const WebhooksPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <div className="mx-auto max-w-3xl py-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
                <Webhook className="w-6 h-6 text-[color:var(--color-accent)]" />
              </div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
                Webhooks
              </h1>
            </div>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Configure webhook subscriptions to receive real-time event notifications
            </p>
          </div>
        </div>

        {/* Info Banner */}
        <div className="mx-auto max-w-3xl py-6">
          <div className="mb-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <Bell className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-500 mb-1">Real-Time Event Notifications</p>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Webhooks allow external systems to receive instant notifications when events occur on your streams. Configure event types, verify signatures with HMAC-SHA256, and view delivery logs.
                </p>
              </div>
            </div>
          </div>

          {/* Webhooks List */}
          <WebhookList />
        </div>

        {/* Documentation Link */}
        <div className="mx-auto max-w-3xl pb-6">
          <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
            <p className="font-medium mb-2">Need help?</p>
            <p className="text-sm text-[color:var(--color-text-secondary)] mb-3">
              Learn how to configure and secure webhooks in our documentation.
            </p>
            <a
              href="/api-docs"
              className="inline-flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
            >
              View Webhook Documentation
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default WebhooksPage;
