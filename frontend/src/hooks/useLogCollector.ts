/**
 * useLogCollector - React hook для автоматического сбора логов браузера
 * 
 * Собирает:
 * - Console logs (error, warn, info)
 * - Network errors (failed fetch/XHR)
 * - User actions (clicks, inputs)
 * - Performance metrics
 * 
 * @example
 * const { logs, browserInfo, createIncident, clearLogs } = useLogCollector();
 * 
 * // Создание инцидента с автоматически собранными логами
 * await createIncident({
 *   title: 'Не работает плейлист',
 *   description: 'При нажатии на кнопку Play ничего не происходит'
 * });
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  LogEntry,
  ConsoleLog,
  NetworkLog,
  ActionLog,
  PerformanceLog,
  BrowserInfo,
  LogCollectorConfig,
  CreateIncidentData,
  CreateIncidentResponse,
} from '../types/incident';

// Конфигурация по умолчанию
const DEFAULT_CONFIG: LogCollectorConfig = {
  maxLogs: 100,
  captureConsole: true,
  captureNetwork: true,
  captureActions: true,
  capturePerformance: true,
  ignoredUrls: [
    '/api/health',
    '/api/metrics',
    'google-analytics',
    'hotjar',
    'sentry',
  ],
  sensitiveKeys: [
    'password',
    'token',
    'secret',
    'key',
    'authorization',
    'cookie',
  ],
};

// Получение информации о браузере
function getBrowserInfo(): BrowserInfo {
  const ua = navigator.userAgent;
  let browserName = 'Unknown';
  let browserVersion = 'Unknown';
  let osName = 'Unknown';

  // Определение браузера
  if (ua.includes('Firefox/')) {
    browserName = 'Firefox';
    browserVersion = ua.split('Firefox/')[1]?.split(' ')[0] || 'Unknown';
  } else if (ua.includes('Chrome/') && !ua.includes('Edg/')) {
    browserName = 'Chrome';
    browserVersion = ua.split('Chrome/')[1]?.split(' ')[0] || 'Unknown';
  } else if (ua.includes('Safari/') && !ua.includes('Chrome/')) {
    browserName = 'Safari';
    browserVersion = ua.split('Version/')[1]?.split(' ')[0] || 'Unknown';
  } else if (ua.includes('Edg/')) {
    browserName = 'Edge';
    browserVersion = ua.split('Edg/')[1]?.split(' ')[0] || 'Unknown';
  }

  // Определение ОС
  if (ua.includes('Windows')) {
    osName = 'Windows';
    if (ua.includes('Windows NT 10.0')) osName = 'Windows 10/11';
    else if (ua.includes('Windows NT 6.3')) osName = 'Windows 8.1';
  } else if (ua.includes('Mac OS X')) {
    osName = 'macOS';
  } else if (ua.includes('Linux')) {
    osName = 'Linux';
  } else if (ua.includes('Android')) {
    osName = 'Android';
  } else if (ua.includes('iOS') || ua.includes('iPhone') || ua.includes('iPad')) {
    osName = 'iOS';
  }

  return {
    name: browserName,
    version: browserVersion,
    os: osName,
    platform: navigator.platform,
    userAgent: ua,
    language: navigator.language,
    screenResolution: `${screen.width}x${screen.height}`,
    viewportSize: `${window.innerWidth}x${window.innerHeight}`,
    colorDepth: screen.colorDepth,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

// Маскировка чувствительных данных
function maskSensitiveData(data: unknown, sensitiveKeys: string[]): unknown {
  if (typeof data !== 'object' || data === null) {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map(item => maskSensitiveData(item, sensitiveKeys));
  }

  const masked: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
    const isKeywordSensitive = sensitiveKeys.some(k => 
      key.toLowerCase().includes(k.toLowerCase())
    );
    
    if (isKeywordSensitive) {
      masked[key] = '***MASKED***';
    } else if (typeof value === 'object' && value !== null) {
      masked[key] = maskSensitiveData(value, sensitiveKeys);
    } else {
      masked[key] = value;
    }
  }
  return masked;
}

// Проверка, нужно ли игнорировать URL
function shouldIgnoreUrl(url: string, patterns: string[]): boolean {
  return patterns.some(pattern => url.includes(pattern));
}

export interface UseLogCollectorOptions {
  config?: Partial<LogCollectorConfig>;
  enabled?: boolean;
}

export interface UseLogCollectorReturn {
  logs: LogEntry[];
  browserInfo: BrowserInfo;
  isCollecting: boolean;
  lastError: LogEntry | null;
  
  // Методы
  addLog: (log: LogEntry) => void;
  logAction: (action: string, element?: string, metadata?: Record<string, unknown>) => void;
  clearLogs: () => void;
  createIncident: (data: Pick<CreateIncidentData, 'title' | 'description' | 'screenshot' | 'tags'>) => Promise<CreateIncidentResponse>;
  exportLogs: () => string;
}

export function useLogCollector(
  options: UseLogCollectorOptions = {}
): UseLogCollectorReturn {
  const { 
    config: userConfig = {}, 
    enabled = true 
  } = options;
  
  const config = { ...DEFAULT_CONFIG, ...userConfig };
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastError, setLastError] = useState<LogEntry | null>(null);
  const [isCollecting, setIsCollecting] = useState(enabled);
  
  const browserInfo = useRef<BrowserInfo>(getBrowserInfo());
  const originalConsole = useRef<{
    log: typeof console.log;
    warn: typeof console.warn;
    error: typeof console.error;
    info: typeof console.info;
  } | null>(null);
  const originalFetch = useRef<typeof fetch | null>(null);

  // Добавление лога с ограничением размера
  const addLog = useCallback((log: LogEntry) => {
    setLogs(prev => {
      const newLogs = [...prev, log];
      // Ограничиваем количество логов
      if (newLogs.length > config.maxLogs) {
        return newLogs.slice(-config.maxLogs);
      }
      return newLogs;
    });

    // Сохраняем последнюю ошибку
    if (log.type === 'console' && log.level === 'error') {
      setLastError(log);
    } else if (log.type === 'network' && log.statusCode && log.statusCode >= 400) {
      setLastError(log);
    }
  }, [config.maxLogs]);

  // Логирование действия пользователя
  const logAction = useCallback((
    action: string, 
    element?: string, 
    metadata?: Record<string, unknown>
  ) => {
    const log: ActionLog = {
      type: 'action',
      action,
      element,
      timestamp: new Date().toISOString(),
      metadata: metadata ? maskSensitiveData(metadata, config.sensitiveKeys) as Record<string, unknown> : undefined,
    };
    addLog(log);
  }, [addLog, config.sensitiveKeys]);

  // Очистка логов
  const clearLogs = useCallback(() => {
    setLogs([]);
    setLastError(null);
  }, []);

  // Экспорт логов в JSON
  const exportLogs = useCallback((): string => {
    return JSON.stringify({
      browserInfo: browserInfo.current,
      logs,
      exportedAt: new Date().toISOString(),
    }, null, 2);
  }, [logs]);

  // Перехват console
  useEffect(() => {
    if (!isCollecting || !config.captureConsole) return;

    // Сохраняем оригинальные методы
    originalConsole.current = {
      log: console.log,
      warn: console.warn,
      error: console.error,
      info: console.info,
    };

    const createConsoleHandler = (level: 'info' | 'warn' | 'error') => {
      return (...args: unknown[]) => {
        // Вызываем оригинальный метод
        originalConsole.current?.[level === 'info' ? 'log' : level]?.(...args);

        // Создаём лог
        const log: ConsoleLog = {
          type: 'console',
          level,
          message: args.map(arg => {
            if (typeof arg === 'object') {
              try {
                return JSON.stringify(maskSensitiveData(arg, config.sensitiveKeys));
              } catch {
                return String(arg);
              }
            }
            return String(arg);
          }).join(' '),
          timestamp: new Date().toISOString(),
        };

        // Если это ошибка, пытаемся получить stack trace
        if (level === 'error' && args[0] instanceof Error) {
          log.stack = args[0].stack;
        }

        addLog(log);
      };
    };

    console.log = createConsoleHandler('info');
    console.info = createConsoleHandler('info');
    console.warn = createConsoleHandler('warn');
    console.error = createConsoleHandler('error');

    return () => {
      // Восстанавливаем оригинальные методы
      if (originalConsole.current) {
        console.log = originalConsole.current.log;
        console.warn = originalConsole.current.warn;
        console.error = originalConsole.current.error;
        console.info = originalConsole.current.info;
      }
    };
  }, [isCollecting, config.captureConsole, config.sensitiveKeys, addLog]);

  // Перехват fetch
  useEffect(() => {
    if (!isCollecting || !config.captureNetwork) return;

    originalFetch.current = window.fetch;

    window.fetch = async (input, init) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      const method = init?.method || 'GET';
      const startTime = performance.now();

      // Игнорируем некоторые URL
      if (shouldIgnoreUrl(url, config.ignoredUrls)) {
        return originalFetch.current!(input, init);
      }

      try {
        const response = await originalFetch.current!(input, init);
        const endTime = performance.now();

        const log: NetworkLog = {
          type: 'network',
          url,
          method,
          statusCode: response.status,
          responseTimeMs: Math.round(endTime - startTime),
          timestamp: new Date().toISOString(),
        };

        // Логируем только ошибки или медленные запросы
        if (!response.ok || (endTime - startTime) > 3000) {
          addLog(log);
        }

        return response;
      } catch (error) {
        const endTime = performance.now();

        const log: NetworkLog = {
          type: 'network',
          url,
          method,
          responseTimeMs: Math.round(endTime - startTime),
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString(),
        };

        addLog(log);
        throw error;
      }
    };

    return () => {
      if (originalFetch.current) {
        window.fetch = originalFetch.current;
      }
    };
  }, [isCollecting, config.captureNetwork, config.ignoredUrls, addLog]);

  // Отслеживание кликов
  useEffect(() => {
    if (!isCollecting || !config.captureActions) return;

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target) return;

      // Получаем информацию об элементе
      const tagName = target.tagName.toLowerCase();
      const id = target.id ? `#${target.id}` : '';
      const className = target.className && typeof target.className === 'string' 
        ? `.${target.className.split(' ').join('.')}` 
        : '';
      const text = target.textContent?.slice(0, 50) || '';
      
      const element = `${tagName}${id}${className}`;

      logAction('click', element, { 
        text: text.trim(),
        href: (target as HTMLAnchorElement).href || undefined,
      });
    };

    document.addEventListener('click', handleClick, { passive: true });

    return () => {
      document.removeEventListener('click', handleClick);
    };
  }, [isCollecting, config.captureActions, logAction]);

  // Отслеживание ошибок JavaScript
  useEffect(() => {
    if (!isCollecting) return;

    const handleError = (event: ErrorEvent) => {
      const log: ConsoleLog = {
        type: 'console',
        level: 'error',
        message: event.message,
        stack: event.error?.stack,
        timestamp: new Date().toISOString(),
        metadata: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      };
      addLog(log);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const log: ConsoleLog = {
        type: 'console',
        level: 'error',
        message: `Unhandled Promise Rejection: ${event.reason}`,
        stack: event.reason?.stack,
        timestamp: new Date().toISOString(),
      };
      addLog(log);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [isCollecting, addLog]);

  // Метрики производительности
  useEffect(() => {
    if (!isCollecting || !config.capturePerformance) return;

    // Логируем метрики после загрузки страницы
    const logPerformance = () => {
      const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      
      if (timing) {
        const metrics: PerformanceLog[] = [
          {
            type: 'performance',
            metric: 'domContentLoaded',
            value: Math.round(timing.domContentLoadedEventEnd - timing.startTime),
            timestamp: new Date().toISOString(),
          },
          {
            type: 'performance',
            metric: 'loadComplete',
            value: Math.round(timing.loadEventEnd - timing.startTime),
            timestamp: new Date().toISOString(),
          },
          {
            type: 'performance',
            metric: 'firstByte',
            value: Math.round(timing.responseStart - timing.requestStart),
            timestamp: new Date().toISOString(),
          },
        ];

        metrics.forEach(addLog);
      }

      // Web Vitals (LCP, FID, CLS)
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const log: PerformanceLog = {
            type: 'performance',
            metric: entry.entryType,
            value: Math.round(entry.startTime),
            timestamp: new Date().toISOString(),
            metadata: { name: entry.name },
          };
          addLog(log);
        }
      });

      try {
        observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
      } catch {
        // Some browsers don't support these entry types
      }
    };

    if (document.readyState === 'complete') {
      logPerformance();
    } else {
      window.addEventListener('load', logPerformance);
      return () => window.removeEventListener('load', logPerformance);
    }
  }, [isCollecting, config.capturePerformance, addLog]);

  // Создание инцидента
  const createIncident = useCallback(async (
    data: Pick<CreateIncidentData, 'title' | 'description' | 'screenshot' | 'tags'>
  ): Promise<CreateIncidentResponse> => {
    const incidentData: CreateIncidentData = {
      ...data,
      logs,
      browserInfo: browserInfo.current,
      pageUrl: window.location.href,
    };

    const response = await fetch('/api/incidents', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(incidentData),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create incident: ${errorText}`);
    }

    return response.json();
  }, [logs]);

  return {
    logs,
    browserInfo: browserInfo.current,
    isCollecting,
    lastError,
    addLog,
    logAction,
    clearLogs,
    createIncident,
    exportLogs,
  };
}

export default useLogCollector;
