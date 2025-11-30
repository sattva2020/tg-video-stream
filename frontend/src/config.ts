/**
 * Централизованная конфигурация приложения.
 * Загружает переменные окружения из Vite с fallback значениями.
 */

export const config = {
  // API URLs
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // Telegram Login Widget
  telegram: {
    botUsername: import.meta.env.VITE_TELEGRAM_BOT_USERNAME || '',
    // Размер кнопки: 'large' | 'medium' | 'small'
    buttonSize: 'large' as const,
    // Радиус углов кнопки (0-20)
    cornerRadius: 8,
    // Режим авторизации: 'popup' (рекомендуется для безопасности)
    authMode: 'popup' as const,
  },
  
  // Cloudflare Turnstile CAPTCHA
  turnstile: {
    siteKey: import.meta.env.VITE_TURNSTILE_SITE_KEY || '',
  },
} as const;

export type Config = typeof config;
