/**
 * PWAInstallPrompt — Компонент модального окна для предложения установки PWA.
 *
 * Функции:
 * - Отображение модального окна с предложением установки приложения
 * - Обработка установки через нативный prompt браузера
 * - Возможность отклонить предложение с опцией "Не показывать снова"
 * - Сохранение решения пользователя в localStorage
 * - Плавная анимация появления
 * - Поддержка интернационализации
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Modal, ModalContent, ModalBody, ModalFooter, Button, Checkbox } from '@heroui/react';
import { useTranslation } from 'react-i18next';
import { Download, X, Smartphone, Monitor } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePWAInstall } from '../../hooks/usePWAInstall';

interface PWAInstallPromptProps {
  /**
   * Задержка перед показом промпта в миллисекундах
   * @default 3000
   */
  delay?: number;

  /**
   * Класс для дополнительной стилизации
   */
  className?: string;
}

const STORAGE_KEY = 'pwa-install-dismissed';
const DISMISS_DURATION = 30 * 24 * 60 * 60 * 1000; // 30 дней

const isDismissed = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }

  const dismissed = window.localStorage.getItem(STORAGE_KEY);
  if (!dismissed) {
    return false;
  }

  const dismissedTime = parseInt(dismissed, 10);
  const now = Date.now();

  // Удаляем устаревшую запись
  if (now - dismissedTime > DISMISS_DURATION) {
    window.localStorage.removeItem(STORAGE_KEY);
    return false;
  }

  return true;
};

const setDismissed = () => {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, Date.now().toString());
};

const PWAInstallPrompt: React.FC<PWAInstallPromptProps> = ({
  delay = 3000,
  className
}) => {
  const { t } = useTranslation();
  const { isInstallable, isInstalled, promptInstall } = usePWAInstall();
  const [isVisible, setIsVisible] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);

  // Показываем промпт с задержкой только если приложение можно установить
  useEffect(() => {
    if (!isInstallable || isInstalled) {
      return;
    }

    if (isDismissed()) {
      return;
    }

    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [isInstallable, isInstalled, delay]);

  const handleInstall = useCallback(async () => {
    setIsInstalling(true);
    try {
      const installed = await promptInstall();
      if (installed) {
        setIsVisible(false);
      }
    } catch (error) {
      console.error('Failed to install PWA:', error);
    } finally {
      setIsInstalling(false);
    }
  }, [promptInstall]);

  const handleDismiss = useCallback(() => {
    if (dontShowAgain) {
      setDismissed();
    }
    setIsVisible(false);
  }, [dontShowAgain]);

  // Не рендерим ничего, если промпт не должен быть показан
  if (!isInstallable || isInstalled) {
    return null;
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <Modal
          isOpen={isVisible}
          onClose={handleDismiss}
          size="md"
          backdrop="blur"
          classNames={{
            base: "bg-[#0a0e27]/95 backdrop-blur-xl border border-[#F5E6D3]/20",
            header: "border-b border-[#F5E6D3]/10",
            body: "py-6",
            footer: "border-t border-[#F5E6D3]/10",
            closeButton: "hover:bg-[#F5E6D3]/10 active:bg-[#F5E6D3]/20 text-[#F5E6D3]/60 hover:text-[#F5E6D3]"
          }}
          className={className}
        >
          <ModalContent>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
            >
              <ModalBody className="flex flex-col items-center text-center gap-4">
                {/* Иконки устройств */}
                <div className="flex items-center justify-center gap-4 mb-2">
                  <motion.div
                    animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <Smartphone className="h-12 w-12 text-[#F5E6D3]" />
                  </motion.div>
                  <motion.div
                    animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
                  >
                    <Monitor className="h-12 w-12 text-[#F5E6D3]" />
                  </motion.div>
                </div>

                {/* Заголовок */}
                <h2 className="text-2xl font-semibold text-[#F5E6D3] [text-shadow:0_0_20px_rgba(245,230,211,0.3)]">
                  {t('pwa.install.title', 'Установить приложение')}
                </h2>

                {/* Описание */}
                <p className="text-sm text-[#F5E6D3]/70 leading-relaxed">
                  {t('pwa.install.description', 'Установите приложение на устройство для быстрого доступа и работы в офлайн-режиме.')}
                </p>

                {/* Преимущества */}
                <div className="flex flex-col gap-2 w-full text-left">
                  <div className="flex items-start gap-3 text-sm text-[#F5E6D3]/80">
                    <div className="flex-shrink-0 w-5 h-5 rounded-full bg-[#F5E6D3]/10 flex items-center justify-center mt-0.5">
                      <span className="text-[#F5E6D3] text-xs">✓</span>
                    </div>
                    <span>
                      {t('pwa.install.benefit1', 'Быстрый доступ с главного экрана')}
                    </span>
                  </div>
                  <div className="flex items-start gap-3 text-sm text-[#F5E6D3]/80">
                    <div className="flex-shrink-0 w-5 h-5 rounded-full bg-[#F5E6D3]/10 flex items-center justify-center mt-0.5">
                      <span className="text-[#F5E6D3] text-xs">✓</span>
                    </div>
                    <span>
                      {t('pwa.install.benefit2', 'Работа без интернет-соединения')}
                    </span>
                  </div>
                  <div className="flex items-start gap-3 text-sm text-[#F5E6D3]/80">
                    <div className="flex-shrink-0 w-5 h-5 rounded-full bg-[#F5E6D3]/10 flex items-center justify-center mt-0.5">
                      <span className="text-[#F5E6D3] text-xs">✓</span>
                    </div>
                    <span>
                      {t('pwa.install.benefit3', 'Плавные анимации и высокая производительность')}
                    </span>
                  </div>
                </div>

                {/* Checkbox "Больше не показывать" */}
                <div className="flex items-center gap-2 mt-2">
                  <Checkbox
                    size="sm"
                    isSelected={dontShowAgain}
                    onValueChange={setDontShowAgain}
                    classNames={{
                      wrapper: "border-[#F5E6D3]/30",
                      icon: "text-[#F5E6D3]"
                    }}
                  >
                    <span className="text-xs text-[#F5E6D3]/60">
                      {t('pwa.install.dont_show_again', 'Больше не показывать')}
                    </span>
                  </Checkbox>
                </div>
              </ModalBody>

              <ModalFooter className="gap-3">
                {/* Кнопка отмены */}
                <Button
                  variant="flat"
                  onPress={handleDismiss}
                  disabled={isInstalling}
                  className="bg-transparent text-[#F5E6D3]/60 hover:bg-[#F5E6D3]/10 hover:text-[#F5E6D3]"
                  startContent={<X className="h-4 w-4" />}
                >
                  {t('pwa.install.cancel', 'Позже')}
                </Button>

                {/* Кнопка установки */}
                <Button
                  color="primary"
                  onPress={handleInstall}
                  disabled={isInstalling}
                  isLoading={isInstalling}
                  className="bg-[#F5E6D3] text-black font-semibold hover:bg-[#F5E6D3]/90 hover:shadow-[0_0_20px_rgba(245,230,211,0.3)] transition-all"
                  startContent={!isInstalling && <Download className="h-4 w-4" />}
                >
                  {isInstalling
                    ? t('pwa.install.installing', 'Установка...')
                    : t('pwa.install.install', 'Установить')
                  }
                </Button>
              </ModalFooter>
            </motion.div>
          </ModalContent>
        </Modal>
      )}
    </AnimatePresence>
  );
};

export default PWAInstallPrompt;
