import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { webhooksApi, type Webhook, type CreateWebhookData, type WebhookEvent } from '../../api/webhooks';
import {
  Plus,
  Webhook,
  Trash2,
  Play,
  RefreshCw,
  Eye,
  EyeOff,
  Copy,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Calendar,
  FileText,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface WebhookListProps {
  className?: string;
}

const AVAILABLE_EVENT_TYPES = [
  { value: 'stream.started', label: 'Stream Started', description: 'When a stream starts', category: 'Stream' },
  { value: 'stream.stopped', label: 'Stream Stopped', description: 'When a stream stops', category: 'Stream' },
  { value: 'stream.paused', label: 'Stream Paused', description: 'When a stream is paused', category: 'Stream' },
  { value: 'stream.resumed', label: 'Stream Resumed', description: 'When a stream resumes', category: 'Stream' },
  { value: 'stream.error', label: 'Stream Error', description: 'When a stream encounters an error', category: 'Stream' },
  { value: 'viewer.milestone', label: 'Viewer Milestone', description: 'When viewer count reaches a milestone', category: 'Viewer' },
  { value: 'viewer.joined', label: 'Viewer Joined', description: 'When a viewer joins', category: 'Viewer' },
  { value: 'viewer.left', label: 'Viewer Left', description: 'When a viewer leaves', category: 'Viewer' },
  { value: 'track.started', label: 'Track Started', description: 'When a track starts playing', category: 'Track' },
  { value: 'track.completed', label: 'Track Completed', description: 'When a track finishes', category: 'Track' },
  { value: 'track.failed', label: 'Track Failed', description: 'When a track fails to play', category: 'Track' },
  { value: 'track.skipped', label: 'Track Skipped', description: 'When a track is skipped', category: 'Track' },
];

const EVENT_CATEGORIES = Array.from(new Set(AVAILABLE_EVENT_TYPES.map(e => e.category)));

export const WebhookList: React.FC<WebhookListProps> = ({ className = '' }) => {
  const { t } = useTranslation();
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>(['stream.started']);
  const [creating, setCreating] = useState(false);
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [createdWebhookId, setCreatedWebhookId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [expandedWebhookId, setExpandedWebhookId] = useState<string | null>(null);
  const [webhookEvents, setWebhookEvents] = useState<Record<string, WebhookEvent[]>>({});
  const [loadingEvents, setLoadingEvents] = useState<Record<string, boolean>>({});

  const loadWebhooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const hooks = await webhooksApi.list();
      setWebhooks(hooks);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load webhooks';
      console.error('Failed to load webhooks:', err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const loadWebhookEvents = async (webhookId: string) => {
    setLoadingEvents(prev => ({ ...prev, [webhookId]: true }));
    try {
      const response = await webhooksApi.listEvents(webhookId, 1, 10);
      setWebhookEvents(prev => ({ ...prev, [webhookId]: response.items }));
    } catch (err: unknown) {
      console.error('Failed to load webhook events:', err);
    } finally {
      setLoadingEvents(prev => ({ ...prev, [webhookId]: false }));
    }
  };

  useEffect(() => {
    loadWebhooks();
  }, []);

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webhookUrl.trim()) {
      setError('Webhook URL is required');
      return;
    }
    if (selectedEvents.length === 0) {
      setError('At least one event type is required');
      return;
    }

    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const data: CreateWebhookData = {
        url: webhookUrl.trim(),
        event_types: selectedEvents,
      };

      const result = await webhooksApi.create(data);
      setCreatedSecret(result.secret || null);
      setCreatedWebhookId(result.id);
      setSuccess('Webhook created successfully! Save the secret now, you won\'t see it again.');
      setWebhookUrl('');
      setSelectedEvents(['stream.started']);
      await loadWebhooks();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create webhook';
      console.error('Failed to create webhook:', err);
      setError(message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteWebhook = async (webhookId: string, webhookName: string) => {
    if (!confirm(`Are you sure you want to delete the webhook "${webhookName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await webhooksApi.delete(webhookId);
      setSuccess(`Webhook "${webhookName}" has been deleted.`);
      await loadWebhooks();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete webhook';
      console.error('Failed to delete webhook:', err);
      setError(message);
    }
  };

  const handleToggleActive = async (webhook: Webhook) => {
    try {
      await webhooksApi.update(webhook.id, { is_active: !webhook.is_active });
      setSuccess(`Webhook has been ${webhook.is_active ? 'disabled' : 'enabled'}.`);
      await loadWebhooks();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update webhook';
      console.error('Failed to update webhook:', err);
      setError(message);
    }
  };

  const handleTestWebhook = async (webhookId: string) => {
    try {
      await webhooksApi.test(webhookId);
      setSuccess('Test webhook sent successfully! Check your endpoint.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to send test webhook';
      console.error('Failed to test webhook:', err);
      setError(message);
    }
  };

  const handleRotateSecret = async (webhookId: string) => {
    if (!confirm('Are you sure you want to rotate the webhook secret? The old secret will stop working immediately.')) {
      return;
    }

    try {
      const result = await webhooksApi.rotateSecret(webhookId);
      setCreatedSecret(result.secret);
      setCreatedWebhookId(webhookId);
      setSuccess('Webhook secret rotated successfully! Save the new secret now.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to rotate secret';
      console.error('Failed to rotate secret:', err);
      setError(message);
    }
  };

  const handleCopySecret = () => {
    if (createdSecret) {
      navigator.clipboard.writeText(createdSecret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const toggleEvent = (eventType: string) => {
    setSelectedEvents(prev =>
      prev.includes(eventType)
        ? prev.filter(e => e !== eventType)
        : [...prev, eventType]
    );
  };

  const toggleExpand = async (webhookId: string) => {
    if (expandedWebhookId === webhookId) {
      setExpandedWebhookId(null);
    } else {
      setExpandedWebhookId(webhookId);
      if (!webhookEvents[webhookId]) {
        await loadWebhookEvents(webhookId);
      }
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleString();
  };

  const getStatusBadge = (webhook: Webhook) => {
    if (!webhook.is_active) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400 text-xs font-medium">
          <XCircle className="w-3 h-3" />
          Disabled
        </span>
      );
    }
    if (webhook.failure_count > 5) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-500 text-xs font-medium">
          <AlertCircle className="w-3 h-3" />
          Unhealthy
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/20 text-green-500 text-xs font-medium">
        <CheckCircle className="w-3 h-3" />
        Active
      </span>
    );
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

      {/* Created Secret Display */}
      {createdSecret && createdWebhookId && (
        <div className="mb-6 p-4 rounded-lg bg-[color:var(--color-accent)]/10 border border-[color:var(--color-accent)]/30">
          <div className="flex items-start gap-3 mb-3">
            <Webhook className="w-5 h-5 text-[color:var(--color-accent)] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-[color:var(--color-accent)] mb-2">
                Your Webhook Secret
              </p>
              <p className="text-sm text-[color:var(--color-text-secondary)] mb-3">
                Copy this secret now. You won't be able to see it again! Use it to verify webhook signatures.
              </p>
              <div className="flex items-center gap-2">
                <div className="flex-1 font-mono text-sm bg-[color:var(--color-surface)] rounded-lg p-3 border border-[color:var(--color-border)] break-all">
                  {showSecret ? createdSecret : 'whsec_' + '•'.repeat(32)}
                </div>
                <button
                  onClick={() => setShowSecret(!showSecret)}
                  className="p-2 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)] transition-colors"
                  title={showSecret ? 'Hide secret' : 'Show secret'}
                >
                  {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={handleCopySecret}
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
              setCreatedSecret(null);
              setCreatedWebhookId(null);
              setShowCreateDialog(false);
            }}
            className="text-sm text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)] transition-colors"
          >
            I've saved my secret
          </button>
        </div>
      )}

      {/* Header with Create Button */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">Webhooks</h2>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            Manage webhook subscriptions for real-time event notifications
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(!showCreateDialog)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" />
          Create Webhook
        </button>
      </div>

      {/* Create Webhook Form */}
      {showCreateDialog && !createdSecret && (
        <div className="mb-6 p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          <h3 className="text-lg font-semibold mb-4">Create New Webhook</h3>
          <form onSubmit={handleCreateWebhook} className="space-y-4">
            {/* URL */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Endpoint URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://your-domain.com/webhooks"
                className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-2 text-sm"
                disabled={creating}
              />
              <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                Must be a publicly accessible HTTPS URL
              </p>
            </div>

            {/* Event Types */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Event Types <span className="text-red-500">*</span>
              </label>
              {EVENT_CATEGORIES.map((category) => (
                <div key={category} className="mb-3">
                  <p className="text-xs font-semibold text-[color:var(--color-text-secondary)] mb-2 uppercase">{category}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {AVAILABLE_EVENT_TYPES
                      .filter(e => e.category === category)
                      .map((eventType) => (
                        <label
                          key={eventType.value}
                          className={`flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                            selectedEvents.includes(eventType.value)
                              ? 'bg-[color:var(--color-accent)]/10 border-[color:var(--color-accent)]'
                              : 'bg-[color:var(--color-surface)] border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-muted)]'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedEvents.includes(eventType.value)}
                            onChange={() => toggleEvent(eventType.value)}
                            className="mt-1"
                            disabled={creating}
                          />
                          <div className="flex-1">
                            <span className="font-medium text-sm">{eventType.label}</span>
                            <p className="text-xs text-[color:var(--color-text-secondary)]">{eventType.description}</p>
                          </div>
                        </label>
                      ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              <button
                type="submit"
                disabled={creating || !webhookUrl.trim() || selectedEvents.length === 0}
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
                    Create Webhook
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

      {/* Webhooks List */}
      {webhooks.length === 0 ? (
        <div className="p-8 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)] text-center">
          <Webhook className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
          <p className="text-[color:var(--color-text-muted)] mb-1">No webhooks yet</p>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Create your first webhook to receive real-time event notifications
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div
              key={webhook.id}
              className={`p-4 rounded-lg border ${
                webhook.is_active
                  ? 'bg-[color:var(--color-panel)] border-[color:var(--color-border)]'
                  : 'bg-gray-500/5 border-gray-500/20'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Webhook className={`w-5 h-5 flex-shrink-0 ${
                      webhook.is_active ? 'text-green-500' : 'text-gray-400'
                    }`} />
                    <h3 className="font-semibold truncate">{webhook.url}</h3>
                    {getStatusBadge(webhook)}
                  </div>

                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                      <FileText className="w-4 h-4" />
                      <span className="font-mono text-xs">{webhook.event_types.join(', ')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[color:var(--color-text-secondary)]">
                      <Calendar className="w-4 h-4" />
                      <span>Created: {formatDate(webhook.created_at)}</span>
                    </div>
                    {webhook.last_success_at && (
                      <div className="flex items-center gap-2 text-green-500">
                        <CheckCircle className="w-4 h-4" />
                        <span>Last success: {formatDate(webhook.last_success_at)}</span>
                      </div>
                    )}
                    {webhook.last_failure_at && (
                      <div className="flex items-center gap-2 text-red-500">
                        <XCircle className="w-4 h-4" />
                        <span>Last failure: {formatDate(webhook.last_failure_at)} ({webhook.failure_count} failures)</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleToggleActive(webhook)}
                    className={`p-2 rounded-lg transition-colors ${
                      webhook.is_active
                        ? 'hover:bg-yellow-500/10 text-yellow-500'
                        : 'hover:bg-green-500/10 text-green-500'
                    }`}
                    title={webhook.is_active ? 'Disable webhook' : 'Enable webhook'}
                  >
                    {webhook.is_active ? <XCircle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                  </button>
                  <button
                    onClick={() => handleTestWebhook(webhook.id)}
                    className="p-2 rounded-lg hover:bg-blue-500/10 text-blue-500 transition-colors"
                    title="Send test webhook"
                  >
                    <Play className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleRotateSecret(webhook.id)}
                    className="p-2 rounded-lg hover:bg-yellow-500/10 text-yellow-500 transition-colors"
                    title="Rotate secret"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => toggleExpand(webhook.id)}
                    className="p-2 rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors"
                    title="View event logs"
                  >
                    {expandedWebhookId === webhook.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                  <button
                    onClick={() => handleDeleteWebhook(webhook.id, webhook.url)}
                    className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
                    title="Delete webhook"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Event Logs */}
              {expandedWebhookId === webhook.id && (
                <div className="mt-4 pt-4 border-t border-[color:var(--color-border)]">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold">Recent Event Deliveries</h4>
                    {loadingEvents[webhook.id] && (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent"></div>
                    )}
                  </div>
                  {!webhookEvents[webhook.id] || webhookEvents[webhook.id].length === 0 ? (
                    <p className="text-sm text-[color:var(--color-text-muted)] text-center py-4">
                      No events yet
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {webhookEvents[webhook.id].map((event) => (
                        <div
                          key={event.id}
                          className={`p-3 rounded-lg border ${
                            event.status === 'success'
                              ? 'bg-green-500/5 border-green-500/20'
                              : event.status === 'failed'
                              ? 'bg-red-500/5 border-red-500/20'
                              : event.status === 'retrying'
                              ? 'bg-yellow-500/5 border-yellow-500/20'
                              : 'bg-gray-500/5 border-gray-500/20'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-xs font-medium">{event.event_type}</span>
                                {event.status === 'success' && (
                                  <CheckCircle className="w-3 h-3 text-green-500" />
                                )}
                                {event.status === 'failed' && (
                                  <XCircle className="w-3 h-3 text-red-500" />
                                )}
                                {event.status === 'retrying' && (
                                  <RefreshCw className="w-3 h-3 text-yellow-500" />
                                )}
                                <span className="text-xs text-[color:var(--color-text-secondary)]">
                                  Attempt #{event.attempt_number}
                                </span>
                              </div>
                              <div className="text-xs text-[color:var(--color-text-secondary)]">
                                <Clock className="w-3 h-3 inline mr-1" />
                                {formatDate(event.attempted_at)}
                                {event.duration_ms && ` • ${event.duration_ms}ms`}
                              </div>
                              {event.response_status_code && (
                                <div className="text-xs text-[color:var(--color-text-secondary)] mt-1">
                                  Status: {event.response_status_code}
                                </div>
                              )}
                              {event.response_body && (
                                <div className="text-xs text-red-500 mt-1 truncate">
                                  {event.response_body}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
