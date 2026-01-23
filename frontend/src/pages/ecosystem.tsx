import React from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import {
  Globe,
  Package,
  Code,
  Zap,
  Download,
  ExternalLink,
  Github,
  BookOpen,
  Users,
  Puzzle,
} from 'lucide-react';

interface SDK {
  name: string;
  language: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  installCommand: string;
  docsUrl: string;
  repoUrl: string;
}

interface Integration {
  name: string;
  description: string;
  category: string;
  icon: React.ReactNode;
  url: string;
  official: boolean;
}

const EcosystemPage: React.FC = () => {
  const { t } = useTranslation();

  const sdks: SDK[] = [
    {
      name: 'Python SDK',
      language: 'Python',
      description: 'Official Python SDK with async support, type hints, and comprehensive error handling. Ideal for backend services and data pipelines.',
      icon: <Code className="w-6 h-6" />,
      color: 'bg-blue-500/10 text-blue-500',
      installCommand: 'pip install sattva-api',
      docsUrl: '/api-docs#sdk-python',
      repoUrl: 'https://github.com/sattva/sattva-python-sdk',
    },
    {
      name: 'JavaScript/TypeScript SDK',
      language: 'JavaScript/TypeScript',
      description: 'Official JavaScript/TypeScript SDK for Node.js and browser. Full TypeScript support with modern async/await patterns.',
      icon: <Code className="w-6 h-6" />,
      color: 'bg-yellow-500/10 text-yellow-500',
      installCommand: 'npm install @sattva/sdk',
      docsUrl: '/api-docs#sdk-javascript',
      repoUrl: 'https://github.com/sattva/sattva-js-sdk',
    },
    {
      name: 'Go SDK',
      language: 'Go',
      description: 'Official Go SDK with context support, efficient concurrency, and idiomatic Go patterns. Perfect for high-performance microservices.',
      icon: <Code className="w-6 h-6" />,
      color: 'bg-cyan-500/10 text-cyan-500',
      installCommand: 'go get github.com/sattva/sattva-go-sdk',
      docsUrl: '/api-docs#sdk-go',
      repoUrl: 'https://github.com/sattva/sattva-go-sdk',
    },
  ];

  const integrations: Integration[] = [
    {
      name: 'Python SDK',
      description: 'Full-featured Python client with async support and type hints',
      category: 'SDK',
      icon: <Code className="w-5 h-5" />,
      url: 'https://github.com/sattva/sattva-python-sdk',
      official: true,
    },
    {
      name: 'JavaScript SDK',
      description: 'Modern JavaScript/TypeScript SDK for Node.js and browser',
      category: 'SDK',
      icon: <Code className="w-5 h-5" />,
      url: 'https://github.com/sattva/sattva-js-sdk',
      official: true,
    },
    {
      name: 'Go SDK',
      description: 'Idiomatic Go SDK with context support and concurrency',
      category: 'SDK',
      icon: <Code className="w-5 h-5" />,
      url: 'https://github.com/sattva/sattva-go-sdk',
      official: true,
    },
    {
      name: 'Webhook Signature Verification',
      description: 'Standalone webhook signature verification libraries',
      category: 'Utilities',
      icon: <Zap className="w-5 h-5" />,
      url: '/api-docs#webhooks',
      official: true,
    },
    {
      name: 'API Examples Repository',
      description: 'Collection of code examples and integration samples',
      category: 'Examples',
      icon: <BookOpen className="w-5 h-5" />,
      url: 'https://github.com/sattva/sattva-examples',
      official: true,
    },
    {
      name: 'Community Integrations',
      description: 'Third-party integrations and community tools',
      category: 'Community',
      icon: <Users className="w-5 h-5" />,
      url: 'https://github.com/sattva/sattva-ecosystem',
      official: false,
    },
  ];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-panel)]/30 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <div className="mx-auto max-w-3xl py-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
                <Globe className="w-6 h-6 text-[color:var(--color-accent)]" />
              </div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
                Ecosystem
              </h1>
            </div>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Explore official SDKs, community integrations, and tools to extend the platform
            </p>
          </div>
        </div>

        {/* Info Banner */}
        <div className="mx-auto max-w-3xl py-6">
          <div className="mb-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <Puzzle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-500 mb-1">Extensible Platform</p>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Build powerful integrations with our official SDKs for Python, JavaScript, and Go. Connect your systems using webhooks, automate workflows with the REST API, and join our community of developers building amazing tools.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Official SDKs Section */}
        <div className="mx-auto max-w-3xl pb-6">
          <h2 className="text-xl font-semibold text-[color:var(--color-text)] mb-4">
            Official SDKs
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {sdks.map((sdk) => (
              <div
                key={sdk.name}
                className="p-6 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${sdk.color} flex-shrink-0`}>
                    {sdk.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                        {sdk.name}
                      </h3>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-500">
                        Official
                      </span>
                    </div>
                    <p className="text-sm text-[color:var(--color-text-secondary)] mb-3">
                      {sdk.description}
                    </p>
                    <div className="flex items-center gap-4">
                      <code className="text-xs bg-[color:var(--color-surface)] px-3 py-1.5 rounded border border-[color:var(--color-border)] font-mono">
                        {sdk.installCommand}
                      </code>
                      <a
                        href={sdk.docsUrl}
                        className="inline-flex items-center gap-1 text-sm text-[color:var(--color-accent)] hover:underline"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        Docs
                      </a>
                      <a
                        href={sdk.repoUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-accent)]"
                      >
                        <Github className="w-3.5 h-3.5" />
                        GitHub
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Integrations Directory */}
        <div className="mx-auto max-w-3xl pb-6">
          <h2 className="text-xl font-semibold text-[color:var(--color-text)] mb-4">
            Integrations Directory
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {integrations.map((integration) => (
              <a
                key={integration.name}
                href={integration.url}
                target={integration.url.startsWith('http') ? '_blank' : undefined}
                rel={integration.url.startsWith('http') ? 'noopener noreferrer' : undefined}
                className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-[color:var(--color-surface)] text-[color:var(--color-text-secondary)] group-hover:text-[color:var(--color-accent)] transition-colors flex-shrink-0">
                    {integration.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-[color:var(--color-text)]">
                        {integration.name}
                      </h3>
                      {integration.official && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-500">
                          Official
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[color:var(--color-text-secondary)] mb-2">
                      {integration.description}
                    </p>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[color:var(--color-surface)] border border-[color:var(--color-border)]">
                      {integration.category}
                    </span>
                  </div>
                  {integration.url.startsWith('http') && (
                    <ExternalLink className="w-4 h-4 text-[color:var(--color-text-secondary)] flex-shrink-0 mt-1" />
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Build Your Own Integration */}
        <div className="mx-auto max-w-3xl pb-6">
          <div className="p-6 rounded-lg bg-gradient-to-br from-[color:var(--color-accent)]/10 to-transparent border border-[color:var(--color-accent)]/20">
            <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-3 flex items-center gap-2">
              <Download className="w-5 h-5" />
              Build Your Own Integration
            </h3>
            <p className="text-sm text-[color:var(--color-text-secondary)] mb-4">
              Get started with our comprehensive API documentation, code examples, and webhook guides. Create powerful integrations that fit your specific needs.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="/api-docs"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white hover:opacity-90 transition-opacity"
              >
                <BookOpen className="w-4 h-4" />
                View API Documentation
              </a>
              <a
                href="/api-keys"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:border-[color:var(--color-accent)] transition-colors"
              >
                <Package className="w-4 h-4" />
                Get API Keys
              </a>
              <a
                href="/webhooks"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:border-[color:var(--color-accent)] transition-colors"
              >
                <Zap className="w-4 h-4" />
                Configure Webhooks
              </a>
            </div>
          </div>
        </div>

        {/* Community Section */}
        <div className="mx-auto max-w-3xl pb-6">
          <div className="p-6 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
            <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-3 flex items-center gap-2">
              <Users className="w-5 h-5" />
              Join the Community
            </h3>
            <p className="text-sm text-[color:var(--color-text-secondary)] mb-4">
              Share your integrations, get help from other developers, and contribute to the ecosystem. Join our GitHub discussions or star our repositories to show your support.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://github.com/sattva"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
              >
                <Github className="w-4 h-4" />
                GitHub Organization
                <ExternalLink className="w-3 h-3" />
              </a>
              <a
                href="https://github.com/sattva/sattva-ecosystem"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
              >
                <Puzzle className="w-4 h-4" />
                Community Integrations
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default EcosystemPage;
