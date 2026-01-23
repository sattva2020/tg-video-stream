/**
 * ABTestList Component
 * Feature: 016-a-b-testing-framework-for-content
 *
 * Список A/B тестов с карточками, отображающими статус и метрики.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  FlaskConical,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  TrendingUp,
  Award,
  Calendar,
  Trash2,
  Eye,
} from 'lucide-react';
import * as abTestingApi from '../../api/ab_testing';
import type { ABTestStatus, ABTestListResponse } from '../../types/ab_testing';

export interface ABTestListProps {
  /** Фильтр по ID канала */
  channelId?: string;
  /** Фильтр по статусу */
  status?: ABTestStatus;
  /** Количество тестов на странице (1-100) */
  limit?: number;
  /** Автообновление (мс) */
  refreshInterval?: number;
  /** Обработчик клика по тесту */
  onTestClick?: (testId: string) => void;
  /** Обработчик запуска теста */
  onStartTest?: (testId: string) => void;
  /** Обработчик остановки теста */
  onStopTest?: (testId: string) => void;
  /** Обработчик удаления теста */
  onDeleteTest?: (testId: string) => void;
}

const statusConfig: Record<
  ABTestStatus,
  {
    label: string;
    icon: typeof FlaskConical;
    color: string;
    bg: string;
    border: string;
  }
> = {
  draft: {
    label: 'Черновик',
    icon: Clock,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
  },
  running: {
    label: 'Запущен',
    icon: Play,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
  paused: {
    label: 'Приостановлен',
    icon: Pause,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
  },
  completed: {
    label: 'Завершён',
    icon: CheckCircle,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
  },
  stopped: {
    label: 'Остановлен',
    icon: XCircle,
    color: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/20',
  },
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return 'Сегодня';
  } else if (diffDays === 1) {
    return 'Вчера';
  } else if (diffDays < 7) {
    return `${diffDays} дн. назад`;
  } else {
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  }
};

const formatDuration = (startTime: string, endTime?: string): string => {
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days} дн.`;
  } else if (hours > 0) {
    return `${hours} ч.`;
  } else {
    const minutes = Math.floor(diffMs / (1000 * 60));
    return `${minutes} мин.`;
  }
};

export const ABTestList: React.FC<ABTestListProps> = ({
  channelId,
  status,
  limit = 50,
  refreshInterval,
  onTestClick,
  onStartTest,
  onStopTest,
  onDeleteTest,
}) => {
  const [tests, setTests] = useState<ABTestListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const fetchTests = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await abTestingApi.listABTests(channelId, status, limit, 0);
      setTests(response.tests);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch A/B tests:', err);
      setError('Не удалось загрузить список A/B тестов');
    } finally {
      setLoading(false);
    }
  }, [channelId, status, limit]);

  useEffect(() => {
    fetchTests();

    if (refreshInterval) {
      const interval = setInterval(fetchTests, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchTests, refreshInterval]);

  const handleStart = async (testId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await abTestingApi.startABTest(testId);
      fetchTests();
      onStartTest?.(testId);
    } catch (err) {
      console.error('Failed to start test:', err);
    }
  };

  const handleStop = async (testId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await abTestingApi.stopABTest(testId, true);
      fetchTests();
      onStopTest?.(testId);
    } catch (err) {
      console.error('Failed to stop test:', err);
    }
  };

  const handleDelete = async (testId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Вы уверены, что хотите удалить этот тест?')) {
      return;
    }
    try {
      await abTestingApi.deleteABTest(testId);
      fetchTests();
      onDeleteTest?.(testId);
    } catch (err) {
      console.error('Failed to delete test:', err);
    }
  };

  const getStatusInfo = (testStatus: ABTestStatus) => statusConfig[testStatus];

  return (
    <div className="space-y-4">
      {/* Header with total count */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-[color:var(--color-text-muted)]" />
          <h2 className="text-lg font-semibold text-[color:var(--color-text)]">
            A/B Тесты
          </h2>
          {total > 0 && (
            <span className="text-sm text-[color:var(--color-text-muted)]">
              ({total})
            </span>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-2xl p-4 bg-red-500/10 border border-red-500/20 text-red-300"
        >
          {error}
        </motion.div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-2xl p-6 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] animate-pulse"
            >
              <div className="h-6 w-3/4 bg-[color:var(--color-border)] rounded mb-4" />
              <div className="h-4 w-1/2 bg-[color:var(--color-border)] rounded mb-2" />
              <div className="h-4 w-1/3 bg-[color:var(--color-border)] rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && tests.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-2xl p-12 text-center bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]"
        >
          <FlaskConical className="w-16 h-16 mx-auto text-[color:var(--color-text-muted)] mb-4" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-2">
            Нет A/B тестов
          </h3>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            Создайте первый A/B тест, чтобы начать эксперимент
          </p>
        </motion.div>
      )}

      {/* Test Cards */}
      {!loading && tests.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tests.map((test, index) => {
            const statusInfo = getStatusInfo(test.status);
            const StatusIcon = statusInfo.icon;

            return (
              <motion.div
                key={test.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`
                  relative overflow-hidden rounded-2xl p-6 cursor-pointer
                  bg-[color:var(--color-panel)]
                  border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
                  shadow-md shadow-black/5
                  hover:shadow-lg hover:shadow-black/10 hover:border-[color:var(--color-accent)]/30
                  transition-all duration-300
                `}
                onClick={() => onTestClick?.(test.id)}
              >
                {/* Status Badge */}
                <div className="flex items-center justify-between mb-4">
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${statusInfo.bg} ${statusInfo.border} border`}>
                    <StatusIcon className={`w-4 h-4 ${statusInfo.color}`} />
                    <span className={`text-xs font-medium ${statusInfo.color}`}>
                      {statusInfo.label}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {test.status === 'draft' && onStartTest && (
                      <button
                        onClick={(e) => handleStart(test.id, e)}
                        className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-emerald-600 hover:text-emerald-700 transition-colors"
                        title="Запустить тест"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    {test.status === 'running' && onStopTest && (
                      <button
                        onClick={(e) => handleStop(test.id, e)}
                        className="p-1.5 rounded-lg hover:bg-amber-500/10 text-amber-600 hover:text-amber-700 transition-colors"
                        title="Остановить тест"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    )}
                    {onDeleteTest && (
                      <button
                        onClick={(e) => handleDelete(test.id, e)}
                        className="p-1.5 rounded-lg hover:bg-rose-500/10 text-rose-600 hover:text-rose-700 transition-colors"
                        title="Удалить тест"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Test Name */}
                <h3 className="text-base font-semibold text-[color:var(--color-text)] mb-2 line-clamp-2">
                  {test.name}
                </h3>

                {/* Test Info */}
                <div className="space-y-2 text-xs text-[color:var(--color-text-muted)]">
                  {/* Variants Count */}
                  <div className="flex items-center gap-2">
                    <Users className="w-3.5 h-3.5" />
                    <span>{test.variant_count} вариант(ов)</span>
                  </div>

                  {/* Created Date */}
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Создан: {formatDate(test.created_at)}</span>
                  </div>

                  {/* Duration */}
                  {test.start_time && (
                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5" />
                      <span>
                        {test.status === 'running'
                          ? `Длится: ${formatDuration(test.start_time)}`
                          : test.end_time
                            ? `Длина: ${formatDuration(test.start_time, test.end_time)}`
                            : 'Запланирован'}
                      </span>
                    </div>
                  )}

                  {/* Significance Badge */}
                  {test.is_significant !== undefined && (
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-3.5 h-3.5" />
                      <span>
                        {test.is_significant ? (
                          <span className="text-emerald-600">Статистически значимый</span>
                        ) : (
                          <span className="text-amber-600">Требуется больше данных</span>
                        )}
                      </span>
                    </div>
                  )}

                  {/* Winner Badge */}
                  {test.winner_variant_id && (
                    <div className="flex items-center gap-2">
                      <Award className="w-3.5 h-3.5 text-blue-600" />
                      <span className="text-blue-600">Победитель определён</span>
                    </div>
                  )}
                </div>

                {/* View Details Hint */}
                <div className="mt-4 pt-4 border-t border-[color:var(--color-border)] flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                  <Eye className="w-3.5 h-3.5" />
                  <span>Нажмите для деталей</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ABTestList;
