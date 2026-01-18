import React, { useState } from 'react';
import { AppLayout } from '../../components/layout';
import { NotificationsNav } from '../../components/notifications/NotificationsNav';
import {
  useNotificationTemplates,
  useCreateNotificationTemplate,
  useUpdateNotificationTemplate,
  useDeleteNotificationTemplate,
} from '../../hooks/useNotifications';
import type { NotificationTemplate } from '../../api/notifications';
import { Plus, Trash2, Edit2 } from 'lucide-react';

const defaultTemplateForm = {
  name: '',
  locale: 'en',
  subject: '',
  body: '',
  variables: '{}',
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

const NotificationTemplatesPage: React.FC = () => {
  const { data: templates = [], isLoading: templatesLoading } = useNotificationTemplates();

  const createTemplate = useCreateNotificationTemplate();
  const updateTemplate = useUpdateNotificationTemplate();
  const deleteTemplate = useDeleteNotificationTemplate();

  const [templateForm, setTemplateForm] = useState(defaultTemplateForm);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null);

  const busy =
    templatesLoading ||
    createTemplate.isPending ||
    updateTemplate.isPending ||
    deleteTemplate.isPending;

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

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <NotificationsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Шаблоны уведомлений</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Настройка внешнего вида уведомлений для разных каналов и языков.
          </p>
        </div>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Список шаблонов</h2>
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
      </div>
    </AppLayout>
  );
};

export default NotificationTemplatesPage;
