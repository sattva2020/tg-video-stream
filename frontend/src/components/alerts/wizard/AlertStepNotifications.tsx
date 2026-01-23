import React from 'react';
import { ArrowUp, ArrowDown, Trash2, Plus, Bell, Clock, CheckCircle, XCircle, Zap } from 'lucide-react';
import type { AlertRuleFormState } from './types';
import type { NotificationChannel } from '../../../api/notifications';

interface AlertStepNotificationsProps {
  form: AlertRuleFormState;
  onChange: (updates: Partial<AlertRuleFormState>) => void;
  disabled?: boolean;
  /** Доступные каналы */
  channels: NotificationChannel[];
}

/**
 * Шаг 3: Настройка уведомлений.
 * - Каналы уведомлений
 * - Уведомление о восстановлении
 * - Автоматическое разрешение
 * - Эскалация
 */
export const AlertStepNotifications: React.FC<AlertStepNotificationsProps> = ({
  form,
  onChange,
  disabled = false,
  channels,
}) => {
  const [channelToAdd, setChannelToAdd] = React.useState('');

  // Доступные каналы (не добавленные в список)
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

  // Иконки для типов каналов
  const getChannelIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'email':
        return '📧';
      case 'telegram':
        return '📱';
      case 'slack':
        return '💬';
      case 'webhook':
        return '🔗';
      default:
        return '📢';
    }
  };

  return (
    <div className="space-y-6">
      {/* Каналы уведомлений */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-[color:var(--color-accent)]" />
          <span className="font-medium">Каналы уведомлений</span>
          <span className="text-xs text-[color:var(--color-text-secondary)]">
            ({form.channelIds.length} выбрано)
          </span>
        </div>

        <p className="text-sm text-[color:var(--color-text-secondary)]">
          Выберите каналы для отправки уведомлений. Уведомления будут отправлены во все выбранные каналы.
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
                  {getChannelIcon(channel.type)} {channel.name} ({channel.type})
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

          {/* Список выбранных каналов */}
          <div className="space-y-2">
            {form.channelIds.map((id: string, idx: number) => {
              const channel = channels.find((c) => c.id === id);
              return (
                <div
                  key={id}
                  className="flex items-center justify-between rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">
                      {getChannelIcon(channel?.type || '')}
                    </span>
                    <div>
                      <div className="font-medium">{channel?.name || 'Неизвестный канал'}</div>
                      <div className="text-xs text-[color:var(--color-text-secondary)]">
                        {channel?.type || id}
                        {!channel?.enabled && ' • Отключен'}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeChannel(idx)}
                    disabled={disabled}
                    className="p-2 rounded hover:bg-white/5 text-red-400 disabled:opacity-50"
                    aria-label="Удалить"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}

            {form.channelIds.length === 0 && (
              <p className="text-sm text-[color:var(--color-text-secondary)] text-center py-4">
                Добавьте хотя бы один канал для получения уведомлений
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Настройки уведомлений */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-[color:var(--color-accent)]" />
          <span className="font-medium">Настройки уведомлений</span>
        </div>

        <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4 space-y-4">
          {/* Уведомление о восстановлении */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.notify_on_recovery}
              onChange={(e) => onChange({ notify_on_recovery: e.target.checked })}
              disabled={disabled}
              className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <span className="font-medium">Уведомлять о восстановлении</span>
              </div>
              <p className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                Отправить уведомление когда проблема будет решена
              </p>
            </div>
          </label>

          {/* Автоматическое разрешение */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.auto_resolve}
              onChange={(e) => onChange({ auto_resolve: e.target.checked })}
              disabled={disabled}
              className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-500" />
                <span className="font-medium">Автоматически разрешать</span>
              </div>
              <p className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                Автоматически закрывать алерт когда условие больше не выполняется
              </p>
            </div>
          </label>

          {/* Эскалация */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.escalation_enabled}
              onChange={(e) => onChange({ escalation_enabled: e.target.checked })}
              disabled={disabled}
              className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <ArrowUp className="w-4 h-4 text-orange-500" />
                <span className="font-medium">Включить эскалацию</span>
              </div>
              <p className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                Повышать важность и расширенные уведомления при длительном алерте
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Валидация */}
      {form.channelIds.length === 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">
            ⚠️ Выберите хотя бы один канал уведомлений
          </p>
        </div>
      )}

      {/* Информация о настройке */}
      {form.channelIds.length > 0 && (
        <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
          <p className="text-sm text-blue-300">
            💡 Настройка завершена! Алерт будет отправлен на {form.channelIds.length} канал(ов).
            {form.auto_resolve && ' Алерт будет автоматически закрываться при восстановлении.'}
            {form.notify_on_recovery && ' Вы получите уведомление когда проблема будет решена.'}
          </p>
        </div>
      )}
    </div>
  );
};

export default AlertStepNotifications;
