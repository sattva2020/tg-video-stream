import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import { BookOpen, ExternalLink, Code2, Loader2 } from 'lucide-react';
import { config } from '../config';

const ApiDocsPage: React.FC = () => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const swaggerUrl = `${config.apiBaseUrl}/docs`;

  const handleIframeLoad = () => {
    setIsLoading(false);
    setLoadError(false);
  };

  const handleIframeError = () => {
    setIsLoading(false);
    setLoadError(true);
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <div className="mx-auto max-w-3xl py-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
                <BookOpen className="w-6 h-6 text-[color:var(--color-accent)]" />
              </div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
                API Documentation
              </h1>
            </div>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Interactive API explorer with detailed documentation and code examples
            </p>
          </div>
        </div>

        {/* Info Banner */}
        <div className="mx-auto max-w-3xl py-6">
          <div className="mb-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <Code2 className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-500 mb-1">Interactive API Explorer</p>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Explore all available API endpoints, test requests directly from your browser, and view code examples in multiple languages. Authentication is handled automatically using your session.
                </p>
              </div>
            </div>
          </div>

          {/* External Link */}
          <div className="mb-6">
            <a
              href={swaggerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white hover:opacity-90 transition-opacity"
            >
              <span>Open in New Tab</span>
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>

          {/* Swagger UI iframe */}
          <div className="relative w-full bg-[color:var(--color-surface)] rounded-lg border border-[color:var(--color-border)] overflow-hidden" style={{ minHeight: '800px' }}>
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-[color:var(--color-surface)] z-10">
                <Loader2 className="w-8 h-8 text-[color:var(--color-accent)] animate-spin mb-4" />
                <p className="text-sm text-[color:var(--color-text-muted)]">Loading API documentation...</p>
              </div>
            )}

            {loadError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-[color:var(--color-surface)] z-10 p-6">
                <div className="text-center max-w-md">
                  <p className="text-lg font-medium text-red-500 mb-2">Failed to load API documentation</p>
                  <p className="text-sm text-[color:var(--color-text-muted)] mb-4">
                    The API documentation service may be unavailable. Please try again later or open the documentation in a new tab.
                  </p>
                  <a
                    href={swaggerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-[color:var(--color-accent)] hover:underline"
                  >
                    <span>Open API Docs in New Tab</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            )}

            <iframe
              src={swaggerUrl}
              className="w-full border-0"
              style={{ minHeight: '800px', height: 'calc(100vh - 300px)' }}
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              title="API Documentation"
            />
          </div>
        </div>

        {/* Quick Links */}
        <div className="mx-auto max-w-3xl pb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <a
              href="/api-keys"
              className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors"
            >
              <h3 className="font-medium mb-2">API Keys</h3>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                Manage your API keys for programmatic access
              </p>
            </a>

            <a
              href="/webhooks"
              className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors"
            >
              <h3 className="font-medium mb-2">Webhooks</h3>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                Configure webhook subscriptions for event notifications
              </p>
            </a>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default ApiDocsPage;
