import React from 'react';
import { ArrowUp, ArrowDown, Trash2, Plus, Users, Radio, Clock } from 'lucide-react';
import type { RuleFormState } from './types';
import type { NotificationChannel, NotificationRecipient, NotificationTemplate } from '../../../api/notifications';

interface StepDeliveryProps {
  form: RuleFormState;
  onChange: (updates: Partial<RuleFormState>) => void;
  disabled?: boolean;
  /** Доступные каналы */
  channels: NotificationChannel[];
  /** Доступные получатели */
  recipients: NotificationRecipient[];
  /** Доступные шаблоны */
  templates: NotificationTemplate[];
}

/**
 * Шаг 3: Настройка доставки.
 * - Получатели
 * - Порядок каналов (эскалация)
 * - Шаблон
 * - Таймаут failover
 */
export const StepDelivery: React.FC<StepDeliveryProps> = ({
  form,
  onChange,
  disabled = false,
  channels,
  recipients,
  templates,
}) => {
  const [channelToAdd, setChannelToAdd] = React.useState('');

  // Доступные каналы (не добавленные в порядок)
  const availableChannels = channels.filter((c) => !form.channelIds.includes(c.id));

  // Хелперы для работы с порядком каналов
  const addChannel = () => {
    if (!channelToAdd) return;
    if (form.channelIds.includes(channelToAdd)) return;
    onChange({ channelIds: [...form.channelIds, channelToAdd] });
    setChannelToAdd('');
  };

  const removeChannel = (index: number) => {
    const next = [...form.channelIds];
    next.splice(index, 1);
    onChange({ channelIds: next });
  };

  const moveChannel = (index: number, direction: -1 | 1) => {
    const next = [...form.channelIds];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= next.length) return;
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    onChange({ channelIds: next });
  };

  const toggleRecipient = (recipientId: string) => {
    const current = form.recipientIds;
    if (current.includes(recipientId)) {
      onChange({ recipientIds: current.filter((id: string) => id !== recipientId) });
    } else {
      onChange({ recipientIds: [...current, recipientId] });
    }
  };

  // Группировка получателей по типу
  const recipientsByType = recipients.reduce((acc, r) => {
    if (!acc[r.type]) acc[r.type] = [];
    acc[r.type].push(r);
    return acc;
  }, {} as Record<string, NotificationRecipient[]>);

  const typeLabels: Record<string, string> = {
    email: '📧 Email',
    telegram: '📱 Telegram',
    slack: '💬 Slack',
    webhook: '🔗 Webhook',
  };

  return (
    <div className="space-y-6">
      {/* Получатели */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-[color:var(--color-accent)]" />
          <span className="font-medium">Получатели</span>
          <span className="text-xs text-[color:var(--color-text-secondary)]">
            ({form.recipientIds.length} выбрано)
          </span>
        </div>

        <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4 space-y-4">
          {Object.entries(recipientsByType).map(([type, typeRecipients]) => (
            <div key={type}>
              <div className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-2">
                {typeLabels[type] || type}
              </div>
              <div className="flex flex-wrap gap-2">
                {typeRecipients.map((recipient) => {
                  const isSelected = form.recipientIds.includes(recipient.id);
                  const isDisabled = recipient.status === 'blocked' || recipient.status === 'opt-out';
                  
                  return (
                    <button
                      key={recipient.id}
                      type="button"
                      onClick={() => toggleRecipient(recipient.id)}
                      disabled={disabled || isDisabled}
                      className={`
                        inline-flex items-center gap-2 px-3 py-2 rounded-lg border-2 text-sm
                        transition-all duration-150
                        ${isSelected
                          ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10 text-[color:var(--color-accent)]'
                          : 'border-[color:var(--color-border)] bg-transparent hover:border-[color:var(--color-accent)]/50'
                        }
                        ${isDisabled ? 'opacity-50 cursor-not-allowed line-through' : 'cursor-pointer'}
                      `}
                    >
                      {recipient.address}
                      {isDisabled && (
                        <span className="text-xs text-red-400">({recipient.status})</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {recipients.length === 0 && (
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Нет доступных получателей. Добавьте их на вкладке «Получатели».
            </p>
          )}
        </div>
      </div>

      {/* Порядок каналов (эскалация) */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Radio className="w-5 h-5 text-[color:var(--color-accent)]" />
          <span className="font-medium">Порядок каналов</span>
        </div>

        <p className="text-sm text-[color:var(--color-text-secondary)]">
          Уведомления отправляются по порядку. При неудаче — переход к следующему каналу (failover).
        </p>

        <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4 space-y-3">
          {/* Добавление канала */}
          <div className="flex items-center gap-2">
            <select
              value={channelToAdd}
              onChange={(e) => setChannelToAdd(e.target.value)}
              disabled={disabled || availableChannels.length === 0}
              className="flex-1 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2 text-sm"
            >
              <option value="">Выберите канал...</option>
              {availableChannels.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  {channel.name} ({channel.type})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={addChannel}
              disabled={disabled || !channelToAdd}
              className="inline-flex items-center gap-1 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              Добавить
            </button>
          </div>

          {/* Список каналов с drag-n-drop (кнопками) */}
          <div className="space-y-2">
            {form.channelIds.map((id: string, idx: number) => {
              const channel = channels.find((c) => c.id === id);
              return (
                <div
                  key={id}
                  className="flex items-center justify-between rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-[color:var(--color-accent)] text-white text-xs flex items-center justify-center font-bold">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="font-medium">{channel?.name || 'Неизвестный канал'}</div>
                      <div className="text-xs text-[color:var(--color-text-secondary)]">
                        {channel?.type || id}
                        {!channel?.enabled && ' • Отключен'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => moveChannel(idx, -1)}
                      disabled={disabled || idx === 0}
                      className="p-2 rounded hover:bg-white/5 disabled:opacity-30"
                      aria-label="Переместить вверх"
                    >
                      <ArrowUp className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => moveChannel(idx, 1)}
                      disabled={disabled || idx === form.channelIds.length - 1}
                      className="p-2 rounded hover:bg-white/5 disabled:opacity-30"
                      aria-label="Переместить вниз"
                    >
                      <ArrowDown className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => removeChannel(idx)}
                      disabled={disabled}
                      className="p-2 rounded hover:bg-white/5 text-red-400"
                      aria-label="Удалить"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}

            {form.channelIds.length === 0 && (
              <p className="text-sm text-[color:var(--color-text-secondary)] text-center py-4">
                Добавьте хотя бы один канал для доставки уведомлений
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Шаблон и Failover */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Шаблон */}
        <div className="space-y-2">
          <label className="block text-sm font-medium">Шаблон сообщения</label>
          <select
            value={form.templateId}
            onChange={(e) => onChange({ templateId: e.target.value })}
            disabled={disabled}
            className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm"
          >
            <option value="">Без шаблона (стандартный формат)</option>
            {templates.map((tpl) => (
              <option key={tpl.id} value={tpl.id}>
                {tpl.name} ({tpl.locale})
              </option>
            ))}
          </select>
        </div>

        {/* Таймаут failover */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <Clock className="w-4 h-4" />
            Таймаут failover
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={0}
              max={3600}
              value={form.failoverTimeoutSec}
              onChange={(e) => onChange({ failoverTimeoutSec: Number(e.target.value) })}
              disabled={disabled}
              className="w-24 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm text-center"
            />
            <span className="text-sm text-[color:var(--color-text-secondary)]">секунд</span>
          </div>
          <p className="text-xs text-[color:var(--color-text-secondary)]">
            Время ожидания перед переходом к следующему каналу
          </p>
        </div>
      </div>

      {/* Валидация */}
      {form.recipientIds.length === 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">
            ⚠️ Выберите хотя бы одного получателя
          </p>
        </div>
      )}

      {form.channelIds.length === 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">
            ⚠️ Добавьте хотя бы один канал доставки
          </p>
        </div>
      )}
    </div>
  );
};

export default StepDelivery;
