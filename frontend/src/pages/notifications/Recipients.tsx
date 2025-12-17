import React, { useState } from 'react';
import { ResponsiveHeader } from '../../components/layout';
import { NotificationsNav } from '../../components/notifications/NotificationsNav';
import {
  useNotificationRecipients,
  useCreateNotificationRecipient,
  useUpdateNotificationRecipient,
  useDeleteNotificationRecipient,
} from '../../hooks/useNotifications';
import type { NotificationRecipient } from '../../api/notifications';
import { Plus, Trash2, Edit2 } from 'lucide-react';

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

const NotificationRecipientsPage: React.FC = () => {
  const { data: recipients = [], isLoading: recipientsLoading } = useNotificationRecipients();

  const createRecipient = useCreateNotificationRecipient();
  const updateRecipient = useUpdateNotificationRecipient();
  const deleteRecipient = useDeleteNotificationRecipient();

  const [recipientForm, setRecipientForm] = useState(defaultRecipientForm);
  const [editingRecipient, setEditingRecipient] = useState<NotificationRecipient | null>(null);

  const busy =
    recipientsLoading ||
    createRecipient.isPending ||
    updateRecipient.isPending ||
    deleteRecipient.isPending;

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

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <ResponsiveHeader />
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <NotificationsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Получатели уведомлений</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Управление списком адресатов (email, telegram, webhook).
          </p>
        </div>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Список получателей</h2>
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
      </div>
    </div>
  );
};

export default NotificationRecipientsPage;
