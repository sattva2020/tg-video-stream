import React, { useState, useMemo } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  RefreshCcw,
  Filter,
  Clock,
  CheckCircle,
  XCircle,
  MoreHorizontal,
} from 'lucide-react';
import type { AlertInstance } from '../../api/alerts';
import { useAlertInstances } from '../../hooks/useAlerts';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';

export interface AlertHistoryProps {
  /** ID правила для фильтрации */
  ruleId?: string;
  /** ID группы для фильтрации */
  groupId?: string;
  /** Максимальное количество записей */
  limit?: number;
  /** Показывать фильтры */
  showFilters?: boolean;
}

/**
 * Компонент истории алертов.
 * Отображает историю срабатываний алертов с фильтрацией.
 */
export const AlertHistory: React.FC<AlertHistoryProps> = ({
  ruleId,
  groupId,
  limit = 50,
  showFilters = true,
}) => {
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState('');

  const filters = useMemo(
    () => ({
      rule_id: ruleId,
      group_id: groupId,
      status: statusFilter.length ? statusFilter.join(',') : undefined,
      severity: severityFilter.length ? severityFilter.join(',') : undefined,
      alert_type: typeFilter || undefined,
      limit,
    }),
    [ruleId, groupId, statusFilter, severityFilter, typeFilter, limit]
  );

  const { data: instances = [], isLoading, refetch } = useAlertInstances(filters);

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
        return <AlertCircle className="w-4 h-4" />;
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

  // Получение цвета badge для status
  const getStatusBadgeVariant = (status: string): 'default' | 'destructive' | 'outline' => {
    switch (status.toLowerCase()) {
      case 'fired':
        return 'destructive';
      case 'resolved':
        return 'default';
      case 'acknowledged':
        return 'outline';
      default:
        return 'outline';
    }
  };

  // Получение иконки для status
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'fired':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'acknowledged':
        return <MoreHorizontal className="w-4 h-4 text-yellow-500" />;
      default:
        return <MoreHorizontal className="w-4 h-4" />;
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

  // Форматирование длительности
  const formatDuration = (durationSec: number | null | undefined) => {
    if (!durationSec) return '—';
    if (durationSec < 60) return `${durationSec}с`;
    const minutes = Math.floor(durationSec / 60);
    const seconds = durationSec % 60;
    return `${minutes}м ${seconds}с`;
  };

  const handleStatusToggle = (value: string) => {
    setStatusFilter((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const handleSeverityToggle = (value: string) => {
    setSeverityFilter((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  return (
    <div className="space-y-4">
      {/* Фильтры */}
      {showFilters && (
        <div className="rounded-lg border border-[color:var(--color-border)] p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-secondary)]">
              <Filter className="w-4 h-4" /> Фильтры
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
            >
              <RefreshCcw className="w-4 h-4 mr-2" /> Обновить
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Фильтр по статусу */}
            <div>
              <label className="block text-sm font-medium mb-2">Статус</label>
              <div className="flex flex-wrap gap-2">
                {['fired', 'resolved', 'acknowledged'].map((value) => (
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
            </div>

            {/* Фильтр по важности */}
            <div>
              <label className="block text-sm font-medium mb-2">Важность</label>
              <div className="flex flex-wrap gap-2">
                {['critical', 'warning', 'info'].map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => handleSeverityToggle(value)}
                    className={`rounded-full px-3 py-1 text-xs border transition ${
                      severityFilter.includes(value)
                        ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10'
                        : 'border-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                    }`}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>

            {/* Фильтр по типу */}
            <div>
              <label className="block text-sm font-medium mb-2">Тип алерта</label>
              <input
                type="text"
                className="w-full rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                placeholder="stream_failure, viewer_count..."
              />
            </div>
          </div>
        </div>
      )}

      {/* Таблица истории */}
      <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[color:var(--color-background-secondary)] border-b border-[color:var(--color-border)]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                  Время срабатывания
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
                  Значение
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                  Длительность
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-[color:var(--color-text-secondary)]">
                  Уведомление
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--color-border)]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[140px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[100px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[60px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[60px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[80px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[60px]" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-[40px]" /></td>
                  </tr>
                ))
              ) : instances.length > 0 ? (
                instances.map((instance) => (
                  <tr
                    key={instance.id}
                    className="hover:bg-[color:var(--color-background-secondary)] transition-colors"
                  >
                    {/* Время срабатывания */}
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-1 text-[color:var(--color-text-secondary)]">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(instance.fired_at)}</span>
                      </div>
                    </td>

                    {/* Тип */}
                    <td className="px-4 py-3">
                      <Badge variant="outline" className="text-xs">
                        {instance.alert_type}
                      </Badge>
                    </td>

                    {/* Важность */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getSeverityIcon(instance.severity)}
                        <Badge variant={getSeverityBadgeVariant(instance.severity)} className="text-xs">
                          {instance.severity}
                        </Badge>
                      </div>
                    </td>

                    {/* Статус */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(instance.status)}
                        <Badge variant={getStatusBadgeVariant(instance.status)} className="text-xs">
                          {instance.status}
                        </Badge>
                      </div>
                    </td>

                    {/* Значение */}
                    <td className="px-4 py-3 text-sm">
                      {instance.trigger_value ? (
                        <code className="text-xs bg-[color:var(--color-background-secondary)] px-2 py-1 rounded">
                          {JSON.stringify(instance.trigger_value)}
                        </code>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Длительность */}
                    <td className="px-4 py-3 text-sm text-[color:var(--color-text-secondary)]">
                      {formatDuration(instance.duration_sec)}
                    </td>

                    {/* Уведомление */}
                    <td className="px-4 py-3">
                      {instance.notification_sent ? (
                        <Badge variant="outline" className="text-xs text-green-500 border-green-500">
                          Отправлено
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs text-[color:var(--color-text-secondary)]">
                          Не отправлено
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-[color:var(--color-text-secondary)]">
                    <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>История алертов пуста</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Информация о количестве */}
      <div className="text-sm text-[color:var(--color-text-secondary)]">
        Показано {instances.length} записей
      </div>
    </div>
  );
};

export default AlertHistory;
