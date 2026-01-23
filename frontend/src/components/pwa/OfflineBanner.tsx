/**
 * OfflineBanner — Компонент для отображения статуса офлайн режима.
 *
 * Функции:
 * - Отображение баннера при отсутствии подключения к сети
 * - Информирование пользователя о режиме офлайн
 * - Автоматическое скрытие при восстановлении подключения
 * - Поддержка анимации появления/исчезновения
 */

import React from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useOnlineStatus } from '../../hooks/useOnlineStatus';
import { cn } from '../../lib/utils';

interface OfflineBannerProps {
  className?: string;
}

const OfflineBanner: React.FC<OfflineBannerProps> = ({ className }) => {
  const { t } = useTranslation();
  const isOnline = useOnlineStatus();

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <AnimatePresence>
      {!isOnline && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'fixed top-0 left-0 right-0 z-50 border-b px-4 py-3 shadow-md md:py-4',
            'bg-amber-50 dark:bg-amber-950',
            'border-amber-200 dark:border-amber-800',
            'text-amber-900 dark:text-amber-100',
            className
          )}
          role="alert"
          aria-live="polite"
          aria-label={t('pwa.offline.banner_aria_label', 'Offline mode active')}
        >
          <div className="mx-auto max-w-7xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <WifiOff
                className="h-5 w-5 flex-shrink-0"
                aria-hidden="true"
              />
              <div className="flex flex-col">
                <span className="text-sm font-semibold">
                  {t('pwa.offline.title', 'Вы не в сети')}
                </span>
                <span className="text-xs opacity-90">
                  {t('pwa.offline.message', 'Проверьте подключение к интернету. Данные могут быть устаревшими.')}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleReload}
              className={cn(
                'inline-flex items-center gap-2 rounded-lg px-3 py-2',
                'text-sm font-medium transition-colors',
                'bg-amber-200 dark:bg-amber-800',
                'hover:bg-amber-300 dark:hover:bg-amber-700',
                'focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2',
                'active:scale-95'
              )}
              aria-label={t('pwa.offline.reload_button', 'Перезагрузить страницу')}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">
                {t('pwa.offline.reload', 'Обновить')}
              </span>
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default OfflineBanner;
