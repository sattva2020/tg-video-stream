import React, { useMemo, useState } from 'react';
import { Filter, RefreshCcw, ShieldOff, Timer, WifiOff } from 'lucide-react';
import { ResponsiveHeader } from '../../components/layout';
import {
  useNotificationLogs,
  useNotificationChannels,
  useNotificationRecipients,
  useNotificationRules,
  useUpdateNotificationRule,
} from '../../hooks/useNotifications';
import { DeliveryLogStatus } from '../../api/notifications';
import { useToast } from '../../hooks/useToast';

const statusPalette: Record<DeliveryLogStatus, string> = {
  success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-400/30',
  fail: 'bg-rose-500/10 text-rose-300 border border-rose-400/30',
  failover: 'bg-amber-500/10 text-amber-200 border border-amber-400/30',
  'rate-limited': 'bg-orange-500/10 text-orange-200 border border-orange-400/30',
  suppressed: 'bg-slate-500/15 text-slate-200 border border-slate-400/30',
  deduped: 'bg-indigo-500/10 text-indigo-200 border border-indigo-400/30',
};

const parseJsonSafe = (value: string) => {
  if (!value.trim()) return undefined;
  try {
    return JSON.parse(value);
  } catch (e) {
    console.error('Bad JSON', e);
    return undefined;
  }
};

const LogsPage: React.FC = () => {
  const toast = useToast();
  const { data: channels = [] } = useNotificationChannels();
  const { data: recipients = [] } = useNotificationRecipients();
  const { data: rules = [] } = useNotificationRules();

  const [statusFilter, setStatusFilter] = useState<string[]>(['fail', 'failover', 'suppressed']);
  const [ruleFilter, setRuleFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [recipientFilter, setRecipientFilter] = useState('');
  const [eventIdFilter, setEventIdFilter] = useState('');
  const [fromFilter, setFromFilter] = useState('');
  const [toFilter, setToFilter] = useState('');

  const filters = useMemo(
    () => ({
      rule_id: ruleFilter || undefined,
      channel_id: channelFilter || undefined,
      recipient_id: recipientFilter || undefined,
      event_id: eventIdFilter || undefined,
      statuses: statusFilter.length ? statusFilter : undefined,
      created_from: fromFilter ? new Date(fromFilter).toISOString() : undefined,
      created_to: toFilter ? new Date(toFilter).toISOString() : undefined,
      limit: 200,
    }),
    [ruleFilter, channelFilter, recipientFilter, eventIdFilter, statusFilter, fromFilter, toFilter]
  );

  const { data: logs = [], isLoading, refetch } = useNotificationLogs(filters);

  const [controlsRule, setControlsRule] = useState('');
  const [silenceWindows, setSilenceWindows] = useState('[{"start":"22:00","end":"08:00"}]');
  const [rateLimit, setRateLimit] = useState('{"limit":5,"window_sec":60}');
  const updateRule = useUpdateNotificationRule();

  const handleStatusToggle = (value: string) => {
    setStatusFilter((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const handleControlsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!controlsRule) {
      toast.warning('Выберите правило для обновления окон тишины/лимитов');
      return;
    }
    const silencePayload = parseJsonSafe(silenceWindows);
    const rateLimitPayload = parseJsonSafe(rateLimit);
    await updateRule.mutateAsync({
      id: controlsRule,
      data: {
        silence_windows: silencePayload,
        rate_limit: rateLimitPayload,
      },
    });
    toast.success('Правило обновлено');
  };

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Оповещения: журнал доставки и окна тишины</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Фильтруйте статусы suppressed / rate-limited / deduped и оперативно настраивайте окна тишины и лимиты для правил.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="lg:col-span-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-secondary)]">
                <Filter className="w-4 h-4" /> Фильтры журнала
              </div>
              <button
                className="inline-flex items-center gap-2 rounded-md border border-[color:var(--color-border)] px-3 py-1 text-sm hover:bg-white/5"
                onClick={() => refetch()}
              >
                <RefreshCcw className="w-4 h-4" /> Обновить
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Статусы
                <div className="flex flex-wrap gap-2">
                  {['success', 'fail', 'failover', 'suppressed', 'rate-limited', 'deduped'].map((value) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => handleStatusToggle(value)}
                      className={`rounded-full px-3 py-1 text-xs border transition ${
                        statusFilter.includes(value)
                          ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10'
                          : 'border-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                      }`}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Канал
                <select
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={channelFilter}
                  onChange={(e) => setChannelFilter(e.target.value)}
                >
                  <option value="">Любой</option>
                  {channels.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Получатель
                <select
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={recipientFilter}
                  onChange={(e) => setRecipientFilter(e.target.value)}
                >
                  <option value="">Любой</option>
                  {recipients.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.address}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Правило
                <select
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={ruleFilter}
                  onChange={(e) => setRuleFilter(e.target.value)}
                >
                  <option value="">Любое</option>
                  {rules.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Event ID
                <input
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={eventIdFilter}
                  onChange={(e) => setEventIdFilter(e.target.value)}
                  placeholder="abc-123"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                С
                <input
                  type="datetime-local"
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={fromFilter}
                  onChange={(e) => setFromFilter(e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                По
                <input
                  type="datetime-local"
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={toFilter}
                  onChange={(e) => setToFilter(e.target.value)}
                />
              </label>
            </div>
          </div>

          <form
            className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm space-y-3"
            onSubmit={handleControlsSubmit}
          >
            <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-secondary)]">
              <Timer className="w-4 h-4" /> Окна тишины / rate-limit
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Правило
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={controlsRule}
                onChange={(e) => setControlsRule(e.target.value)}
              >
                <option value="">Выберите правило</option>
                {rules.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Окна тишины (JSON массив)
              <textarea
                className="min-h-[80px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                value={silenceWindows}
                onChange={(e) => setSilenceWindows(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Rate-limit (JSON)
              <textarea
                className="min-h-[80px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                value={rateLimit}
                onChange={(e) => setRateLimit(e.target.value)}
              />
            </label>
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-md bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
              disabled={updateRule.isPending}
            >
              <ShieldOff className="w-4 h-4" /> Сохранить
            </button>
            <p className="text-xs text-[color:var(--color-text-secondary)]">
              Пример окна: {`[{"start":"22:00","end":"08:00"}]`} · Rate-limit: {`{"limit":3,"window_sec":60}`}
            </p>
          </form>
        </div>

        <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[color:var(--color-border)]">
            <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-secondary)]">
              <WifiOff className="w-4 h-4" /> Последние события ({logs.length})
            </div>
            {isLoading && <span className="text-xs text-[color:var(--color-text-secondary)]">Обновление...</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-secondary)]">
                <tr>
                  <th className="px-3 py-2 text-left">Статус</th>
                  <th className="px-3 py-2 text-left">Event</th>
                  <th className="px-3 py-2 text-left">Правило</th>
                  <th className="px-3 py-2 text-left">Канал</th>
                  <th className="px-3 py-2 text-left">Получатель</th>
                  <th className="px-3 py-2 text-left">Ответ</th>
                  <th className="px-3 py-2 text-left">Ошибка</th>
                  <th className="px-3 py-2 text-left">Создано</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--color-border)]">
                {logs.map((log) => {
                  const badge = statusPalette[log.status] || 'bg-white/5 text-[color:var(--color-text-secondary)] border border-[color:var(--color-border)]';
                  const ruleName = rules.find((r) => r.id === log.rule_id)?.name || '—';
                  const channelName = channels.find((c) => c.id === log.channel_id)?.name || '—';
                  const recipientAddr = recipients.find((r) => r.id === log.recipient_id)?.address || '—';
                  return (
                    <tr key={log.id} className="hover:bg-white/5">
                      <td className="px-3 py-2">
                        <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs ${badge}`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">{log.event_id}</td>
                      <td className="px-3 py-2">{ruleName}</td>
                      <td className="px-3 py-2">{channelName}</td>
                      <td className="px-3 py-2">{recipientAddr}</td>
                      <td className="px-3 py-2 text-xs">
                        {log.response_code ? `HTTP ${log.response_code}` : '—'}
                        {log.latency_ms ? ` · ${log.latency_ms}ms` : ''}
                      </td>
                      <td className="px-3 py-2 text-xs text-rose-200 max-w-[240px] truncate" title={log.error_message || ''}>
                        {log.error_message || '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-[color:var(--color-text-secondary)]">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
                {!logs.length && !isLoading && (
                  <tr>
                    <td className="px-3 py-4 text-center text-[color:var(--color-text-secondary)]" colSpan={8}>
                      Логи не найдены под выбранные фильтры
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
