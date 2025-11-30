/**
 * Кнопка авторизации через Telegram Login Widget.
 * 
 * Использует официальный Telegram Login Widget в режиме popup.
 * @see https://core.telegram.org/widgets/login
 */
import React, { useEffect, useRef, useCallback } from 'react';
import { config } from '../config';
import { TelegramAuthData } from '../services/telegramAuth';

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
 * При клике открывает popup окно Telegram для авторизации.
 * После авторизации вызывает onAuth с данными пользователя.
 */
export const TelegramLoginButton: React.FC<TelegramLoginButtonProps> = ({
  onAuth,
  buttonSize = config.telegram.buttonSize,
  cornerRadius = config.telegram.cornerRadius,
  showUserPhoto = true,
  className = '',
  disabled = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

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

    // Добавляем script в контейнер
    if (containerRef.current) {
      // Очищаем предыдущий контент
      containerRef.current.innerHTML = '';
      containerRef.current.appendChild(script);
      scriptRef.current = script;
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

  // Если bot username не настроен, показываем заглушку
  if (!config.telegram.botUsername) {
    return (
      <div className={`text-center text-gray-500 text-sm ${className}`}>
        Telegram авторизация не настроена
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`flex justify-center ${disabled ? 'opacity-50 pointer-events-none' : ''} ${className}`}
      aria-label="Войти через Telegram"
    />
  );
};

export default TelegramLoginButton;
