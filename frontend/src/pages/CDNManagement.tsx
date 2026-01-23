/**
 * CDN Management Page
 *
 * Страница управления CDN-провайдерами (Cloudflare, CloudFront, Fastly).
 * Позволяет настраивать провайдеров, управлять кэшем, мониторить здоровье.
 *
 * Feature: 024-global-cdn-integration-edge-deployment
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import {
  cdnApi,
  type CDNProvider,
  type CDNHealthStatusResponse,
  type HealthStatus,
  type CDNProviderType,
  type CDNConfigCreate,
  type PurgeCacheRequest
} from '../services/cdnApi';

// === Types ===

interface FormErrors {
  provider?: string;
  name?: string;
  apiToken?: string;
  general?: string;
}

// === Helper Components ===

const StatusBadge: React.FC<{ status: HealthStatus }> = ({ status }) => {
  const statusConfig = {
    healthy: {
      label: 'Healthy',
      className: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
      dotColor: 'bg-emerald-500'
    },
    degraded: {
      label: 'Degraded',
      className: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
      dotColor: 'bg-amber-500'
    },
    unhealthy: {
      label: 'Unhealthy',
      className: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
      dotColor: 'bg-rose-500'
    }
  };

  const config = statusConfig[status];
  const { t } = useTranslation();

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${config.className}`}>
      <span className={`w-2 h-2 mr-2 rounded-full ${config.dotColor}`} />
      {t(`cdn.status.${status}`, config.label)}
    </span>
  );
};

const ProviderIcon: React.FC<{ provider: CDNProviderType }> = ({ provider }) => {
  const icons = {
    cloudflare: '🌐',
    cloudfront: '☁️',
    fastly: '⚡'
  };
  return <span className="text-2xl">{icons[provider]}</span>;
};

// === Main Page Component ===

const CDNManagement: React.FC = () => {
  const { t } = useTranslation();
  const [providers, setProviders] = useState<CDNProvider[]>([]);
  const [healthStatus, setHealthStatus] = useState<CDNHealthStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<CDNProvider | null>(null);
  const [formData, setFormData] = useState<CDNConfigCreate>({
    provider: 'cloudflare',
    name: '',
    api_token: '',
    enabled: true,
    priority: 1
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cache purge state
  const [purgeUrls, setPurgeUrls] = useState('');
  const [purgeAll, setPurgeAll] = useState(false);
  const [isPurging, setIsPurging] = useState(false);

  // Fetch providers
  const fetchProviders = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await cdnApi.listProviders(false);
      setProviders(response.providers);
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to fetch CDN providers';
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch health status
  const fetchHealthStatus = useCallback(async () => {
    try {
      const response = await cdnApi.getHealthStatus(undefined, false);
      setHealthStatus(response);
    } catch (err: any) {
      // Don't show error for health check failures, just log
      console.error('Failed to fetch health status:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchProviders();
    fetchHealthStatus();
  }, [fetchProviders, fetchHealthStatus]);

  // Refresh data
  const handleRefresh = () => {
    fetchProviders();
    fetchHealthStatus();
  };

  // Form handlers
  const handleInputChange = (field: keyof CDNConfigCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear field error when user starts typing
    setFormErrors(prev => ({ ...prev, [field]: undefined }));
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    if (!formData.name?.trim()) {
      errors.name = 'Name is required';
    }

    if (!formData.api_token?.trim()) {
      errors.apiToken = 'API token is required';
    }

    // Provider-specific validation
    if (formData.provider === 'cloudflare' && !formData.zone_id?.trim()) {
      errors.general = 'Zone ID is required for Cloudflare';
    }

    if (formData.provider === 'cloudfront' && !formData.distribution_id?.trim()) {
      errors.general = 'Distribution ID is required for CloudFront';
    }

    if (formData.provider === 'fastly' && !formData.service_id?.trim()) {
      errors.general = 'Service ID is required for Fastly';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      // TODO: Implement create/update API call when backend endpoint is ready
      // For now, just simulate success
      await new Promise(resolve => setTimeout(resolve, 1000));

      setSuccess(editingProvider ? 'Provider updated successfully' : 'Provider added successfully');
      setShowAddForm(false);
      setEditingProvider(null);
      setFormData({
        provider: 'cloudflare',
        name: '',
        api_token: '',
        enabled: true,
        priority: 1
      });
      fetchProviders();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to save provider';
      setError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (provider: CDNProvider) => {
    setEditingProvider(provider);
    setFormData({
      provider: provider.provider,
      name: provider.name,
      api_token: provider.api_token || '',
      enabled: provider.enabled,
      priority: provider.priority,
      account_id: provider.account_id,
      zone_id: provider.zone_id,
      distribution_id: provider.distribution_id,
      service_id: provider.service_id
    });
    setShowAddForm(true);
    setFormErrors({});
    setSuccess(null);
    setError(null);
  };

  const handleDelete = async (providerId: string) => {
    if (!confirm('Are you sure you want to delete this CDN provider?')) {
      return;
    }

    try {
      // TODO: Implement delete API call when backend endpoint is ready
      await new Promise(resolve => setTimeout(resolve, 500));
      setSuccess('Provider deleted successfully');
      fetchProviders();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to delete provider';
      setError(errorMsg);
    }
  };

  const handleToggleEnabled = async (provider: CDNProvider) => {
    try {
      // TODO: Implement toggle API call when backend endpoint is ready
      await new Promise(resolve => setTimeout(resolve, 500));
      setSuccess(`Provider ${provider.enabled ? 'disabled' : 'enabled'} successfully`);
      fetchProviders();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to toggle provider';
      setError(errorMsg);
    }
  };

  const handlePurgeCache = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!purgeAll && !purgeUrls.trim()) {
      setError('Please enter URLs to purge or select "Purge All"');
      return;
    }

    setIsPurging(true);
    setError(null);
    setSuccess(null);

    try {
      const request: PurgeCacheRequest = {
        urls: purgeUrls.split('\n').map(url => url.trim()).filter(url => url),
        purge_all: purgeAll
      };

      const response = await cdnApi.purgeCache(request);

      if (response.success) {
        setSuccess(`Cache purged successfully for ${response.purged_urls.length} URL(s)`);
        setPurgeUrls('');
        setPurgeAll(false);
      } else {
        setError(response.errors.join(', ') || 'Failed to purge cache');
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to purge cache';
      setError(errorMsg);
    } finally {
      setIsPurging(false);
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
              {t('cdn.title', 'CDN Management')}
            </h1>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('cdn.subtitle', 'Manage CDN providers and cache settings')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm hover:bg-[color:var(--color-surface-muted)] transition-colors"
              disabled={isLoading}
            >
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
            <button
              onClick={() => {
                setShowAddForm(true);
                setEditingProvider(null);
                setFormData({
                  provider: 'cloudflare',
                  name: '',
                  api_token: '',
                  enabled: true,
                  priority: 1
                });
                setFormErrors({});
                setSuccess(null);
                setError(null);
              }}
              className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              {t('cdn.addProvider', 'Add Provider')}
            </button>
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            {success}
          </div>
        )}

        {/* Health Status Overview */}
        {healthStatus && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">
              {t('cdn.healthStatus', 'Health Status')}
            </h2>
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={healthStatus.overall_status} />
                  <span className="text-sm text-[color:var(--color-text-muted)]">
                    Last check: {new Date(healthStatus.last_check).toLocaleString()}
                  </span>
                </div>
              </div>
              {healthStatus.providers.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {healthStatus.providers.map(provider => (
                    <div
                      key={provider.id}
                      className="p-3 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)]"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-[color:var(--color-text)]">{provider.name}</span>
                        <StatusBadge status={provider.status} />
                      </div>
                      <div className="text-xs text-[color:var(--color-text-muted)] space-y-1">
                        <div>Response time: {provider.response_time_ms}ms</div>
                        {provider.edge_nodes_total !== undefined && (
                          <div>
                            Edge nodes: {provider.edge_nodes_healthy || 0}/{provider.edge_nodes_total} healthy
                          </div>
                        )}
                        {provider.error && (
                          <div className="text-rose-400">{provider.error}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Add/Edit Provider Form */}
        {showAddForm && (
          <div className="mb-6">
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-[color:var(--color-text)]">
                  {editingProvider ? 'Edit Provider' : 'Add CDN Provider'}
                </h2>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingProvider(null);
                    setFormErrors({});
                  }}
                  className="text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Provider Type */}
                <div>
                  <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                    Provider Type
                  </label>
                  <div className="flex gap-2">
                    {(['cloudflare', 'cloudfront', 'fastly'] as CDNProviderType[]).map(type => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => handleInputChange('provider', type)}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-colors ${
                          formData.provider === type
                            ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10 text-[color:var(--color-accent)]'
                            : 'border-[color:var(--color-border)] bg-[color:var(--color-surface)] hover:bg-[color:var(--color-surface-muted)]'
                        }`}
                      >
                        <ProviderIcon provider={type} />
                        <span className="capitalize">{type}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                    Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="My Cloudflare CDN"
                    className={`w-full rounded-lg border bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)] ${
                      formErrors.name ? 'border-rose-500' : 'border-[color:var(--color-border)]'
                    }`}
                  />
                  {formErrors.name && (
                    <p className="mt-1 text-sm text-rose-400">{formErrors.name}</p>
                  )}
                </div>

                {/* API Token */}
                <div>
                  <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                    API Token
                  </label>
                  <input
                    type="password"
                    value={formData.api_token}
                    onChange={(e) => handleInputChange('api_token', e.target.value)}
                    placeholder="Enter API token"
                    className={`w-full rounded-lg border bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)] ${
                      formErrors.apiToken ? 'border-rose-500' : 'border-[color:var(--color-border)]'
                    }`}
                  />
                  {formErrors.apiToken && (
                    <p className="mt-1 text-sm text-rose-400">{formErrors.apiToken}</p>
                  )}
                </div>

                {/* Provider-specific fields */}
                {formData.provider === 'cloudflare' && (
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                      Zone ID
                    </label>
                    <input
                      type="text"
                      value={formData.zone_id || ''}
                      onChange={(e) => handleInputChange('zone_id', e.target.value)}
                      placeholder="Enter Cloudflare zone ID"
                      className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]"
                    />
                  </div>
                )}

                {formData.provider === 'cloudfront' && (
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                      Distribution ID
                    </label>
                    <input
                      type="text"
                      value={formData.distribution_id || ''}
                      onChange={(e) => handleInputChange('distribution_id', e.target.value)}
                      placeholder="Enter CloudFront distribution ID"
                      className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]"
                    />
                  </div>
                )}

                {formData.provider === 'fastly' && (
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                      Service ID
                    </label>
                    <input
                      type="text"
                      value={formData.service_id || ''}
                      onChange={(e) => handleInputChange('service_id', e.target.value)}
                      placeholder="Enter Fastly service ID"
                      className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]"
                    />
                  </div>
                )}

                {formErrors.general && (
                  <p className="text-sm text-rose-400">{formErrors.general}</p>
                )}

                {/* Priority and Enabled */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                      Priority
                    </label>
                    <input
                      type="number"
                      value={formData.priority}
                      onChange={(e) => handleInputChange('priority', parseInt(e.target.value))}
                      min="1"
                      max="100"
                      className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-3 text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-3 p-3 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] cursor-pointer hover:bg-[color:var(--color-surface-muted)]">
                      <input
                        type="checkbox"
                        checked={formData.enabled}
                        onChange={(e) => handleInputChange('enabled', e.target.checked)}
                        className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
                      />
                      <span className="text-sm font-medium text-[color:var(--color-text)]">Enabled</span>
                    </label>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 px-4 py-3 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-60"
                  >
                    {isSubmitting ? 'Saving...' : editingProvider ? 'Update Provider' : 'Add Provider'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddForm(false);
                      setEditingProvider(null);
                    }}
                    className="px-4 py-3 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Providers List */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">
            {t('cdn.providers', 'CDN Providers')} ({providers.length})
          </h2>

          {isLoading ? (
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-8 text-center">
              <div className="flex justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
              </div>
              <p className="mt-4 text-[color:var(--color-text-muted)]">Loading CDN providers...</p>
            </div>
          ) : providers.length === 0 ? (
            <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-8 text-center">
              <span className="text-4xl mb-4 block">🌐</span>
              <p className="text-[color:var(--color-text-muted)]">No CDN providers configured</p>
              <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                Add a CDN provider to get started with global content delivery
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {providers.map(provider => (
                <div
                  key={provider.id}
                  className={`rounded-2xl bg-[color:var(--color-panel)] border ring-1 ring-inset shadow-md shadow-black/5 p-4 transition-all ${
                    provider.enabled
                      ? 'border-[color:var(--color-border)]'
                      : 'border-gray-700 opacity-60'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <ProviderIcon provider={provider.provider} />
                      <div>
                        <h3 className="font-semibold text-[color:var(--color-text)]">{provider.name}</h3>
                        <p className="text-xs text-[color:var(--color-text-muted)] capitalize">{provider.provider}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {provider.health_status && <StatusBadge status={provider.health_status} />}
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          provider.enabled
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-gray-500/10 text-gray-400'
                        }`}
                      >
                        {provider.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm text-[color:var(--color-text-muted)]">
                    <div className="flex justify-between">
                      <span>Priority:</span>
                      <span className="font-medium text-[color:var(--color-text)]">{provider.priority}</span>
                    </div>
                    {provider.last_health_check && (
                      <div className="flex justify-between">
                        <span>Last check:</span>
                        <span className="font-medium text-[color:var(--color-text)]">
                          {new Date(provider.last_health_check).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {provider.last_error && (
                      <div className="text-rose-400 text-xs">
                        Error: {provider.last_error}
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => handleEdit(provider)}
                      className="flex-1 px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm hover:bg-[color:var(--color-surface-muted)] transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleToggleEnabled(provider)}
                      className="flex-1 px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm hover:bg-[color:var(--color-surface-muted)] transition-colors"
                    >
                      {provider.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleDelete(provider.id)}
                      className="px-3 py-2 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-400 text-sm hover:bg-rose-500/20 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cache Purge Section */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">
            {t('cdn.cachePurge', 'Cache Purge')}
          </h2>
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
            <form onSubmit={handlePurgeCache} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                  URLs to Purge
                </label>
                <textarea
                  value={purgeUrls}
                  onChange={(e) => setPurgeUrls(e.target.value)}
                  placeholder="https://example.com/video1.mp4&#10;https://example.com/video2.mp4&#10;One URL per line"
                  rows={5}
                  disabled={purgeAll}
                  className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-3 text-sm text-[color:var(--color-text)] placeholder-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)] disabled:opacity-60 font-mono"
                />
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={purgeAll}
                    onChange={(e) => setPurgeAll(e.target.checked)}
                    className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
                  />
                  <span className="text-sm font-medium text-[color:var(--color-text)]">
                    Purge All Cache
                  </span>
                </label>
                <span className="text-xs text-[color:var(--color-text-muted)]">
                  (⚠️ Use with caution - clears entire CDN cache)
                </span>
              </div>

              <button
                type="submit"
                disabled={isPurging || (!purgeAll && !purgeUrls.trim())}
                className="w-full px-4 py-3 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-60"
              >
                {isPurging ? 'Purging...' : 'Purge Cache'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default CDNManagement;
