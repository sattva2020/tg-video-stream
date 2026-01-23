/**
 * SyncStatus — Компонент для отображения статуса синхронизации офлайн-очереди.
 *
 * Функции:
 * - Отображение индикатора при наличии ожидающих изменений
 * - Информирование пользователя о количестве несинхронизированных данных
 * - Возможность ручной синхронизации
 * - Автоматическая синхронизация при восстановлении подключения
 * - Поддержка анимации появления/исчезновения
 */

import React, { useState } from 'react';
import { Cloud, CloudOff, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useOnlineStatus } from '../../hooks/useOnlineStatus';
import { useOfflineQueue } from '../../hooks/useOfflineQueue';
import { cn } from '../../lib/utils';

interface SyncStatusProps {
  className?: string;
}

type SyncState = 'idle' | 'syncing' | 'success' | 'error';

const SyncStatus: React.FC<SyncStatusProps> = ({ className }) => {
  const { t } = useTranslation();
  const isOnline = useOnlineStatus();
  const { queueSize, isQueueEmpty, processQueue } = useOfflineQueue();
  const [syncState, setSyncState] = useState<SyncState>('idle');

  const handleSync = async () => {
    if (!isOnline || isQueueEmpty()) {
      return;
    }

    setSyncState('syncing');
    try {
      await processQueue();
      setSyncState('success');
      setTimeout(() => setSyncState('idle'), 2000);
    } catch (error) {
      setSyncState('error');
      setTimeout(() => setSyncState('idle'), 3000);
    }
  };

  // Сбрасываем состояние синхронизации при изменении размера очереди
  React.useEffect(() => {
    if (isQueueEmpty() && syncState === 'syncing') {
      setSyncState('idle');
    }
  }, [queueSize, syncState, isQueueEmpty]);

  const hasPendingChanges = !isQueueEmpty();

  const getIcon = () => {
    if (syncState === 'syncing') {
      return <RefreshCw className="h-5 w-5 animate-spin" aria-hidden="true" />;
    }
    if (syncState === 'success') {
      return <CheckCircle2 className="h-5 w-5" aria-hidden="true" />;
    }
    if (syncState === 'error') {
      return <AlertCircle className="h-5 w-5" aria-hidden="true" />;
    }
    if (!isOnline) {
      return <CloudOff className="h-5 w-5" aria-hidden="true" />;
    }
    return <Cloud className="h-5 w-5" aria-hidden="true" />;
  };

  const getAriaLabel = () => {
    if (syncState === 'syncing') {
      return t('pwa.sync.syncing_aria_label', 'Синхронизация...');
    }
    if (syncState === 'success') {
      return t('pwa.sync.success_aria_label', 'Синхронизация завершена');
    }
    if (syncState === 'error') {
      return t('pwa.sync.error_aria_label', 'Ошибка синхронизации');
    }
    if (!isOnline) {
      return t('pwa.sync.offline_aria_label', 'Ожидаются изменения (офлайн)');
    }
    return t('pwa.sync.pending_aria_label', 'Ожидаются изменения', { count: queueSize });
  };

  return (
    <AnimatePresence>
      {hasPendingChanges && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'fixed bottom-0 left-0 right-0 z-40 border-t px-4 py-3 shadow-lg md:py-4',
            syncState === 'error' && 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-900 dark:text-red-100',
            syncState === 'success' && 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-900 dark:text-green-100',
            syncState === 'syncing' && 'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-100',
            syncState === 'idle' && 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100',
            className
          )}
          role="status"
          aria-live="polite"
          aria-label={getAriaLabel()}
        >
          <div className="mx-auto max-w-7xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {getIcon()}
              <div className="flex flex-col">
                <span className="text-sm font-semibold">
                  {syncState === 'syncing' && t('pwa.sync.syncing_title', 'Синхронизация...')}
                  {syncState === 'success' && t('pwa.sync.success_title', 'Синхронизировано')}
                  {syncState === 'error' && t('pwa.sync.error_title', 'Ошибка синхронизации')}
                  {syncState === 'idle' && !isOnline && t('pwa.sync.offline_title', 'Ожидают подключения')}
                  {syncState === 'idle' && isOnline && t('pwa.sync.pending_title', 'Ожидают синхронизации')}
                </span>
                <span className="text-xs opacity-90">
                  {syncState === 'syncing' && t('pwa.sync.syncing_message', 'Обработка изменений...')}
                  {syncState === 'success' && t('pwa.sync.success_message', 'Все изменения успешно сохранены')}
                  {syncState === 'error' && t('pwa.sync.error_message', 'Не удалось синхронизировать изменения')}
                  {syncState === 'idle' && !isOnline && t('pwa.sync.offline_message', 'Изменения будут отправлены при подключении к сети', { count: queueSize })}
                  {syncState === 'idle' && isOnline && t('pwa.sync.pending_message', '{count} {count, one, изменение} {count, few, изменения} {count, many, изменений} ожидают отправки', { count: queueSize })}
                </span>
              </div>
            </div>
            {isOnline && syncState === 'idle' && (
              <button
                type="button"
                onClick={handleSync}
                disabled={syncState === 'syncing'}
                className={cn(
                  'inline-flex items-center gap-2 rounded-lg px-3 py-2',
                  'text-sm font-medium transition-colors',
                  'bg-slate-200 dark:bg-slate-800',
                  'hover:bg-slate-300 dark:hover:bg-slate-700',
                  'focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2',
                  'active:scale-95',
                  'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100'
                )}
                aria-label={t('pwa.sync.sync_button', 'Синхронизировать сейчас')}
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">
                  {t('pwa.sync.sync_now', 'Синхронизировать')}
                </span>
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SyncStatus;
