/**
 * InstallButton — Компонент кнопки для установки PWA.
 *
 * Функции:
 * - Отображение кнопки установки только когда приложение доступно для установки
 * - Запуск нативного prompt установки браузера
 * - Отображение состояния загрузки во время установки
 * - Автоматическое скрытие после успешной установки
 * - Поддержка анимации и интернационализации
 * - Доступность и поддержка темной темы
 */

import React, { useCallback, useState } from 'react';
import { Download } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { usePWAInstall } from '../../hooks/usePWAInstall';
import { cn } from '../../lib/utils';

export interface InstallButtonProps {
  /**
   * Дополнительный класс для стилизации
   */
  className?: string;

  /**
   * Вариант отображения кнопки
   * @default 'primary'
   */
  variant?: 'primary' | 'secondary' | 'ghost';

  /**
   * Размер кнопки
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Показывать иконку
   * @default true
   */
  showIcon?: boolean;

  /**
   * Текст кнопки (переопределяет перевод)
   */
  label?: string;

  /**
   * Обработчик успешной установки
   */
  onInstallSuccess?: () => void;

  /**
   * Обработчик ошибки установки
   */
  onInstallError?: (error: Error) => void;
}

const variantStyles = {
  primary: 'bg-[#F5E6D3] text-black hover:bg-[#F5E6D3]/90 hover:shadow-[0_0_20px_rgba(245,230,211,0.3)]',
  secondary: 'bg-[#F5E6D3]/10 text-[#F5E6D3] hover:bg-[#F5E6D3]/20 border border-[#F5E6D3]/30',
  ghost: 'bg-transparent text-[#F5E6D3]/60 hover:bg-[#F5E6D3]/10 hover:text-[#F5E6D3]',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
};

const iconSizes = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

const InstallButton: React.FC<InstallButtonProps> = ({
  className,
  variant = 'primary',
  size = 'md',
  showIcon = true,
  label,
  onInstallSuccess,
  onInstallError,
}) => {
  const { t } = useTranslation();
  const { isInstallable, isInstalled, promptInstall } = usePWAInstall();
  const [isInstalling, setIsInstalling] = useState(false);

  const handleInstall = useCallback(async () => {
    if (!isInstallable || isInstalled || isInstalling) {
      return;
    }

    setIsInstalling(true);
    try {
      const installed = await promptInstall();
      if (installed && onInstallSuccess) {
        onInstallSuccess();
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Installation failed');
      if (onInstallError) {
        onInstallError(err);
      }
    } finally {
      setIsInstalling(false);
    }
  }, [isInstallable, isInstalled, isInstalling, promptInstall, onInstallSuccess, onInstallError]);

  // Не рендерим кнопку, если приложение нельзя установить или уже установлено
  if (!isInstallable || isInstalled) {
    return null;
  }

  const buttonText = label || t('pwa.install_button.label', 'Установить приложение');
  const iconSize = iconSizes[size];

  return (
    <motion.button
      type="button"
      onClick={handleInstall}
      disabled={isInstalling}
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-semibold transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-[#F5E6D3] focus:ring-offset-2 focus:ring-offset-[#0a0e27]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
        'active:scale-95',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      aria-label={t('pwa.install_button.aria_label', 'Установить приложение на устройство')}
      aria-busy={isInstalling}
    >
      {isInstalling ? (
        <>
          {/* Иконка загрузки */}
          <motion.div
            className={cn('flex-shrink-0', iconSize)}
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <Download className={iconSize} aria-hidden="true" />
          </motion.div>
          <span>
            {t('pwa.install_button.installing', 'Установка...')}
          </span>
        </>
      ) : (
        <>
          {/* Иконка загрузки */}
          {showIcon && (
            <Download className={cn('flex-shrink-0', iconSize)} aria-hidden="true" />
          )}
          <span>{buttonText}</span>
        </>
      )}
    </motion.button>
  );
};

export default InstallButton;
