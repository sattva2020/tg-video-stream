/**
 * Кнопка авторизации через Telegram Login Widget.
 * 
 * Использует кастомную стилизованную кнопку + скрытый Telegram Widget.
 * @see https://core.telegram.org/widgets/login
 */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import clsx from 'clsx';
import { config } from '../config';
import { TelegramAuthData } from '../services/telegramAuth';

// Telegram иконка
const TelegramIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
  </svg>
);

interface TelegramLoginButtonProps {
  /** Callback при получении данных от Telegram */
  onAuth: (data: TelegramAuthData) => void;
  /** Размер кнопки */
  buttonSize?: 'large' | 'medium' | 'small';
  /** Радиус скругления углов (0-20) */
  cornerRadius?: number;
  /** Показывать фото пользователя */
  showUserPhoto?: boolean;
  /** Дополнительные CSS классы */
  className?: string;
  /** Отключена ли кнопка */
  disabled?: boolean;
}

// Глобальный callback для Telegram Widget
declare global {
  interface Window {
    TelegramLoginCallback?: (user: TelegramAuthData) => void;
  }
}

/**
 * Компонент кнопки входа через Telegram.
 * 
 * Показывает кастомную стилизованную кнопку.
 * При клике симулирует клик на скрытый Telegram Widget.
 */
export const TelegramLoginButton: React.FC<TelegramLoginButtonProps> = ({
  onAuth,
  buttonSize = config.telegram.buttonSize,
  cornerRadius = config.telegram.cornerRadius,
  showUserPhoto = true,
  className = '',
  disabled = false,
}) => {
  const hiddenContainerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);
  const [isWidgetReady, setIsWidgetReady] = useState(false);

  // Callback для Telegram Widget
  const handleAuth = useCallback((user: TelegramAuthData) => {
    if (!disabled) {
      onAuth(user);
    }
  }, [onAuth, disabled]);

  useEffect(() => {
    // Проверяем наличие bot username
    const botUsername = config.telegram.botUsername;
    if (!botUsername) {
      console.warn('VITE_TELEGRAM_BOT_USERNAME не настроен');
      return;
    }

    // Устанавливаем глобальный callback
    window.TelegramLoginCallback = handleAuth;

    // Создаём script элемент для Telegram Widget
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', buttonSize);
    script.setAttribute('data-radius', cornerRadius.toString());
    script.setAttribute('data-onauth', 'TelegramLoginCallback(user)');
    script.setAttribute('data-request-access', 'write');
    
    if (showUserPhoto) {
      script.setAttribute('data-userpic', 'true');
    } else {
      script.setAttribute('data-userpic', 'false');
    }

    // Добавляем script в скрытый контейнер
    if (hiddenContainerRef.current) {
      hiddenContainerRef.current.innerHTML = '';
      hiddenContainerRef.current.appendChild(script);
      scriptRef.current = script;
      
      // Отмечаем что widget загружен после небольшой задержки
      setTimeout(() => setIsWidgetReady(true), 500);
    }

    // Cleanup
    return () => {
      if (window.TelegramLoginCallback === handleAuth) {
        delete window.TelegramLoginCallback;
      }
      if (scriptRef.current && scriptRef.current.parentNode) {
        scriptRef.current.parentNode.removeChild(scriptRef.current);
      }
    };
  }, [handleAuth, buttonSize, cornerRadius, showUserPhoto]);

  // Обработчик клика на кастомную кнопку
  const handleCustomButtonClick = () => {
    if (disabled || !isWidgetReady) return;
    
    // Находим iframe от Telegram Widget и кликаем на него
    const iframe = hiddenContainerRef.current?.querySelector('iframe');
    if (iframe) {
      // Симулируем клик на iframe - это откроет popup Telegram
      iframe.click();
    }
  };

  // Если bot username не настроен, показываем заглушку
  if (!config.telegram.botUsername) {
    return (
      <div className={`text-center text-gray-500 text-sm ${className}`}>
        Telegram авторизация не настроена
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Скрытый контейнер для оригинального Telegram Widget */}
      <div 
        ref={hiddenContainerRef}
        className="absolute opacity-0 pointer-events-none h-0 overflow-hidden"
        aria-hidden="true"
      />
      
      {/* Кастомная стилизованная кнопка */}
      <button
        type="button"
        onClick={handleCustomButtonClick}
        disabled={disabled || !isWidgetReady}
        className={clsx(
          'group flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-lg transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
          '!bg-[#F5E6D3]/10 !text-[#F5E6D3] !border !border-[#F5E6D3]/30',
          'hover:!shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:!bg-[#F5E6D3]/20 hover:!border-[#F5E6D3]/50',
        )}
        aria-label="Войти через Telegram"
      >
        <TelegramIcon />
        <span className="tracking-wide">Войти через Telegram</span>
      </button>
    </div>
  );
};

export default TelegramLoginButton;
