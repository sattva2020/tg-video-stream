import { toast, ExternalToast } from 'sonner';

/**
 * Централизованный хук для toast-уведомлений
 * Использует sonner для отображения уведомлений
 */

type ToastOptions = ExternalToast;

interface UseToastReturn {
  success: (message: string, options?: ToastOptions) => void;
  error: (message: string, options?: ToastOptions) => void;
  warning: (message: string, options?: ToastOptions) => void;
  info: (message: string, options?: ToastOptions) => void;
  loading: (message: string, options?: ToastOptions) => string | number;
  dismiss: (id?: string | number) => void;
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    }
  ) => Promise<T>;
}

/**
 * Хук для работы с toast-уведомлениями
 * 
 * @example
 * const toast = useToast();
 * 
 * // Простые уведомления
 * toast.success('Операция выполнена успешно');
 * toast.error('Произошла ошибка');
 * toast.warning('Внимание!');
 * toast.info('Информация');
 * 
 * // Promise-based
 * toast.promise(fetchData(), {
 *   loading: 'Загрузка...',
 *   success: 'Данные загружены',
 *   error: 'Ошибка загрузки'
 * });
 */
export function useToast(): UseToastReturn {
  return {
    success: (message, options) => {
      toast.success(message, {
        duration: 4000,
        ...options,
      });
    },

    error: (message, options) => {
      toast.error(message, {
        duration: 6000,
        ...options,
      });
    },

    warning: (message, options) => {
      toast.warning(message, {
        duration: 5000,
        ...options,
      });
    },

    info: (message, options) => {
      toast.info(message, {
        duration: 4000,
        ...options,
      });
    },

    loading: (message, options) => {
      return toast.loading(message, options);
    },

    dismiss: (id) => {
      toast.dismiss(id);
    },

    promise: async <T>(
      promise: Promise<T>,
      messages: {
        loading: string;
        success: string | ((data: T) => string);
        error: string | ((error: unknown) => string);
      }
    ) => {
      const result = await toast.promise(promise, messages);
      return result.unwrap();
    },
  };
}

// Экспортируем также статические методы для использования вне компонентов
export const showToast = {
  success: (message: string, options?: ToastOptions) => {
    toast.success(message, { duration: 4000, ...options });
  },
  error: (message: string, options?: ToastOptions) => {
    toast.error(message, { duration: 6000, ...options });
  },
  warning: (message: string, options?: ToastOptions) => {
    toast.warning(message, { duration: 5000, ...options });
  },
  info: (message: string, options?: ToastOptions) => {
    toast.info(message, { duration: 4000, ...options });
  },
  loading: (message: string, options?: ToastOptions) => {
    return toast.loading(message, options);
  },
  dismiss: (id?: string | number) => {
    toast.dismiss(id);
  },
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    }
  ) => {
    return toast.promise(promise, messages);
  },
};

export default useToast;
