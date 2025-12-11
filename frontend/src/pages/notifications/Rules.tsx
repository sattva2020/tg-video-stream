import React, { useMemo, useState } from 'react';
import { ResponsiveHeader } from '../../components/layout';
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
import { Plus, Trash2, Edit2, ArrowUp, ArrowDown, Play, ShieldAlert } from 'lucide-react';

const defaultRuleForm = {
  name: '',
  enabled: true,
  severity_filter: '{}',
  tag_filter: '{}',
  host_filter: '{}',
  silence_windows: '{}',
  rate_limit: '{}',
  dedup_window_sec: 0,
  failover_timeout_sec: 30,
  template_id: '',
  recipient_ids: [] as string[],
  channel_ids: [] as string[],
  test_channel_ids: [] as string[],
};

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

  const [ruleForm, setRuleForm] = useState(defaultRuleForm);
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null);
  const [testForm, setTestForm] = useState(defaultTestForm);
  const [channelToAdd, setChannelToAdd] = useState('');

  const busy =
    createRule.isPending ||
    updateRule.isPending ||
    deleteRule.isPending ||
    testRule.isPending ||
    channelsLoading ||
    recipientsLoading ||
    templatesLoading;

  const addChannelToOrder = () => {
    if (!channelToAdd) return;
    if (ruleForm.channel_ids.includes(channelToAdd)) {
      toast.warning('Канал уже в порядке эскалации');
      return;
    }
    setRuleForm({ ...ruleForm, channel_ids: [...ruleForm.channel_ids, channelToAdd] });
    setChannelToAdd('');
  };

  const moveChannel = (index: number, direction: -1 | 1) => {
    const next = [...ruleForm.channel_ids];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= next.length) return;
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    setRuleForm({ ...ruleForm, channel_ids: next });
  };

  const removeChannel = (index: number) => {
    const next = [...ruleForm.channel_ids];
    next.splice(index, 1);
    setRuleForm({ ...ruleForm, channel_ids: next });
  };

  const handleRecipientSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = Array.from(e.target.selectedOptions).map((opt) => opt.value);
    setRuleForm({ ...ruleForm, recipient_ids: selected });
  };

  const handleTestChannelSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = Array.from(e.target.selectedOptions).map((opt) => opt.value);
    setRuleForm({ ...ruleForm, test_channel_ids: selected });
  };

  const resetForm = () => {
    setEditingRule(null);
    setRuleForm(defaultRuleForm);
  };

  const handleRuleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleForm.recipient_ids.length) {
      toast.warning('Добавьте хотя бы одного получателя');
      return;
    }
    if (!ruleForm.channel_ids.length) {
      toast.warning('Укажите порядок каналов');
      return;
    }

    const payload: NotificationRuleCreate = {
      name: ruleForm.name,
      enabled: ruleForm.enabled,
      severity_filter: parseJsonSafe(ruleForm.severity_filter),
      tag_filter: parseJsonSafe(ruleForm.tag_filter),
      host_filter: parseJsonSafe(ruleForm.host_filter),
      silence_windows: parseJsonSafe(ruleForm.silence_windows),
      rate_limit: parseJsonSafe(ruleForm.rate_limit),
      dedup_window_sec: Number(ruleForm.dedup_window_sec) || 0,
      failover_timeout_sec: Number(ruleForm.failover_timeout_sec) || 0,
      template_id: ruleForm.template_id || undefined,
      recipient_ids: ruleForm.recipient_ids,
      channel_ids: ruleForm.channel_ids,
      test_channel_ids: ruleForm.test_channel_ids?.length ? ruleForm.test_channel_ids : undefined,
    };

    if (editingRule) {
      await updateRule.mutateAsync({ id: editingRule.id, data: payload });
    } else {
      await createRule.mutateAsync(payload);
    }

    resetForm();
  };

  const handleEditRule = (rule: NotificationRule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      enabled: rule.enabled,
      severity_filter: JSON.stringify(rule.severity_filter || {}, null, 2),
      tag_filter: JSON.stringify(rule.tag_filter || {}, null, 2),
      host_filter: JSON.stringify(rule.host_filter || {}, null, 2),
      silence_windows: JSON.stringify(rule.silence_windows || {}, null, 2),
      rate_limit: JSON.stringify(rule.rate_limit || {}, null, 2),
      dedup_window_sec: rule.dedup_window_sec,
      failover_timeout_sec: rule.failover_timeout_sec,
      template_id: rule.template_id || '',
      recipient_ids: rule.recipient_ids || [],
      channel_ids: rule.channel_ids || [],
      test_channel_ids: rule.test_channel_ids || [],
    });
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

  const availableChannels = useMemo(
    () => channels.filter((c) => !ruleForm.channel_ids.includes(c.id)),
    [channels, ruleForm.channel_ids]
  );

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Оповещения: правила маршрутизации</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Настройте фильтры событий, адресатов, порядок каналов и таймауты failover. Тестовая отправка проверит
            эскалацию с текущими настройками.
          </p>
        </div>

        {suppressionNotice && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-yellow-400/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-300">
            <ShieldAlert className="w-5 h-5" />
            <span>
              Есть отключенные каналы или получатели в opt-out/blocked — такие адресаты будут пропущены, статус
              попадёт в DeliveryLog.
            </span>
          </div>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Правила</h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
                onClick={resetForm}
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
                    className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-3 flex flex-col gap-3"
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
                          <p className="text-xs text-yellow-400">Правило выключено — события будут пропущены</p>
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
                          onClick={() => handleEditRule(rule)}
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
                    <div className="flex flex-wrap gap-2 text-xs text-[color:var(--color-text-secondary)]">
                      {rule.severity_filter && <span>Severity: {JSON.stringify(rule.severity_filter)}</span>}
                      {rule.tag_filter && <span>Tags: {JSON.stringify(rule.tag_filter)}</span>}
                      {rule.host_filter && <span>Hosts: {JSON.stringify(rule.host_filter)}</span>}
                    </div>
                  </div>
                ))}
                {rules.length === 0 && (
                  <p className="text-sm text-[color:var(--color-text-secondary)]">Правил пока нет</p>
                )}
              </div>
            )}
          </div>

          <form
            className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm flex flex-col gap-3"
            onSubmit={handleRuleSubmit}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">
                {editingRule ? 'Редактирование правила' : 'Новое правило'}
              </h3>
              {editingRule && (
                <button type="button" className="text-sm text-[color:var(--color-accent)]" onClick={resetForm}>
                  Сброс
                </button>
              )}
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Название
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={ruleForm.name}
                onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                required
              />
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Таймаут failover, сек
                <input
                  type="number"
                  min={0}
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={ruleForm.failover_timeout_sec}
                  onChange={(e) => setRuleForm({ ...ruleForm, failover_timeout_sec: Number(e.target.value) })}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Окно дедупликации, сек
                <input
                  type="number"
                  min={0}
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={ruleForm.dedup_window_sec}
                  onChange={(e) => setRuleForm({ ...ruleForm, dedup_window_sec: Number(e.target.value) })}
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={ruleForm.enabled}
                onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })}
              />
              Правило активно
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Severity filter (JSON)
                <textarea
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                  rows={3}
                  value={ruleForm.severity_filter}
                  onChange={(e) => setRuleForm({ ...ruleForm, severity_filter: e.target.value })}
                  placeholder='{"levels": ["critical", "warning"]}'
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Tag filter (JSON)
                <textarea
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                  rows={3}
                  value={ruleForm.tag_filter}
                  onChange={(e) => setRuleForm({ ...ruleForm, tag_filter: e.target.value })}
                  placeholder='{"service": ["billing"], "env": ["prod"]}'
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Host filter (JSON)
                <textarea
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                  rows={3}
                  value={ruleForm.host_filter}
                  onChange={(e) => setRuleForm({ ...ruleForm, host_filter: e.target.value })}
                  placeholder='{"include": ["web-*"], "exclude": ["dev-*"]}'
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Окна тишины (JSON)
                <textarea
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                  rows={3}
                  value={ruleForm.silence_windows}
                  onChange={(e) => setRuleForm({ ...ruleForm, silence_windows: e.target.value })}
                  placeholder='{"cron": "0 0 * * *"}'
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Rate limit (JSON)
                <textarea
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                  rows={3}
                  value={ruleForm.rate_limit}
                  onChange={(e) => setRuleForm({ ...ruleForm, rate_limit: e.target.value })}
                  placeholder='{"per_recipient_min": 5}'
                />
              </label>
            </div>

            <label className="flex flex-col gap-1 text-sm">
              Шаблон
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={ruleForm.template_id}
                onChange={(e) => setRuleForm({ ...ruleForm, template_id: e.target.value })}
              >
                <option value="">Без шаблона</option>
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name} ({tpl.locale})
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              Получатели
              <select
                multiple
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 min-h-[120px]"
                value={ruleForm.recipient_ids}
                onChange={handleRecipientSelect}
              >
                {recipients.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.address} ({r.type}) {r.status !== 'active' ? `· ${r.status}` : ''}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex flex-col gap-2 text-sm">
              <div className="flex items-center gap-2">
                <label className="flex flex-col gap-1 flex-1">
                  Добавить канал в порядок эскалации
                  <select
                    className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                    value={channelToAdd}
                    onChange={(e) => setChannelToAdd(e.target.value)}
                  >
                    <option value="">Выберите канал</option>
                    {availableChannels.map((channel) => (
                      <option key={channel.id} value={channel.id}>
                        {channel.name} ({channel.type})
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
                  onClick={addChannelToOrder}
                  disabled={busy}
                >
                  Добавить
                </button>
              </div>

              <div className="space-y-2">
                {ruleForm.channel_ids.map((id, idx) => {
                  const channel = channels.find((c) => c.id === id);
                  return (
                    <div
                      key={id}
                      className="flex items-center justify-between rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                    >
                      <div className="text-sm">
                        {channel?.name || 'Неизвестный канал'}{' '}
                        <span className="text-[color:var(--color-text-secondary)]">({channel?.type || id})</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          className="p-1 rounded hover:bg-white/5"
                          onClick={() => moveChannel(idx, -1)}
                          disabled={idx === 0}
                          aria-label="Move up"
                        >
                          <ArrowUp className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          className="p-1 rounded hover:bg-white/5"
                          onClick={() => moveChannel(idx, 1)}
                          disabled={idx === ruleForm.channel_ids.length - 1}
                          aria-label="Move down"
                        >
                          <ArrowDown className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          className="p-1 rounded hover:bg-white/5 text-red-400"
                          onClick={() => removeChannel(idx)}
                          aria-label="Remove"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
                {ruleForm.channel_ids.length === 0 && (
                  <p className="text-xs text-[color:var(--color-text-secondary)]">Порядок каналов пуст</p>
                )}
              </div>
            </div>

            <label className="flex flex-col gap-1 text-sm">
              Тестовые каналы (опционально)
              <select
                multiple
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 min-h-[100px]"
                value={ruleForm.test_channel_ids}
                onChange={handleTestChannelSelect}
              >
                {channels.map((channel) => (
                  <option key={channel.id} value={channel.id}>
                    {channel.name} ({channel.type})
                  </option>
                ))}
              </select>
              <span className="text-xs text-[color:var(--color-text-secondary)]">
                Если не выбрано, тест использует основной порядок каналов
              </span>
            </label>

            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90"
              disabled={busy}
            >
              {editingRule ? 'Сохранить правило' : 'Создать правило'}
            </button>
          </form>
        </section>

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
