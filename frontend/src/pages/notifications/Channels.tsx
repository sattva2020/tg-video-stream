import React, { useMemo, useState } from 'react';
import { ResponsiveHeader } from '../../components/layout';
import {
  useNotificationChannels,
  useCreateNotificationChannel,
  useUpdateNotificationChannel,
  useDeleteNotificationChannel,
  useTestNotificationChannel,
  useNotificationTemplates,
  useCreateNotificationTemplate,
  useUpdateNotificationTemplate,
  useDeleteNotificationTemplate,
  useNotificationRecipients,
  useCreateNotificationRecipient,
  useUpdateNotificationRecipient,
  useDeleteNotificationRecipient,
} from '../../hooks/useNotifications';
import type {
  NotificationChannel,
  NotificationTemplate,
  NotificationRecipient,
} from '../../api/notifications';
import { useToast } from '../../hooks/useToast';
import { Plus, Send, Trash2, Edit2, ShieldAlert } from 'lucide-react';

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

const defaultTemplateForm = {
  name: '',
  locale: 'en',
  subject: '',
  body: '',
  variables: '{}',
};

const defaultRecipientForm = {
  type: 'email',
  address: '',
  status: 'active',
  silence_windows: '{}',
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
  const { data: templates = [], isLoading: templatesLoading } = useNotificationTemplates();
  const { data: recipients = [], isLoading: recipientsLoading } = useNotificationRecipients();

  const createChannel = useCreateNotificationChannel();
  const updateChannel = useUpdateNotificationChannel();
  const deleteChannel = useDeleteNotificationChannel();
  const testChannel = useTestNotificationChannel();

  const createTemplate = useCreateNotificationTemplate();
  const updateTemplate = useUpdateNotificationTemplate();
  const deleteTemplate = useDeleteNotificationTemplate();

  const createRecipient = useCreateNotificationRecipient();
  const updateRecipient = useUpdateNotificationRecipient();
  const deleteRecipient = useDeleteNotificationRecipient();

  const [channelForm, setChannelForm] = useState(defaultChannelForm);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);

  const [templateForm, setTemplateForm] = useState(defaultTemplateForm);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null);

  const [recipientForm, setRecipientForm] = useState(defaultRecipientForm);
  const [editingRecipient, setEditingRecipient] = useState<NotificationRecipient | null>(null);

  const [testForm, setTestForm] = useState({
    channelId: '',
    recipient: '',
    subject: '',
    body: 'Test notification',
  });

  const busy =
    channelsLoading ||
    templatesLoading ||
    recipientsLoading ||
    createChannel.isPending ||
    updateChannel.isPending ||
    deleteChannel.isPending ||
    createTemplate.isPending ||
    updateTemplate.isPending ||
    deleteTemplate.isPending ||
    createRecipient.isPending ||
    updateRecipient.isPending ||
    deleteRecipient.isPending;

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

  const handleTemplateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...templateForm,
      variables: parseJsonSafe(templateForm.variables),
    } as any;

    if (editingTemplate) {
      await updateTemplate.mutateAsync({ id: editingTemplate.id, data: payload });
    } else {
      await createTemplate.mutateAsync(payload);
    }
    setEditingTemplate(null);
    setTemplateForm(defaultTemplateForm);
  };

  const handleRecipientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...recipientForm,
      silence_windows: parseJsonSafe(recipientForm.silence_windows),
    } as any;

    if (editingRecipient) {
      await updateRecipient.mutateAsync({ id: editingRecipient.id, data: payload });
    } else {
      await createRecipient.mutateAsync(payload);
    }
    setEditingRecipient(null);
    setRecipientForm(defaultRecipientForm);
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
    () =>
      recipients.some((r) => r.status === 'opt-out' || r.status === 'blocked') ||
      channels.some((c) => !c.enabled),
    [recipients, channels]
  );

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Оповещения: каналы и шаблоны</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Управление транспортами, шаблонами и получателями. Тестовая отправка доступна для любого канала.
          </p>
        </div>

        {suppressionNotice && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-yellow-400/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-300">
            <ShieldAlert className="w-5 h-5" />
            <span>
              Некоторые каналы выключены или получатели в opt-out/blocked — такие отправки будут подавлены.
            </span>
          </div>
        )}

        {/* Channels */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Каналы</h2>
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
                      <div>
                        <p className="font-medium">{channel.name}</p>
                        <p className="text-xs text-[color:var(--color-text-secondary)]">
                          {channel.type} · статус: {channel.status}
                        </p>
                        {!channel.enabled && (
                          <p className="text-xs text-yellow-400">Канал выключен — отправки будут подавлены</p>
                        )}
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
                onChange={(e) => setChannelForm({ ...channelForm, type: e.target.value })}
              >
                <option value="email">Email</option>
                <option value="telegram">Telegram</option>
                <option value="webhook">Webhook</option>
                <option value="slack">Slack</option>
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

        {/* Templates */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Шаблоны</h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
                onClick={() => {
                  setEditingTemplate(null);
                  setTemplateForm(defaultTemplateForm);
                }}
                disabled={busy}
              >
                <Plus className="w-4 h-4" /> Новый
              </button>
            </div>
            {templatesLoading ? (
              <p className="text-sm text-[color:var(--color-text-secondary)]">Загрузка шаблонов...</p>
            ) : (
              <div className="space-y-3">
                {templates.map((template) => (
                  <div
                    key={template.id}
                    className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-3 flex items-start justify-between gap-3"
                  >
                    <div>
                      <p className="font-medium">{template.name}</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">Locale: {template.locale}</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)] truncate max-w-xl">
                        {template.subject || 'Без темы'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className="p-2 rounded-md hover:bg-white/5"
                        onClick={() => {
                          setEditingTemplate(template);
                          setTemplateForm({
                            name: template.name,
                            locale: template.locale,
                            subject: template.subject || '',
                            body: template.body,
                            variables: JSON.stringify(template.variables || {}, null, 2),
                          });
                        }}
                        disabled={busy}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 rounded-md hover:bg-white/5 text-red-400"
                        onClick={() => deleteTemplate.mutate(template.id)}
                        disabled={busy}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
                {templates.length === 0 && (
                  <p className="text-sm text-[color:var(--color-text-secondary)]">Шаблонов нет</p>
                )}
              </div>
            )}
          </div>

          <form
            className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm flex flex-col gap-3"
            onSubmit={handleTemplateSubmit}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">
                {editingTemplate ? 'Редактирование шаблона' : 'Новый шаблон'}
              </h3>
              {editingTemplate && (
                <button
                  type="button"
                  className="text-sm text-[color:var(--color-accent)]"
                  onClick={() => {
                    setEditingTemplate(null);
                    setTemplateForm(defaultTemplateForm);
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
                value={templateForm.name}
                onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                required
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Locale
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={templateForm.locale}
                onChange={(e) => setTemplateForm({ ...templateForm, locale: e.target.value })}
              >
                <option value="en">en</option>
                <option value="ru">ru</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Subject
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={templateForm.subject}
                onChange={(e) => setTemplateForm({ ...templateForm, subject: e.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Body
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                rows={5}
                value={templateForm.body}
                onChange={(e) => setTemplateForm({ ...templateForm, body: e.target.value })}
                required
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Variables (JSON)
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                rows={4}
                value={templateForm.variables}
                onChange={(e) => setTemplateForm({ ...templateForm, variables: e.target.value })}
              />
            </label>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90"
              disabled={busy}
            >
              {editingTemplate ? 'Сохранить' : 'Создать шаблон'}
            </button>
          </form>
        </section>

        {/* Recipients */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Получатели</h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
                onClick={() => {
                  setEditingRecipient(null);
                  setRecipientForm(defaultRecipientForm);
                }}
                disabled={busy}
              >
                <Plus className="w-4 h-4" /> Новый
              </button>
            </div>
            {recipientsLoading ? (
              <p className="text-sm text-[color:var(--color-text-secondary)]">Загрузка получателей...</p>
            ) : (
              <div className="space-y-3">
                {recipients.map((recipient) => (
                  <div
                    key={recipient.id}
                    className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-3 flex items-start justify-between gap-3"
                  >
                    <div>
                      <p className="font-medium">{recipient.address}</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">{recipient.type}</p>
                      <p className="text-xs text-[color:var(--color-text-secondary)]">
                        Статус: {recipient.status}
                      </p>
                      {recipient.status !== 'active' && (
                        <p className="text-xs text-yellow-400">Доставка будет подавлена ({recipient.status})</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                          recipient.status === 'active'
                            ? 'bg-[color:var(--color-accent)] text-white'
                            : 'bg-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                        }`}
                        onClick={() =>
                          updateRecipient.mutate({
                            id: recipient.id,
                            data: { status: recipient.status === 'active' ? 'opt-out' : 'active' },
                          })
                        }
                        type="button"
                        disabled={busy}
                      >
                        {recipient.status === 'active' ? 'Вкл' : 'Opt-out'}
                      </button>
                      <button
                        className="p-2 rounded-md hover:bg-white/5"
                        onClick={() => {
                          setEditingRecipient(recipient);
                          setRecipientForm({
                            type: recipient.type,
                            address: recipient.address,
                            status: recipient.status,
                            silence_windows: JSON.stringify(recipient.silence_windows || {}, null, 2),
                          });
                        }}
                        disabled={busy}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 rounded-md hover:bg-white/5 text-red-400"
                        onClick={() => deleteRecipient.mutate(recipient.id)}
                        disabled={busy}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
                {recipients.length === 0 && (
                  <p className="text-sm text-[color:var(--color-text-secondary)]">Получателей нет</p>
                )}
              </div>
            )}
          </div>

          <form
            className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm flex flex-col gap-3"
            onSubmit={handleRecipientSubmit}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">
                {editingRecipient ? 'Редактирование получателя' : 'Новый получатель'}
              </h3>
              {editingRecipient && (
                <button
                  type="button"
                  className="text-sm text-[color:var(--color-accent)]"
                  onClick={() => {
                    setEditingRecipient(null);
                    setRecipientForm(defaultRecipientForm);
                  }}
                >
                  Сброс
                </button>
              )}
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Тип
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={recipientForm.type}
                onChange={(e) => setRecipientForm({ ...recipientForm, type: e.target.value })}
              >
                <option value="email">Email</option>
                <option value="telegram">Telegram</option>
                <option value="webhook">Webhook</option>
                <option value="sms">SMS</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Адрес
              <input
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={recipientForm.address}
                onChange={(e) => setRecipientForm({ ...recipientForm, address: e.target.value })}
                required
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Статус
              <select
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2"
                value={recipientForm.status}
                onChange={(e) => setRecipientForm({ ...recipientForm, status: e.target.value })}
              >
                <option value="active">active</option>
                <option value="opt-out">opt-out</option>
                <option value="blocked">blocked</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Окна тишины (JSON)
              <textarea
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 font-mono text-xs"
                rows={4}
                value={recipientForm.silence_windows}
                onChange={(e) => setRecipientForm({ ...recipientForm, silence_windows: e.target.value })}
              />
            </label>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90"
              disabled={busy}
            >
              {editingRecipient ? 'Сохранить' : 'Создать получателя'}
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
