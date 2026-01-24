/**
 * React хук для очереди офлайн-мутаций
 * Позволяет накапливать запросы при отсутствии сети и выполнять их при восстановлении соединения
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useOnlineStatus } from './useOnlineStatus';
import { useToast } from './useToast';

/**
 * Элемент очереди мутаций
 */
interface QueuedMutation<T = any> {
  id: string;
  timestamp: number;
  mutationFn: () => Promise<T>;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  retryCount?: number;
}

/**
 * Опции для добавления мутации в очередь
 */
interface QueueMutationOptions<T = any> {
  mutationFn: () => Promise<T>;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  maxRetries?: number;
}

/**
 * Ключ для localStorage
 */
const QUEUE_STORAGE_KEY = 'offline-mutation-queue';

/**
 * Хук для управления офлайн-очередью мутаций
 *
 * Позволяет добавлять мутации в очередь, когда пользователь офлайн,
 * и автоматически выполнять их при восстановлении соединения.
 *
 * @example
 * ```tsx
 * const { queueMutation, isQueueEmpty, queueSize } = useOfflineQueue();
 *
 * const addPlaylistItem = (data: any) => {
 *   queueMutation({
 *     mutationFn: () => playlistService.addPlaylistItem(data),
 *     onSuccess: (newItem) => {
 *       toast.success(`Трек "${newItem.title}" добавлен`);
 *     },
 *     onError: (error) => {
 *       toast.error(`Ошибка: ${error.message}`);
 *     },
 *   });
 * };
 * ```
 */
export function useOfflineQueue() {
  const isOnline = useOnlineStatus();
  const toast = useToast();
  const processingRef = useRef(false);
  const queueRef = useRef<QueuedMutation[]>([]);
  const [queueSize, setQueueSize] = useState(0);

  /**
   * Загружает очередь из localStorage
   */
  const loadQueue = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          queueRef.current = parsed;
          setQueueSize(parsed.length);
        }
      }
    } catch (error) {
      // Ошибка при загрузке — начинаем с пустой очередью
      console.error('Failed to load offline queue:', error);
      queueRef.current = [];
      setQueueSize(0);
    }
  }, []);

  /**
   * Сохраняет очередь в localStorage
   */
  const saveQueue = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      // Сохраняем только данные, необходимые для восстановления
      const serializable = queueRef.current.map(item => ({
        id: item.id,
        timestamp: item.timestamp,
        retryCount: item.retryCount,
      }));
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(serializable));
    } catch (error) {
      // Локальное хранилище может быть переполнено или недоступно
      console.warn('Failed to save offline queue:', error);
    }
  }, []);

  /**
   * Загружаем очередь при монтировании
   */
  useEffect(() => {
    loadQueue();

    // Также загружаем при восстановлении страницы
    const handleLoad = () => {
      loadQueue();
    };

    window.addEventListener('load', handleLoad);
    return () => {
      window.removeEventListener('load', handleLoad);
    };
  }, [loadQueue]);

  /**
   * Обрабатываем очередь при восстановлении соединения
   */
  useEffect(() => {
    if (isOnline && !processingRef.current && queueRef.current.length > 0) {
      processQueue();
    }
  }, [isOnline, processQueue]);

  /**
   * Обрабатывает все мутации в очереди
   */
  const processQueue = useCallback(async () => {
    if (processingRef.current || queueRef.current.length === 0) {
      return;
    }

    processingRef.current = true;

    try {
      // Обрабатываем очередь последовательно
      while (queueRef.current.length > 0) {
        const item = queueRef.current[0];

        try {
          const result = await item.mutationFn();

          // Успешно — удаляем из очереди
          queueRef.current.shift();
          setQueueSize(prev => prev - 1);
          saveQueue();

          if (item.onSuccess) {
            item.onSuccess(result);
          }
        } catch (error) {
          const errorObj = error instanceof Error ? error : new Error(String(error));

          // Проверяем количество попыток
          const maxRetries = 3;
          const currentRetries = item.retryCount || 0;

          if (currentRetries < maxRetries) {
            // Увеличиваем счётчик попыток и перемещаем в конец очереди
            queueRef.current.shift();
            const retryItem = { ...item, retryCount: currentRetries + 1 };
            queueRef.current.push(retryItem);
            saveQueue();

            // Небольшая задержка перед повторной попыткой
            await new Promise(resolve => setTimeout(resolve, 1000));
          } else {
            // Превышен лимит попыток — удаляем из очереди
            queueRef.current.shift();
            setQueueSize(prev => prev - 1);
            saveQueue();

            if (item.onError) {
              item.onError(errorObj);
            } else {
              toast.error(`Не удалось выполнить операцию: ${errorObj.message}`);
            }
          }
        }
      }
    } finally {
      processingRef.current = false;
    }
  }, [toast, saveQueue]);

  /**
   * Добавляет мутацию в очередь
   *
   * Если онлайн — выполняет сразу, если офлайн — добавляет в очередь.
   *
   * @param options Опции мутации
   */
  const queueMutation = useCallback(
    <T,>(options: QueueMutationOptions<T>) => {
      const { mutationFn, onSuccess, onError } = options;

      if (isOnline) {
        // Онлайн — выполняем сразу
        mutationFn()
          .then((data) => {
            if (onSuccess) {
              onSuccess(data);
            }
          })
          .catch((error) => {
            const errorObj = error instanceof Error ? error : new Error(String(error));
            if (onError) {
              onError(errorObj);
            } else {
              toast.error(`Ошибка: ${errorObj.message}`);
            }
          });
      } else {
        // Офлайн — добавляем в очередь
        const generateId = () => {
          if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return `${Date.now()}-${crypto.randomUUID()}`;
          }
          return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
        };

        const item: QueuedMutation<T> = {
          id: generateId(),
          timestamp: Date.now(),
          mutationFn,
          onSuccess,
          onError,
          retryCount: 0,
        };

        queueRef.current.push(item);
        setQueueSize(prev => prev + 1);
        saveQueue();

        toast.info('Сохранено в офлайн-очередь. Выполнится при подключении к сети.');
      }
    },
    [isOnline, toast, saveQueue]
  );

  /**
   * Очищает всю очередь
   */
  const clearQueue = useCallback(() => {
    queueRef.current = [];
    setQueueSize(0);

    if (typeof window !== 'undefined') {
      localStorage.removeItem(QUEUE_STORAGE_KEY);
    }
  }, []);

  /**
   * Проверяет, пуста ли очередь
   */
  const isQueueEmpty = useCallback(() => {
    return queueRef.current.length === 0;
  }, []);

  return {
    /**
     * Добавляет мутацию в очередь (или выполняет сразу, если онлайн)
     */
    queueMutation,

    /**
     * Размер очереди
     */
    queueSize,

    /**
     * Пуста ли очередь
     */
    isQueueEmpty,

    /**
     * Очищает очередь
     */
    clearQueue,

    /**
     * Обрабатывает очередь вручную
     */
    processQueue,
  };
}
