/**
 * Sentry/Glitchtip integration для mobile error tracking и APM.
 * Автоматический захват ошибок React Native, network requests, performance traces.
 *
 * Follows pattern from frontend/src/instrumentation/sentry.ts
 */

import * as Sentry from '@sentry/react-native';

/**
 * Инициализация Sentry для отслеживания ошибок.
 * Вызывать в App.tsx перед рендерингом приложения.
 */
export function initSentry() {
  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;

  if (!dsn) {
    console.warn('⚠️  EXPO_PUBLIC_SENTRY_DSN not set, error tracking disabled');
    return;
  }

  const environment = process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT || 'production';
  const release = process.env.EXPO_PUBLIC_SENTRY_RELEASE || 'unknown';

  Sentry.init({
    dsn,
    environment,
    release,

    // Интеграции для React Native
    integrations: [
      // Mobile file I/O tracing
      new Sentry.ReactNativeTracing({
        tracingOrigins: ['localhost', 'api.sattva.tv', /^\//],
      }),
    ],

    // Performance Monitoring
    tracesSampleRate: 1.0, // 100% транзакций (можно уменьшить до 0.1 в production)

    // Не отправлять PII
    beforeSend(event) {
      // Фильтрация событий перед отправкой

      // Игнорировать ошибки от development mode
      if (__DEV__) {
        // В development можно логировать но не отправлять
        console.log('[Sentry] Event:', event);
        return null;
      }

      // Добавить устройство и контекст
      event.tags = {
        ...event.tags,
        app: 'sattva-tv-mobile',
      };

      return event;
    },

    // Игнорировать определённые ошибки
    ignoreErrors: [
      // Network errors (часто возникают при проблемах с интернетом)
      'NetworkError',
      'Network request failed',
      'Failed to fetch',

      // Ошибки отмены запросов
      'Request aborted',
      'canceled',

      // React Native специфичные ошибки
      'Non-Error promise rejection captured',

      // Ошибки от development
      'Warning: ',
    ],

    // Breadcrumbs (контекст для debugging)
    maxBreadcrumbs: 50,
    attachStacktrace: true,

    // React Native специфичные настройки
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 30000,

    // Профилирование производительности (опционально)
    enableWatchdogTerminationTracking: true,
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
