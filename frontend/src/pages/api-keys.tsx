import React from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import { ApiKeyList } from '../components/api-keys/ApiKeyList';
import { Key, Lock } from 'lucide-react';

const ApiKeysPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <div className="mx-auto max-w-3xl py-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
                <Key className="w-6 h-6 text-[color:var(--color-accent)]" />
              </div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
                API Keys
              </h1>
            </div>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Manage your API keys for programmatic access to the platform
            </p>
          </div>
        </div>

        {/* Info Banner */}
        <div className="mx-auto max-w-3xl py-6">
          <div className="mb-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <Lock className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-500 mb-1">Security Notice</p>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  API keys are sensitive credentials. Treat them like passwords. Never share them in public repositories or expose them in client-side code.
                </p>
              </div>
            </div>
          </div>

          {/* API Keys List */}
          <ApiKeyList />
        </div>

        {/* Documentation Link */}
        <div className="mx-auto max-w-3xl pb-6">
          <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
            <p className="font-medium mb-2">Need help?</p>
            <p className="text-sm text-[color:var(--color-text-secondary)] mb-3">
              Learn how to use API keys in our documentation.
            </p>
            <a
              href="/api-docs"
              className="inline-flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
            >
              View API Documentation
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

export default ApiKeysPage;
