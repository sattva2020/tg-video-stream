import React, { useMemo, useState } from 'react';
import { ResponsiveHeader } from '../../components/layout';
import { NotificationsNav } from '../../components/notifications/NotificationsNav';
import {
  parseSeverityFilter,
  toSeverityFilter,
  parseTagFilter,
  toTagFilter,
  parseHostFilter,
  toHostFilter,
  parseRateLimitConfig,
  toRateLimitConfig,
} from '../../components/notifications/filters';
import { RuleWizard, type RuleFormState } from '../../components/notifications/RuleWizard';
import {
  useNotificationRules,
  useCreateNotificationRule,
  useUpdateNotificationRule,
  useDeleteNotificationRule,
  useTestNotificationRule,
  useNotificationChannels,
  useNotificationRecipients,
  useNotificationTemplates,
} from '../../hooks/useNotifications';
import type { NotificationRule, NotificationRuleCreate } from '../../api/notifications';
import { useToast } from '../../hooks/useToast';
import { Plus, Trash2, Edit2, Play, ShieldAlert, X } from 'lucide-react';

// Вью-режимы страницы
type ViewMode = 'list' | 'wizard';

const defaultTestForm = {
  ruleId: '',
  severity: 'warning',
  tags: '{}',
  host: '',
  subject: 'Test notification',
  body: 'Эта отправка создана из UI правил',
};

const parseJsonSafe = (value: string): Record<string, unknown> | undefined => {
  if (!value || !value.trim()) return undefined;
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === 'object' ? (parsed as Record<string, unknown>) : undefined;
  } catch (e) {
    console.error('JSON parse error', e);
    return undefined;
  }
};

/**
 * Конвертирует RuleFormState в API payload
 */
const formToPayload = (form: RuleFormState): NotificationRuleCreate => ({
  name: form.name,
  enabled: form.enabled,
  severity_filter: toSeverityFilter(form.severityLevels),
  tag_filter: toTagFilter(form.tagConditions),
  host_filter: toHostFilter(form.hostConditions),
  silence_windows: undefined,
  rate_limit: toRateLimitConfig(form.maxMessages, form.windowSec),
  dedup_window_sec: form.dedupWindowSec,
  failover_timeout_sec: form.failoverTimeoutSec,
  template_id: form.templateId || undefined,
  recipient_ids: form.recipientIds,
  channel_ids: form.channelIds,
  test_channel_ids: undefined,
});

/**
 * Конвертирует NotificationRule в RuleFormState
 */
const ruleToForm = (rule: NotificationRule): Partial<RuleFormState> => {
  const rateLimitConfig = parseRateLimitConfig(rule.rate_limit, rule.dedup_window_sec);
  return {
    name: rule.name,
    description: '',
    enabled: rule.enabled,
    priority: 100,
    severityLevels: parseSeverityFilter(rule.severity_filter),
    tagConditions: parseTagFilter(rule.tag_filter),
    hostConditions: parseHostFilter(rule.host_filter),
    maxMessages: rateLimitConfig.maxMessages,
    windowSec: rateLimitConfig.windowSec,
    dedupWindowSec: rule.dedup_window_sec,
    recipientIds: rule.recipient_ids || [],
    channelIds: rule.channel_ids || [],
    templateId: rule.template_id || '',
    failoverTimeoutSec: rule.failover_timeout_sec,
  };
};

const RulesPage: React.FC = () => {
  const toast = useToast();

  const { data: rules = [], isLoading: rulesLoading } = useNotificationRules();
  const { data: channels = [], isLoading: channelsLoading } = useNotificationChannels();
  const { data: recipients = [], isLoading: recipientsLoading } = useNotificationRecipients();
  const { data: templates = [], isLoading: templatesLoading } = useNotificationTemplates();

  const createRule = useCreateNotificationRule();
  const updateRule = useUpdateNotificationRule();
  const deleteRule = useDeleteNotificationRule();
  const testRule = useTestNotificationRule();

  // Режим отображения
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null);
  const [testForm, setTestForm] = useState(defaultTestForm);

  const busy =
    createRule.isPending ||
    updateRule.isPending ||
    deleteRule.isPending ||
    testRule.isPending ||
    channelsLoading ||
    recipientsLoading ||
    templatesLoading;

  // Открыть wizard для создания
  const openCreateWizard = () => {
    setEditingRule(null);
    setViewMode('wizard');
  };

  // Открыть wizard для редактирования
  const openEditWizard = (rule: NotificationRule) => {
    setEditingRule(rule);
    setViewMode('wizard');
  };

  // Закрыть wizard
  const closeWizard = () => {
    setEditingRule(null);
    setViewMode('list');
  };

  // Сохранение из wizard
  const handleWizardSave = async (form: RuleFormState) => {
    const payload = formToPayload(form);

    try {
      if (editingRule) {
        await updateRule.mutateAsync({ id: editingRule.id, data: payload });
        toast.success('Правило обновлено');
      } else {
        await createRule.mutateAsync(payload);
        toast.success('Правило создано');
      }
      closeWizard();
    } catch (err) {
      toast.error(`Ошибка: ${err instanceof Error ? err.message : 'Неизвестная ошибка'}`);
    }
  };

  const handleTestRule = async () => {
    if (!testForm.ruleId) {
      toast.warning('Выберите правило для теста');
      return;
    }
    const payload = {
      severity: testForm.severity || undefined,
      tags: parseJsonSafe(testForm.tags),
      host: testForm.host || undefined,
      subject: testForm.subject || undefined,
      body: testForm.body || undefined,
    };
    await testRule.mutateAsync({ id: testForm.ruleId, payload });
  };

  const suppressionNotice = useMemo(
    () =>
      rules.some((r) => !r.enabled) ||
      recipients.some((r) => r.status === 'opt-out' || r.status === 'blocked') ||
      channels.some((c) => !c.enabled),
    [rules, recipients, channels]
  );

  // ===============================================
  // WIZARD MODE - полноэкранный wizard
  // ===============================================
  if (viewMode === 'wizard') {
    return (
      <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
        <ResponsiveHeader />
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          {/* Кнопка закрытия и заголовок */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-semibold">
                {editingRule ? 'Редактирование правила' : 'Новое правило'}
              </h1>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                Настройте правило маршрутизации уведомлений за 3 шага
              </p>
            </div>
            <button
              onClick={closeWizard}
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-3 py-2 text-sm hover:bg-white/5"
            >
              <X className="w-4 h-4" />
              Закрыть
            </button>
          </div>

          {/* Wizard */}
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] shadow-sm overflow-hidden min-h-[600px]">
            <RuleWizard
              initialData={editingRule ? ruleToForm(editingRule) : undefined}
              onSave={handleWizardSave}
              onCancel={closeWizard}
              loading={busy}
              channels={channels}
              recipients={recipients}
              templates={templates}
            />
          </div>
        </div>
      </div>
    );
  }

  // ===============================================
  // LIST MODE - список правил с тестом
  // ===============================================
  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <NotificationsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Оповещения: правила маршрутизации</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Настройте фильтры событий, адресатов, порядок каналов и таймауты failover.
          </p>
        </div>

        {suppressionNotice && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-yellow-400/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-300">
            <ShieldAlert className="w-5 h-5" />
            <span>
              Есть отключенные каналы или получатели в opt-out/blocked — такие адресаты будут пропущены.
            </span>
          </div>
        )}

        {/* Список правил */}
        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Правила</h2>
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
              onClick={openCreateWizard}
              disabled={busy}
            >
              <Plus className="w-4 h-4" /> Новое правило
            </button>
          </div>
          {rulesLoading ? (
            <p className="text-sm text-[color:var(--color-text-secondary)]">Загрузка правил...</p>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-4 flex flex-col gap-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-medium">{rule.name}</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">
                        Каналы: {rule.channel_ids.length} · Получатели: {rule.recipient_ids.length}
                      </p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">
                        Failover: {rule.failover_timeout_sec}s · Dedup: {rule.dedup_window_sec}s
                      </p>
                      {!rule.enabled && (
                        <p className="text-xs text-yellow-400">Правило выключено</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                          rule.enabled
                            ? 'bg-[color:var(--color-accent)] text-white'
                            : 'bg-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                        }`}
                        onClick={() => updateRule.mutate({ id: rule.id, data: { enabled: !rule.enabled } })}
                        type="button"
                        disabled={busy}
                      >
                        {rule.enabled ? 'Вкл' : 'Выкл'}
                      </button>
                      <button
                        className="p-2 rounded-md hover:bg-white/5"
                        onClick={() => openEditWizard(rule)}
                        disabled={busy}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 rounded-md hover:bg-white/5 text-red-400"
                        onClick={() => deleteRule.mutate(rule.id)}
                        disabled={busy}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {/* Краткий превью фильтров */}
                  <div className="flex flex-wrap gap-2">
                    {rule.severity_filter && (
                      <span className="px-2 py-1 rounded bg-purple-500/20 text-purple-300 text-xs">
                        Severity: {Array.isArray(rule.severity_filter.levels) ? rule.severity_filter.levels.join(', ') : 'custom'}
                      </span>
                    )}
                    {rule.tag_filter && (
                      <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-300 text-xs">
                        Tags: активны
                      </span>
                    )}
                    {rule.host_filter && (
                      <span className="px-2 py-1 rounded bg-green-500/20 text-green-300 text-xs">
                        Hosts: активны
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {rules.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-[color:var(--color-text-secondary)] mb-4">Правил пока нет</p>
                  <button
                    className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90"
                    onClick={openCreateWizard}
                  >
                    <Plus className="w-4 h-4" /> Создать первое правило
                  </button>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Секция теста правила */}
        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Тест правила</h2>
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
              onClick={handleTestRule}
              disabled={busy || !testForm.ruleId}
            >
              <Play className="w-4 h-4" /> Запустить
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1 text-sm">
              Правило
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.ruleId}
                onChange={(e) => setTestForm({ ...testForm, ruleId: e.target.value })}
              >
                <option value="">Выберите правило</option>
                {rules.map((rule) => (
                  <option key={rule.id} value={rule.id}>
                    {rule.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Severity
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.severity}
                onChange={(e) => setTestForm({ ...testForm, severity: e.target.value })}
                placeholder="warning"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Tags (JSON)
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                rows={3}
                value={testForm.tags}
                onChange={(e) => setTestForm({ ...testForm, tags: e.target.value })}
                placeholder='{"service": "api"}'
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Host
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.host}
                onChange={(e) => setTestForm({ ...testForm, host: e.target.value })}
                placeholder="web-01"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm md:col-span-2">
              Subject
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.subject}
                onChange={(e) => setTestForm({ ...testForm, subject: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm md:col-span-2">
              Body
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                rows={3}
                value={testForm.body}
                onChange={(e) => setTestForm({ ...testForm, body: e.target.value })}
              />
            </label>
          </div>
        </section>
      </div>
    </div>
  );
};

export default RulesPage;
