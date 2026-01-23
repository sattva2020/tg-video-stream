import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { apiKeysApi, type APIKey, type CreateAPIKeyData } from '../../api/apiKeys';
import {
  Plus,
  Key,
  Trash2,
  Shield,
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  Copy,
  Eye,
  EyeOff,
  AlertCircle
} from 'lucide-react';

interface ApiKeyListProps {
  className?: string;
}

const AVAILABLE_SCOPES = [
  { value: 'read:streams', label: 'Read Streams', description: 'View stream information' },
  { value: 'write:streams', label: 'Write Streams', description: 'Control streams (start/stop)' },
  { value: 'read:playlists', label: 'Read Playlists', description: 'View playlists' },
  { value: 'write:playlists', label: 'Write Playlists', description: 'Manage playlists' },
  { value: 'read:channels', label: 'Read Channels', description: 'View channel information' },
  { value: 'write:channels', label: 'Write Channels', description: 'Manage channels' },
  { value: 'read:webhooks', label: 'Read Webhooks', description: 'View webhook subscriptions' },
  { value: 'write:webhooks', label: 'Write Webhooks', description: 'Manage webhooks' },
  { value: 'read:analytics', label: 'Read Analytics', description: 'View analytics data' },
  { value: 'admin', label: 'Admin', description: 'Full administrative access' },
];

export const ApiKeyList: React.FC<ApiKeyListProps> = ({ className = '' }) => {
  const { t } = useTranslation();
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['read:streams']);
  const [rateLimitRequests, setRateLimitRequests] = useState('');
  const [rateLimitWindow, setRateLimitWindow] = useState('60');
  const [expiresAt, setExpiresAt] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const loadApiKeys = async () => {
    setLoading(true);
    setError(null);
    try {
      const keys = await apiKeysApi.list();
      setApiKeys(keys);
    } catch (err: any) {
      console.error('Failed to load API keys:', err);
      setError(err.response?.data?.detail || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApiKeys();
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) {
      setError('Key name is required');
      return;
    }
    if (selectedScopes.length === 0) {
      setError('At least one scope is required');
      return;
    }

    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const data: CreateAPIKeyData = {
        name: newKeyName.trim(),
        scopes: selectedScopes,
      };

      if (rateLimitRequests && rateLimitWindow) {
        data.rate_limit = {
          requests: parseInt(rateLimitRequests, 10),
          window: parseInt(rateLimitWindow, 10),
        };
      }

      if (expiresAt) {
        data.expires_at = expiresAt;
      }

      const result = await apiKeysApi.create(data);
      setCreatedKey(result.key || null);
      setSuccess('API key created successfully! Copy it now, you won\'t see it again.');
      setNewKeyName('');
      setSelectedScopes(['read:streams']);
      setRateLimitRequests('');
      setExpiresAt('');
      await loadApiKeys();
    } catch (err: any) {
      console.error('Failed to create API key:', err);
      setError(err.response?.data?.detail || 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeKey = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiKeysApi.revoke(keyId);
      setSuccess(`API key "${keyName}" has been revoked.`);
      await loadApiKeys();
    } catch (err: any) {
      console.error('Failed to revoke API key:', err);
      setError(err.response?.data?.detail || 'Failed to revoke API key');
    }
  };

  const handleDeleteKey = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to permanently delete the API key "${keyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiKeysApi.delete(keyId);
      setSuccess(`API key "${keyName}" has been deleted.`);
      await loadApiKeys();
    } catch (err: any) {
      console.error('Failed to delete API key:', err);
      setError(err.response?.data?.detail || 'Failed to delete API key');
    }
  };

  const handleCopyKey = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes(prev =>
      prev.includes(scope)
        ? prev.filter(s => s !== scope)
        : [...prev, scope]
    );
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleString();
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
          <span className="text-sm text-[color:var(--color-text-muted)]">
            {t('common.loading', 'Loading...')}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Messages */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 flex items-start gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-500">
          {success}
        </div>
      )}

      {/* Created Key Display */}
      {createdKey && (
        <div className="mb-6 p-4 rounded-lg bg-[color:var(--color-accent)]/10 border border-[color:var(--color-accent)]/30">
          <div className="flex items-start gap-3 mb-3">
            <Key className="w-5 h-5 text-[color:var(--color-accent)] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-[color:var(--color-accent)] mb-2">
                Your New API Key
              </p>
              <p className="text-sm text-[color:var(--color-text-secondary)] mb-3">
                Copy this key now. You won't be able to see it again!
              </p>
              <div className="flex items-center gap-2">
                <div className="flex-1 font-mono text-sm bg-[color:var(--color-surface)] rounded-lg p-3 border border-[color:var(--color-border)] break-all">
                  {showKey ? createdKey : 'sk_' + '•'.repeat(40)}
                </div>
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="p-2 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
                  title={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={handleCopyKey}
                  className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                >
                  {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              setCreatedKey(null);
              setShowCreateDialog(false);
            }}
            className="text-sm text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)] transition-colors"
          >
            I've saved my key
          </button>
        </div>
      )}

      {/* Header with Create Button */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">API Keys</h2>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            Manage your API keys for programmatic access
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(!showCreateDialog)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" />
          Create Key
        </button>
      </div>

      {/* Create Key Form */}
      {showCreateDialog && !createdKey && (
        <div className="mb-6 p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          <h3 className="text-lg font-semibold mb-4">Create New API Key</h3>
          <form onSubmit={handleCreateKey} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g., Production App Key"
                className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                disabled={creating}
              />
            </div>

            {/* Scopes */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Scopes <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {AVAILABLE_SCOPES.map((scope) => (
                  <label
                    key={scope.value}
                    className={`flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedScopes.includes(scope.value)
                        ? 'bg-[color:var(--color-accent)]/10 border-[color:var(--color-accent)]'
                        : 'bg-[color:var(--color-surface)] border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)]'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes(scope.value)}
                      onChange={() => toggleScope(scope.value)}
                      className="mt-1"
                      disabled={creating}
                    />
                    <div className="flex-1">
                      <span className="font-medium text-sm">{scope.label}</span>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">{scope.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Rate Limit */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Rate Limit (optional)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={rateLimitRequests}
                  onChange={(e) => setRateLimitRequests(e.target.value)}
                  placeholder="100"
                  className="w-32 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                  disabled={creating}
                />
                <span className="text-sm text-[color:var(--color-text-secondary)]">requests per</span>
                <input
                  type="number"
                  value={rateLimitWindow}
                  onChange={(e) => setRateLimitWindow(e.target.value)}
                  placeholder="60"
                  className="w-24 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                  disabled={creating}
                />
                <span className="text-sm text-[color:var(--color-text-secondary)]">seconds</span>
              </div>
              <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                Leave empty for default limits
              </p>
            </div>

            {/* Expiration */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Expires At (optional)
              </label>
              <input
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full sm:w-auto rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                disabled={creating}
              />
              <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                Leave empty for no expiration
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              <button
                type="submit"
                disabled={creating || !newKeyName.trim() || selectedScopes.length === 0}
                className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {creating ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    Create Key
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateDialog(false)}
                disabled={creating}
                className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* API Keys List */}
      {apiKeys.length === 0 ? (
        <div className="p-8 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center">
          <Key className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
          <p className="text-[color:var(--color-text-muted)] mb-1">No API keys yet</p>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Create your first API key to get started with the API
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {apiKeys.map((key) => (
            <div
              key={key.id}
              className={`p-4 rounded-lg border ${
                isExpired(key.expires_at)
                  ? 'bg-red-500/5 border-red-500/20'
                  : key.is_active
                  ? 'bg-[color:var(--color-panel)] border-[color:var(--color-border)]'
                  : 'bg-gray-500/5 border-gray-500/20'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Key className={`w-5 h-5 flex-shrink-0 ${
                      key.is_active && !isExpired(key.expires_at)
                        ? 'text-green-500'
                        : 'text-gray-400'
                    }`} />
                    <h3 className="font-semibold truncate">{key.name}</h3>
                    {key.is_active && !isExpired(key.expires_at) ? (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/20 text-green-500 text-xs font-medium">
                        <CheckCircle className="w-3 h-3" />
                        Active
                      </span>
                    ) : isExpired(key.expires_at) ? (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-500 text-xs font-medium">
                        <XCircle className="w-3 h-3" />
                        Expired
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400 text-xs font-medium">
                        <XCircle className="w-3 h-3" />
                        Revoked
                      </span>
                    )}
                  </div>

                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                      <Shield className="w-4 h-4" />
                      <span className="font-mono text-xs">{key.scopes.join(', ')}</span>
                    </div>
                    {key.rate_limit && (
                      <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                        <Clock className="w-4 h-4" />
                        <span>
                          {key.rate_limit.requests} requests / {key.rate_limit.window} seconds
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                      <Calendar className="w-4 h-4" />
                      <span>Created: {formatDate(key.created_at)}</span>
                    </div>
                    {key.expires_at && (
                      <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                        <Calendar className="w-4 h-4" />
                        <span className={isExpired(key.expires_at) ? 'text-red-500' : ''}>
                          Expires: {formatDate(key.expires_at)}
                        </span>
                      </div>
                    )}
                    {key.last_used && (
                      <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                        <Clock className="w-4 h-4" />
                        <span>Last used: {formatDate(key.last_used)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {key.is_active && !isExpired(key.expires_at) && (
                    <button
                      onClick={() => handleRevokeKey(key.id, key.name)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
                      title="Revoke key"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteKey(key.id, key.name)}
                    className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
                    title="Delete key"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
