/**
 * Cloudflare Turnstile CAPTCHA компонент.
 * 
 * Использует Turnstile API для защиты от ботов.
 * @see https://developers.cloudflare.com/turnstile/
 */
import React, { useEffect, useRef, useCallback } from 'react';
import { config } from '../config';

interface TurnstileWidgetProps {
  /** Callback при успешной проверке CAPTCHA */
  onVerify: (token: string) => void;
  /** Callback при истечении срока действия токена */
  onExpire?: () => void;
  /** Callback при ошибке */
  onError?: (error: string) => void;
  /** Тема: 'light' | 'dark' | 'auto' */
  theme?: 'light' | 'dark' | 'auto';
  /** Размер: 'normal' | 'compact' */
  size?: 'normal' | 'compact';
  /** Дополнительные CSS классы */
  className?: string;
}

// Типы для Turnstile API
declare global {
  interface Window {
    turnstile?: {
      render: (container: string | HTMLElement, options: TurnstileOptions) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
      getResponse: (widgetId: string) => string | undefined;
    };
  }
}

interface TurnstileOptions {
  sitekey: string;
  callback: (token: string) => void;
  'expired-callback'?: () => void;
  'error-callback'?: (error: string) => void;
  theme?: 'light' | 'dark' | 'auto';
  size?: 'normal' | 'compact';
}

/**
 * Загружает Turnstile скрипт если ещё не загружен.
 */
function loadTurnstileScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }

    const existingScript = document.querySelector('script[src*="turnstile"]');
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve());
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Turnstile')));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Turnstile'));
    document.head.appendChild(script);
  });
}

/**
 * Компонент Cloudflare Turnstile CAPTCHA.
 * 
 * Рендерит невидимый или видимый CAPTCHA widget.
 * При успешной проверке вызывает onVerify с токеном.
 */
export const TurnstileWidget: React.FC<TurnstileWidgetProps> = ({
  onVerify,
  onExpire,
  onError,
  theme = 'auto',
  size = 'normal',
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  const handleVerify = useCallback((token: string) => {
    onVerify(token);
  }, [onVerify]);

  const handleExpire = useCallback(() => {
    if (onExpire) {
      onExpire();
    }
  }, [onExpire]);

  const handleError = useCallback((error: string) => {
    console.error('Turnstile error:', error);
    if (onError) {
      onError(error);
    }
  }, [onError]);

  useEffect(() => {
    const siteKey = config.turnstile.siteKey;
    if (!siteKey) {
      console.warn('VITE_TURNSTILE_SITE_KEY не настроен');
      return;
    }

    let mounted = true;

    const initWidget = async () => {
      try {
        await loadTurnstileScript();
        
        if (!mounted || !containerRef.current || !window.turnstile) {
          return;
        }

        // Очищаем предыдущий widget если есть
        if (widgetIdRef.current) {
          try {
            window.turnstile.remove(widgetIdRef.current);
          } catch (e) {
            // Игнорируем ошибки удаления
          }
        }

        // Рендерим новый widget
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          callback: handleVerify,
          'expired-callback': handleExpire,
          'error-callback': handleError,
          theme,
          size,
        });
      } catch (error) {
        console.error('Failed to initialize Turnstile:', error);
        if (onError) {
          onError('Failed to load CAPTCHA');
        }
      }
    };

    initWidget();

    return () => {
      mounted = false;
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch (e) {
          // Игнорируем ошибки удаления
        }
      }
    };
  }, [theme, size, handleVerify, handleExpire, handleError, onError]);

  // Если site key не настроен, не рендерим ничего
  if (!config.turnstile.siteKey) {
    return null;
  }

  return (
    <div 
      ref={containerRef}
      className={`cf-turnstile ${className}`}
      aria-label="CAPTCHA verification"
    />
  );
};

export default TurnstileWidget;
