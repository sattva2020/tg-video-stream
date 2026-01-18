/**
 * Тесты для хука useToast
 * 
 * Проверяет:
 * - Создание различных типов уведомлений
 * - Настройки длительности
 * - Promise-based уведомления
 * - Закрытие уведомлений
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useToast } from '../useToast';
import { toast } from 'sonner';

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    loading: vi.fn(() => 'mock-toast-id'),
    dismiss: vi.fn(),
    promise: vi.fn((promise) => {
      const actualPromise = typeof promise === 'function' ? promise() : promise;
      return actualPromise.then((val: any) => ({ unwrap: () => Promise.resolve(val) }));
    }),
  },
}));

describe('useToast', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Базовые уведомления', () => {
    it('вызывает toast.success с правильными параметрами', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.success('Успех!');
      });

      expect(toast.success).toHaveBeenCalledWith('Успех!', {
        duration: 4000,
      });
    });

    it('вызывает toast.error с правильными параметрами', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.error('Ошибка!');
      });

      expect(toast.error).toHaveBeenCalledWith('Ошибка!', {
        duration: 6000,
      });
    });

    it('вызывает toast.warning с правильными параметрами', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.warning('Внимание!');
      });

      expect(toast.warning).toHaveBeenCalledWith('Внимание!', {
        duration: 5000,
      });
    });

    it('вызывает toast.info с правильными параметрами', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.info('Информация');
      });

      expect(toast.info).toHaveBeenCalledWith('Информация', {
        duration: 4000,
      });
    });
  });

  describe('Кастомные опции', () => {
    it('принимает кастомные опции для success', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.success('Успех!', { duration: 2000 });
      });

      expect(toast.success).toHaveBeenCalledWith('Успех!', {
        duration: 2000,
      });
    });

    it('принимает кастомные опции для error', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.error('Ошибка!', { position: 'top-right' });
      });

      expect(toast.error).toHaveBeenCalledWith('Ошибка!', {
        duration: 6000,
        position: 'top-right',
      });
    });
  });

  describe('Loading уведомления', () => {
    it('создаёт loading уведомление и возвращает ID', () => {
      const { result } = renderHook(() => useToast());
      let toastId: string | number | undefined;

      act(() => {
        toastId = result.current.loading('Загрузка...');
      });

      expect(toast.loading).toHaveBeenCalledWith('Загрузка...', undefined);
      expect(toastId).toBe('mock-toast-id');
    });

    it('принимает опции для loading', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.loading('Загрузка...', { duration: Infinity });
      });

      expect(toast.loading).toHaveBeenCalledWith('Загрузка...', {
        duration: Infinity,
      });
    });
  });

  describe('Dismiss уведомления', () => {
    it('закрывает уведомление по ID', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.dismiss('toast-123');
      });

      expect(toast.dismiss).toHaveBeenCalledWith('toast-123');
    });

    it('закрывает все уведомления без ID', () => {
      const { result } = renderHook(() => useToast());

      act(() => {
        result.current.dismiss();
      });

      expect(toast.dismiss).toHaveBeenCalledWith(undefined);
    });
  });

  describe('Promise-based уведомления', () => {
    it('обрабатывает успешный promise', async () => {
      const { result } = renderHook(() => useToast());
      const mockPromise = Promise.resolve({ data: 'test' });

      await act(async () => {
        await result.current.promise(mockPromise, {
          loading: 'Загрузка...',
          success: 'Успех!',
          error: 'Ошибка!',
        });
      });

      expect(toast.promise).toHaveBeenCalledWith(mockPromise, {
        loading: 'Загрузка...',
        success: 'Успех!',
        error: 'Ошибка!',
      });
    });

    it('поддерживает функции для success сообщений', async () => {
      const { result } = renderHook(() => useToast());
      const mockPromise = Promise.resolve({ name: 'Test' });

      await act(async () => {
        await result.current.promise(mockPromise, {
          loading: 'Загрузка...',
          success: (data) => `Загружено: ${data.name}`,
          error: 'Ошибка!',
        });
      });

      expect(toast.promise).toHaveBeenCalledWith(
        mockPromise,
        expect.objectContaining({
          loading: 'Загрузка...',
          success: expect.any(Function),
          error: 'Ошибка!',
        })
      );
    });

    it('поддерживает функции для error сообщений', async () => {
      const { result } = renderHook(() => useToast());
      const mockPromise = Promise.reject(new Error('Test error'));

      // Mock для обработки rejected promise
      vi.mocked(toast.promise).mockImplementationOnce((p: any) => {
        const actualPromise = typeof p === 'function' ? p() : p;
        return actualPromise.catch(() => ({ unwrap: () => Promise.reject() }));
      });

      try {
        await act(async () => {
          await result.current.promise(mockPromise, {
            loading: 'Загрузка...',
            success: 'Успех!',
            error: (err) => `Ошибка: ${(err as Error).message}`,
          });
        });
      } catch {
        // Expected to fail
      }

      expect(toast.promise).toHaveBeenCalledWith(
        mockPromise,
        expect.objectContaining({
          loading: 'Загрузка...',
          success: 'Успех!',
          error: expect.any(Function),
        })
      );
    });
  });
});
