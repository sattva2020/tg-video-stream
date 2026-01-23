import React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Bell,
  BellOff,
  Edit,
  Trash2,
  Clock,
  Zap,
} from 'lucide-react';
import type { AlertRule } from '../../api/alerts';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Switch';
import { Skeleton } from '../ui/Skeleton';

export interface AlertRuleListProps {
  /** Список правил */
  rules: AlertRule[];
  /** Загрузка */
  isLoading?: boolean;
  /** Callback при переключении enabled */
  onToggleEnabled: (rule: AlertRule, enabled: boolean) => void;
  /** Callback при редактировании */
  onEdit: (rule: AlertRule) => void;
  /** Callback при удалении */
  onDelete: (rule: AlertRule) => void;
  /** Callback при просмотре */
  onView?: (rule: AlertRule) => void;
}

/**
 * Компонент списка правил алертов.
 * Отображает правила в виде таблицы с возможностью управления.
 */
export const AlertRuleList: React.FC<AlertRuleListProps> = ({
  rules,
  isLoading = false,
  onToggleEnabled,
  onEdit,
  onDelete,
  onView,
}) => {
  const safeRules = Array.isArray(rules) ? rules : [];

  // Получение иконки для severity
  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'info':
        return <Info className="w-4 h-4 text-blue-500" />;
      default:
        return <Bell className="w-4 h-4" />;
    }
  };

  // Получение цвета badge для severity
  const getSeverityBadgeVariant = (severity: string): 'default' | 'destructive' | 'outline' => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'destructive';
      case 'warning':
        return 'default';
      default:
        return 'outline';
    }
  };

  // Форматирование даты
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '—';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '—';
    }
  };

  // Скелетон загрузки
  if (isLoading) {
    return (
      <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[color:var(--color-background-secondary)] border-b border-[color:var(--color-border)]">
              <tr>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                  <th key={i} className="px-4 py-3 text-left">
                    <Skeleton className="h-4 w-[100px]" />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i} className="border-b border-[color:var(--color-border)]">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[120px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[150px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[80px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[60px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[80px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[100px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[80px]" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-[80px]" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Пустое состояние
  if (safeRules.length === 0) {
    return (
      <div className="text-center py-12">
        <BellOff className="w-12 h-12 mx-auto text-[color:var(--color-text-secondary)] mb-4" />
        <h3 className="text-lg font-medium mb-2">Нет правил алертов</h3>
        <p className="text-sm text-[color:var(--color-text-secondary)]">
          Создайте первое правило для начала мониторинга
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[color:var(--color-background-secondary)] border-b border-[color:var(--color-border)]">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Название
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Тип
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Важность
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Статус
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Триггеров
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Последнее срабатывание
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Cooldown
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--color-border)]">
            {safeRules.map((rule) => (
              <tr
                key={rule.id}
                className="hover:bg-[color:var(--color-background-secondary)] transition-colors cursor-pointer"
                onClick={() => onView?.(rule)}
              >
                {/* Название */}
                <td className="px-4 py-3">
                  <div>
                    <div className="font-medium text-sm">{rule.name}</div>
                    {rule.description && (
                      <div className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                        {rule.description}
                      </div>
                    )}
                  </div>
                </td>

                {/* Тип */}
                <td className="px-4 py-3">
                  <Badge variant="outline" className="text-xs">
                    {rule.alert_type}
                  </Badge>
                </td>

                {/* Важность */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(rule.severity)}
                    <Badge variant={getSeverityBadgeVariant(rule.severity)} className="text-xs">
                      {rule.severity}
                    </Badge>
                  </div>
                </td>

                {/* Статус */}
                <td className="px-4 py-3">
                  <Switch
                    checked={rule.enabled}
                    onCheckedChange={(checked) => {
                      onToggleEnabled(rule, checked);
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </td>

                {/* Триггеров */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 text-sm">
                    <Zap className="w-3 h-3 text-[color:var(--color-accent)]" />
                    <span>{rule.trigger_count}</span>
                  </div>
                </td>

                {/* Последнее срабатывание */}
                <td className="px-4 py-3 text-sm">
                  <div className="flex items-center gap-1 text-[color:var(--color-text-secondary)]">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(rule.last_triggered_at)}</span>
                  </div>
                </td>

                {/* Cooldown */}
                <td className="px-4 py-3 text-sm text-[color:var(--color-text-secondary)]">
                  {rule.cooldown_sec > 0 ? `${rule.cooldown_sec}с` : '—'}
                </td>

                {/* Действия */}
                <td className="px-4 py-3">
                  <div
                    className="flex items-center justify-end gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(rule)}
                      title="Редактировать"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(rule)}
                      title="Удалить"
                      className="text-red-500 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AlertRuleList;
