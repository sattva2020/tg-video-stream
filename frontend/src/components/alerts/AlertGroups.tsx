import React, { useState, useMemo } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  RefreshCcw,
  Filter,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  Layers,
  Clock,
  UserCheck,
  MoreHorizontal,
} from 'lucide-react';
import type { AlertGroup, AlertInstance } from '../../api/alerts';
import { useAlertGroups, useResolveAlertGroup, useAlertGroup } from '../../hooks/useAlerts';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';
import { useToast } from '../../hooks/useToast';

export interface AlertGroupsProps {
  /** ID правила для фильтрации */
  ruleId?: string;
  /** Максимальное количество записей */
  limit?: number;
  /** Показывать фильтры */
  showFilters?: boolean;
}

/**
 * Компонент групп алертов.
 * Отображает группы алертов с возможностью раскрытия деталей.
 */
export const AlertGroups: React.FC<AlertGroupsProps> = ({
  ruleId,
  limit = 50,
  showFilters = true,
}) => {
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const filters = useMemo(
    () => ({
      rule_id: ruleId,
      status: statusFilter.length ? statusFilter.join(',') : undefined,
      severity: severityFilter.length ? severityFilter.join(',') : undefined,
      limit,
    }),
    [ruleId, statusFilter, severityFilter, limit]
  );

  const { data: groups = [], isLoading, refetch } = useAlertGroups(filters);
  const resolveGroup = useResolveAlertGroup();

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
      case 'active':
        return 'destructive';
      case 'resolved':
        return 'default';
      case 'suppressed':
        return 'outline';
      default:
        return 'outline';
    }
  };

  // Получение иконки для status
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'suppressed':
        return <MoreHorizontal className="w-4 h-4 text-gray-500" />;
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

  // Раскрытие/скрытие группы
  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Разрешение группы
  const handleResolveGroup = async (groupId: string) => {
    try {
      await resolveGroup.mutateAsync({
        id: groupId,
        request: { resolved: true },
      });
      toast.success('Группа разрешена');
    } catch (error) {
      // Error уже обработан в хуке
    }
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

  // Компонент деталей группы
  const GroupDetails: React.FC<{ group: AlertGroup }> = ({ group }) => {
    const { data: groupDetail, isLoading: isLoadingDetail } = useAlertGroup(group.id);

    if (isLoadingDetail) {
      return (
        <div className="px-4 py-3 border-t border-[color:var(--color-border)]">
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    if (!groupDetail || !groupDetail.instances || groupDetail.instances.length === 0) {
      return (
        <div className="px-4 py-3 border-t border-[color:var(--color-border)] text-sm text-[color:var(--color-text-secondary)]">
          Нет алертов в группе
        </div>
      );
    }

    return (
      <div className="px-4 py-3 border-t border-[color:var(--color-border)] bg-[color:var(--color-background-secondary)]">
        <div className="space-y-2">
          {groupDetail.instances.map((instance) => (
            <div
              key={instance.id}
              className="flex items-center gap-3 text-sm p-2 rounded bg-[color:var(--color-surface-muted)]"
            >
              <Clock className="w-3 h-3 text-[color:var(--color-text-secondary)] flex-shrink-0" />
              <span className="text-[color:var(--color-text-secondary)] text-xs">
                {formatDate(instance.fired_at)}
              </span>
              <Badge variant="outline" className="text-xs flex-shrink-0">
                {instance.alert_type}
              </Badge>
              {instance.trigger_value && (
                <code className="text-xs bg-[color:var(--color-background-secondary)] px-2 py-0.5 rounded">
                  {JSON.stringify(instance.trigger_value)}
                </code>
              )}
              {instance.resolved_at && (
                <Badge variant="outline" className="text-xs text-green-500 border-green-500 ml-auto">
                  Разрешен
                </Badge>
              )}
            </div>
          ))}
        </div>
      </div>
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Фильтр по статусу */}
            <div>
              <label className="block text-sm font-medium mb-2">Статус</label>
              <div className="flex flex-wrap gap-2">
                {['active', 'resolved', 'suppressed'].map((value) => (
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
          </div>
        </div>
      )}

      {/* Список групп */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-[color:var(--color-border)] p-4">
              <Skeleton className="h-6 w-[200px] mb-2" />
              <Skeleton className="h-4 w-[300px]" />
            </div>
          ))
        ) : groups.length > 0 ? (
          groups.map((group) => {
            const isExpanded = expandedGroups.has(group.id);
            return (
              <div
                key={group.id}
                className="rounded-lg border border-[color:var(--color-border)] overflow-hidden"
              >
                {/* Заголовок группы */}
                <div
                  className="p-4 cursor-pointer hover:bg-[color:var(--color-background-secondary)] transition-colors"
                  onClick={() => toggleGroup(group.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      {/* Кнопка раскрытия */}
                      <button
                        className="flex-shrink-0 mt-1 text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)]"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleGroup(group.id);
                        }}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>

                      {/* Информация о группе */}
                      <div className="flex-1 min-w-0 space-y-2">
                        {/* Название и ключ */}
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-[color:var(--color-text-secondary)] flex-shrink-0" />
                          <span className="font-medium text-sm truncate">
                            {group.name || group.group_key}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {group.alert_count} {group.alert_count === 1 ? 'алерт' : 'алертов'}
                          </Badge>
                        </div>

                        {/* Метаданные */}
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[color:var(--color-text-secondary)]">
                          {/* Важность */}
                          <div className="flex items-center gap-1">
                            {getSeverityIcon(group.severity)}
                            <span>{group.severity}</span>
                          </div>

                          {/* Статус */}
                          <div className="flex items-center gap-1">
                            {getStatusIcon(group.status)}
                            <span>{group.status}</span>
                          </div>

                          {/* Первый алерт */}
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>с {formatDate(group.first_alert_at)}</span>
                          </div>

                          {/* Последний алерт */}
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>до {formatDate(group.last_alert_at)}</span>
                          </div>

                          {/* Уведомления */}
                          {group.notification_count > 0 && (
                            <div className="flex items-center gap-1">
                              <span>уведомлений: {group.notification_count}</span>
                            </div>
                          )}

                          {/* Разрешен */}
                          {group.resolved_at && (
                            <div className="flex items-center gap-1">
                              <UserCheck className="w-3 h-3 text-green-500" />
                              <span>разрешен {formatDate(group.resolved_at)}</span>
                              {group.resolved_by && (
                                <span>(by {group.resolved_by})</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Действия */}
                    <div className="flex-shrink-0">
                      {group.status === 'active' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolveGroup(group.id);
                          }}
                          disabled={resolveGroup.isPending}
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Разрешить
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Детали группы (раскрытое состояние) */}
                {isExpanded && <GroupDetails group={group} />}
              </div>
            );
          })
        ) : (
          <div className="text-center py-12 rounded-lg border border-[color:var(--color-border)]">
            <Layers className="w-12 h-12 mx-auto text-[color:var(--color-text-secondary)] mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">Нет групп алертов</h3>
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Группы алертов формируются при срабатывании правил
            </p>
          </div>
        )}
      </div>

      {/* Информация о количестве */}
      <div className="text-sm text-[color:var(--color-text-secondary)]">
        Показано {groups.length} {groups.length === 1 ? 'группа' : 'групп'}
      </div>
    </div>
  );
};

export default AlertGroups;
