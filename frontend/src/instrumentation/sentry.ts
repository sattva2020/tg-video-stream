/**
 * Sentry/Glitchtip integration для frontend error tracking и APM.
 * Автоматический захват ошибок React, network requests, performance traces.
 */

import * as Sentry from '@sentry/react';

/**
 * Инициализация Sentry для отслеживания ошибок.
 * Вызывать в main.tsx перед рендерингом приложения.
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;

  if (!dsn) {
    console.warn('⚠️  VITE_SENTRY_DSN not set, error tracking disabled');
    return;
  }

  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production';
  const release = import.meta.env.VITE_SENTRY_RELEASE || 'unknown';

  Sentry.init({
    dsn,
    environment,
    release,

    // Интеграции
    integrations: [
      // Browser tracing для performance monitoring
      Sentry.browserTracingIntegration(),
      // Replay session для debugging (опционально)
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Performance Monitoring
    tracesSampleRate: 1.0, // 100% транзакций (можно уменьшить до 0.1 в production)

    // Session Replay
    replaysSessionSampleRate: 0.1, // 10% сессий
    replaysOnErrorSampleRate: 1.0, // 100% сессий с ошибками

    // Не отправлять PII
    beforeSend(event) {
      // Фильтрация событий перед отправкой
      
      // Игнорировать ошибки от расширений браузера
      if (event.exception?.values?.[0]?.stacktrace?.frames) {
        const frames = event.exception.values[0].stacktrace.frames;
        const isExtensionError = frames.some((frame) =>
          frame.filename?.includes('chrome-extension://') ||
          frame.filename?.includes('moz-extension://')
        );
        if (isExtensionError) {
          return null; // Не отправлять
        }
      }

      // Игнорировать ошибки от ad blockers
      if (event.message?.includes('adsbygoogle')) {
        return null;
      }

      // Добавить пользовательские теги
      event.tags = {
        ...event.tags,
        app: 'sattva-tv-frontend',
      };

      return event;
    },

    // Игнорировать определённые ошибки
    ignoreErrors: [
      // Network errors (часто возникают при проблемах с интернетом)
      'NetworkError',
      'Network request failed',
      'Failed to fetch',
      
      // Ошибки от расширений браузера
      'ResizeObserver loop limit exceeded',
      'Non-Error promise rejection captured',
      
      // Ошибки отмены запросов
      'Request aborted',
      'canceled',
    ],

    // Breadcrumbs (контекст для debugging)
    maxBreadcrumbs: 50,
    attachStacktrace: true,
  });

  console.log(
    `✅ Sentry initialized: environment=${environment}, release=${release}`
  );
}

/**
 * Установка контекста пользователя (после логина).
 */
export function setSentryUser(user: { id: string; username?: string; email?: string }) {
  Sentry.setUser({
    id: user.id,
    username: user.username,
    email: user.email,
  });
}

/**
 * Очистка контекста пользователя (после логаута).
 */
export function clearSentryUser() {
  Sentry.setUser(null);
}

/**
 * Ручной захват исключения.
 */
export function captureException(error: Error, context?: Record<string, any>) {
  if (context) {
    Sentry.setContext('custom', context);
  }
  Sentry.captureException(error);
}

/**
 * Ручная отправка сообщения (для важных событий).
 */
export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  Sentry.captureMessage(message, level);
}

/**
 * HOC для оборачивания компонентов с error boundary.
 * Автоматически ловит ошибки в React компонентах.
 */
export const withSentryErrorBoundary = Sentry.withErrorBoundary;

/**
 * React Error Boundary компонент.
 * Использовать для оборачивания критичных частей приложения.
 */
export const SentryErrorBoundary = Sentry.ErrorBoundary;

// Экспорт Sentry для расширенного использования
export { Sentry };
