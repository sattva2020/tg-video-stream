import React, { useMemo, useState } from 'react';
import { ResponsiveHeader } from '../../components/layout';
import { NotificationsNav } from '../../components/notifications/NotificationsNav';
import {
  useNotificationChannels,
  useCreateNotificationChannel,
  useUpdateNotificationChannel,
  useDeleteNotificationChannel,
  useTestNotificationChannel,
} from '../../hooks/useNotifications';
import type { NotificationChannel } from '../../api/notifications';
import { useToast } from '../../hooks/useToast';
import { Plus, Send, Trash2, Edit2, ShieldAlert, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const defaultChannelForm = {
  name: '',
  type: 'email',
  config: '{}',
  enabled: true,
  status: 'ok',
  concurrency_limit: 5,
  retry_attempts: 3,
  retry_interval_sec: 30,
  timeout_sec: 10,
  is_primary: false,
};

const CHANNEL_PRESETS: Record<string, string> = {
  discord: JSON.stringify({ url: '', method: 'POST' }, null, 2),
  slack: JSON.stringify({ url: '', method: 'POST' }, null, 2),
  telegram: JSON.stringify({ token: '' }, null, 2),
  email: JSON.stringify({ smtp_host: '', smtp_port: 587, user: '', password: '' }, null, 2),
};

const StatusIcon = ({ status, enabled }: { status: string; enabled: boolean }) => {
  if (!enabled) return <XCircle className="w-5 h-5 text-gray-400" />;
  if (status === 'ok') return <CheckCircle className="w-5 h-5 text-emerald-500" />;
  if (status === 'error') return <XCircle className="w-5 h-5 text-rose-500" />;
  return <AlertTriangle className="w-5 h-5 text-amber-500" />;
};

const parseJsonSafe = (value: string) => {
  if (!value.trim()) return {};
  try {
    return JSON.parse(value);
  } catch (e) {
    console.error('JSON parse error', e);
    return {};
  }
};

const NotificationsChannelsPage: React.FC = () => {
  const toast = useToast();

  const { data: channels = [], isLoading: channelsLoading } = useNotificationChannels();

  const createChannel = useCreateNotificationChannel();
  const updateChannel = useUpdateNotificationChannel();
  const deleteChannel = useDeleteNotificationChannel();
  const testChannel = useTestNotificationChannel();

  const [channelForm, setChannelForm] = useState(defaultChannelForm);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);

  const [testForm, setTestForm] = useState({
    channelId: '',
    recipient: '',
    subject: '',
    body: 'Test notification',
  });

  const busy =
    channelsLoading ||
    createChannel.isPending ||
    updateChannel.isPending ||
    deleteChannel.isPending ||
    testChannel.isPending;

  const handleChannelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...channelForm,
      config: parseJsonSafe(channelForm.config),
    } as any;

    if (editingChannel) {
      await updateChannel.mutateAsync({ id: editingChannel.id, data: payload });
    } else {
      await createChannel.mutateAsync(payload);
    }
    setEditingChannel(null);
    setChannelForm(defaultChannelForm);
  };

  const handleTestSend = async () => {
    if (!testForm.channelId || !testForm.recipient) {
      toast.warning('Укажите канал и получателя для теста');
      return;
    }
    await testChannel.mutateAsync({
      id: testForm.channelId,
      payload: {
        recipient: testForm.recipient,
        subject: testForm.subject || undefined,
        body: testForm.body || undefined,
        use_celery: true,
      },
    });
  };

  const suppressionNotice = useMemo(
    () => channels.some((c) => !c.enabled),
    [channels]
  );

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <NotificationsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Каналы уведомлений</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Управление транспортами (Telegram, Email, Webhook).
          </p>
        </div>

        {suppressionNotice && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-yellow-400/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-300">
            <ShieldAlert className="w-5 h-5" />
            <span>
              Некоторые каналы выключены — отправки через них будут подавлены.
            </span>
          </div>
        )}

        {/* Channels */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Список каналов</h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
                onClick={() => {
                  setEditingChannel(null);
                  setChannelForm(defaultChannelForm);
                }}
                disabled={busy}
              >
                <Plus className="w-4 h-4" /> Новый
              </button>
            </div>

            {channelsLoading ? (
              <p className="text-sm text-[color:var(--color-text-secondary)]">Загрузка каналов...</p>
            ) : (
              <div className="space-y-3">
                {channels.map((channel) => (
                  <div
                    key={channel.id}
                    className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-3 flex flex-col gap-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <StatusIcon status={channel.status} enabled={channel.enabled} />
                        <div>
                          <p className="font-medium">{channel.name}</p>
                          <p className="text-xs text-[color:var(--color-text-secondary)]">
                            {channel.type}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                            channel.enabled
                              ? 'bg-[color:var(--color-accent)] text-white'
                              : 'bg-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                          }`}
                          onClick={() =>
                            updateChannel.mutate({ id: channel.id, data: { enabled: !channel.enabled } })
                          }
                          type="button"
                          disabled={busy}
                        >
                          {channel.enabled ? 'Вкл' : 'Выкл'}
                        </button>
                        <button
                          className="p-2 rounded-md hover:bg-white/5"
                          onClick={() => {
                            setEditingChannel(channel);
                            setChannelForm({
                              name: channel.name,
                              type: channel.type,
                              config: JSON.stringify(channel.config, null, 2),
                              enabled: channel.enabled,
                              status: channel.status,
                              concurrency_limit: channel.concurrency_limit ?? undefined,
                              retry_attempts: channel.retry_attempts,
                              retry_interval_sec: channel.retry_interval_sec,
                              timeout_sec: channel.timeout_sec,
                              is_primary: channel.is_primary,
                            } as any);
                          }}
                          disabled={busy}
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          className="p-2 rounded-md hover:bg-white/5 text-red-400"
                          onClick={() => deleteChannel.mutate(channel.id)}
                          disabled={busy}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-[color:var(--color-text-secondary)]">
                      <span>Retry: {channel.retry_attempts} × {channel.retry_interval_sec}s</span>
                      <span>Timeout: {channel.timeout_sec}s</span>
                      {channel.concurrency_limit && <span>Пул: {channel.concurrency_limit}</span>}
                    </div>
                  </div>
                ))}

                {channels.length === 0 && (
                  <p className="text-sm text-[color:var(--color-text-secondary)]">Каналов нет</p>
                )}
              </div>
            )}
          </div>

          <form
            className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm flex flex-col gap-3"
            onSubmit={handleChannelSubmit}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">
                {editingChannel ? 'Редактирование канала' : 'Новый канал'}
              </h3>
              {editingChannel && (
                <button
                  type="button"
                  className="text-sm text-[color:var(--color-accent)]"
                  onClick={() => {
                    setEditingChannel(null);
                    setChannelForm(defaultChannelForm);
                  }}
                >
                  Сброс
                </button>
              )}
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Название
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={channelForm.name}
                onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
                required
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Тип
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={channelForm.type}
                onChange={(e) => {
                  const newType = e.target.value;
                  const preset = CHANNEL_PRESETS[newType];
                  setChannelForm({
                    ...channelForm,
                    type: newType,
                    config: preset || channelForm.config,
                  });
                }}
              >
                <option value="email">Email</option>
                <option value="telegram">Telegram</option>
                <option value="webhook">Webhook</option>
                <option value="slack">Slack</option>
                <option value="discord">Discord</option>
                <option value="sms">SMS</option>
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Retry attempts
                <input
                  type="number"
                  min={0}
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={channelForm.retry_attempts}
                  onChange={(e) =>
                    setChannelForm({ ...channelForm, retry_attempts: Number(e.target.value) })
                  }
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Retry interval, sec
                <input
                  type="number"
                  min={0}
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                  value={channelForm.retry_interval_sec}
                  onChange={(e) =>
                    setChannelForm({ ...channelForm, retry_interval_sec: Number(e.target.value) })
                  }
                />
              </label>
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Timeout, sec
              <input
                type="number"
                min={1}
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={channelForm.timeout_sec}
                onChange={(e) => setChannelForm({ ...channelForm, timeout_sec: Number(e.target.value) })}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={channelForm.enabled}
                onChange={(e) => setChannelForm({ ...channelForm, enabled: e.target.checked })}
              />
              Канал включен
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Config (JSON)
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                rows={5}
                value={channelForm.config}
                onChange={(e) => setChannelForm({ ...channelForm, config: e.target.value })}
                placeholder='{"smtp_host": "smtp.example.com"}'
              />
            </label>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90"
              disabled={busy}
            >
              {editingChannel ? 'Сохранить' : 'Создать канал'}
            </button>
          </form>
        </section>

        {/* Test send */}
        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Тестовая отправка</h2>
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
              onClick={handleTestSend}
              disabled={busy || testChannel.isPending}
            >
              <Send className="w-4 h-4" /> Отправить тест
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1 text-sm">
              Канал
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.channelId}
                onChange={(e) => setTestForm({ ...testForm, channelId: e.target.value })}
              >
                <option value="">Выберите канал</option>
                {channels.map((channel) => (
                  <option key={channel.id} value={channel.id}>
                    {channel.name} ({channel.type})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Получатель
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.recipient}
                onChange={(e) => setTestForm({ ...testForm, recipient: e.target.value })}
                placeholder="email, chat_id или url"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Тема
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={testForm.subject}
                onChange={(e) => setTestForm({ ...testForm, subject: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm md:col-span-2">
              Текст
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

export default NotificationsChannelsPage;
