import React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Bell,
  BellOff,
  Clock,
  Zap,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  ArrowLeft,
  Calendar,
  Hash,
  Sliders,
  User,
  Timer,
} from 'lucide-react';
import type { AlertRule } from '../../api/alerts';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Switch';

export interface AlertRuleDetailProps {
  /** Правило алерта */
  rule: AlertRule;
  /** Загрузка */
  isLoading?: boolean;
  /** Callback при переключении enabled */
  onToggleEnabled?: (rule: AlertRule, enabled: boolean) => void;
  /** Callback при редактировании */
  onEdit?: (rule: AlertRule) => void;
  /** Callback при удалении */
  onDelete?: (rule: AlertRule) => void;
  /** Callback при возврате к списку */
  onBack?: () => void;
}

/**
 * Компонент детализации правила алерта.
 * Отображает полную информацию о правиле и его настройках.
 */
export const AlertRuleDetail: React.FC<AlertRuleDetailProps> = ({
  rule,
  isLoading = false,
  onToggleEnabled,
  onEdit,
  onDelete,
  onBack,
}) => {
  // Получение иконки для severity
  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />;
      default:
        return <Bell className="w-5 h-5" />;
    }
  };

  // Получение цвета для severity
  const getSeverityColor = (severity: string): string => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'text-red-500';
      case 'warning':
        return 'text-yellow-500';
      case 'info':
        return 'text-blue-500';
      default:
        return 'text-[color:var(--color-text-primary)]';
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
        second: '2-digit',
      });
    } catch {
      return '—';
    }
  };

  // Форматирование булевых значений
  const formatBoolean = (value: boolean) => {
    return value ? (
      <div className="flex items-center gap-1 text-green-500">
        <CheckCircle className="w-4 h-4" />
        <span className="text-sm">Да</span>
      </div>
    ) : (
      <div className="flex items-center gap-1 text-[color:var(--color-text-secondary)]">
        <XCircle className="w-4 h-4" />
        <span className="text-sm">Нет</span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <div className="h-8 w-[200px] bg-[color:var(--color-border)] rounded animate-pulse" />
        </div>
        <div className="rounded-lg border border-[color:var(--color-border)] p-6 space-y-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-20 bg-[color:var(--color-border)] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Заголовок */}
      <div className="mb-6">
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Назад к списку
          </Button>
        )}

        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            {getSeverityIcon(rule.severity)}
            <div>
              <h1 className="text-2xl font-bold">{rule.name}</h1>
              {rule.description && (
                <p className="text-sm text-[color:var(--color-text-secondary)] mt-1">
                  {rule.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onToggleEnabled && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-[color:var(--color-text-secondary)]">
                  {rule.enabled ? 'Включено' : 'Выключено'}
                </span>
                <Switch
                  checked={rule.enabled}
                  onCheckedChange={(checked) => onToggleEnabled(rule, checked)}
                />
              </div>
            )}

            {onEdit && (
              <Button variant="outline" size="sm" onClick={() => onEdit(rule)}>
                <Edit className="w-4 h-4 mr-2" />
                Редактировать
              </Button>
            )}

            {onDelete && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(rule)}
                className="text-red-500 hover:text-red-600 border-red-500/30 hover:bg-red-500/10"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Удалить
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Детали */}
      <div className="space-y-6">
        {/* Основная информация */}
        <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
          <div className="bg-[color:var(--color-background-secondary)] px-6 py-3 border-b border-[color:var(--color-border)]">
            <h2 className="text-sm font-medium uppercase text-[color:var(--color-text-secondary)]">
              Основная информация
            </h2>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <Hash className="w-4 h-4" />
                  ID правила
                </dt>
                <dd className="text-sm font-mono">{rule.id}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <Sliders className="w-4 h-4" />
                  Тип алерта
                </dt>
                <dd>
                  <Badge variant="outline">{rule.alert_type}</Badge>
                </dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Важность
                </dt>
                <dd>
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(rule.severity)}
                    <span className={`font-medium ${getSeverityColor(rule.severity)}`}>
                      {rule.severity}
                    </span>
                  </div>
                </dd>
              </div>

              {rule.category && (
                <div>
                  <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                    Категория
                  </dt>
                  <dd className="text-sm">{rule.category}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        {/* Статистика */}
        <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
          <div className="bg-[color:var(--color-background-secondary)] px-6 py-3 border-b border-[color:var(--color-border)]">
            <h2 className="text-sm font-medium uppercase text-[color:var(--color-text-secondary)]">
              Статистика
            </h2>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Всего срабатываний
                </dt>
                <dd className="text-lg font-semibold">{rule.trigger_count}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Последовательных срабатываний
                </dt>
                <dd className="text-lg font-semibold">{rule.consecutive_triggers}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Последнее срабатывание
                </dt>
                <dd className="text-sm">{formatDate(rule.last_triggered_at)}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Последнее разрешение
                </dt>
                <dd className="text-sm">{formatDate(rule.last_resolved_at)}</dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Настройки */}
        <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
          <div className="bg-[color:var(--color-background-secondary)] px-6 py-3 border-b border-[color:var(--color-border)]">
            <h2 className="text-sm font-medium uppercase text-[color:var(--color-text-secondary)]">
              Настройки
            </h2>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                  <Timer className="w-4 h-4" />
                  Cooldown
                </dt>
                <dd className="text-sm">
                  {rule.cooldown_sec > 0 ? `${rule.cooldown_sec} секунд` : 'Отключен'}
                </dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Rate Limit
                </dt>
                <dd className="text-sm">
                  {rule.rate_limit_minutes && rule.rate_limit_count
                    ? `${rule.rate_limit_count} раз в ${rule.rate_limit_minutes} мин`
                    : 'Не ограничен'}
                </dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Уведомление о восстановлении
                </dt>
                <dd>{formatBoolean(rule.notify_on_recovery)}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Автоматическое разрешение
                </dt>
                <dd>{formatBoolean(rule.auto_resolve)}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Эскалация
                </dt>
                <dd>{formatBoolean(rule.escalation_enabled)}</dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Условия */}
        {Object.keys(rule.conditions).length > 0 && (
          <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
            <div className="bg-[color:var(--color-background-secondary)] px-6 py-3 border-b border-[color:var(--color-border)]">
              <h2 className="text-sm font-medium uppercase text-[color:var(--color-text-secondary)]">
                Условия срабатывания
              </h2>
            </div>
            <div className="p-6">
              <pre className="bg-[color:var(--color-background-secondary)] rounded-lg p-4 text-sm overflow-x-auto">
                {JSON.stringify(rule.conditions, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Метаданные */}
        <div className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
          <div className="bg-[color:var(--color-background-secondary)] px-6 py-3 border-b border-[color:var(--color-border)]">
            <h2 className="text-sm font-medium uppercase text-[color:var(--color-text-secondary)]">
              <Calendar className="w-4 h-4 inline mr-2" />
              Метаданные
            </h2>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Создано
                </dt>
                <dd className="text-sm">{formatDate(rule.created_at)}</dd>
              </div>

              <div>
                <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1">
                  Обновлено
                </dt>
                <dd className="text-sm">{formatDate(rule.updated_at)}</dd>
              </div>

              {rule.created_by && (
                <div>
                  <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Создал
                  </dt>
                  <dd className="text-sm font-mono">{rule.created_by}</dd>
                </div>
              )}

              {rule.updated_by && (
                <div>
                  <dt className="text-sm text-[color:var(--color-text-secondary)] mb-1 flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Обновил
                  </dt>
                  <dd className="text-sm font-mono">{rule.updated_by}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertRuleDetail;
