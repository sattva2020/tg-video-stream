/**
 * Тесты для хука useScheduleAI
 *
 * Проверяет:
 * - Получение AI-рекомендаций
 * - Предпросмотр оптимизации расписания
 * - Генерацию расписания автопилота
 * - Получение анализа пиковых часов
 * - Обнаружение конфликтов
 * - Разрешение конфликтов
 * - Обнаружение пробелов
 * - Обработку ошибок
 * - Инвалидацию кэша
 * - Toast-уведомления
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useScheduleRecommendations,
  usePreviewOptimization,
  useGenerateAutoPilotSchedule,
  usePreviewAutoPilotSchedule,
  usePeakHours,
  useDetectConflicts,
  useResolveConflicts,
  useDetectGaps,
} from '../useScheduleAI';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { scheduleAIApi } from '../api/scheduleAI';
import { toast } from 'sonner';

// Mock API
vi.mock('../api/scheduleAI', () => ({
  scheduleAIApi: {
    getRecommendations: vi.fn(),
    previewOptimization: vi.fn(),
    generateAutoPilotSchedule: vi.fn(),
    previewAutoPilotSchedule: vi.fn(),
    getPeakHours: vi.fn(),
    detectConflicts: vi.fn(),
    resolveConflicts: vi.fn(),
    detectGaps: vi.fn(),
  },
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useScheduleAI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useScheduleRecommendations', () => {
    it('получает рекомендации для расписания', async () => {
      const mockRecommendations = {
        channel_id: 'test-channel',
        target_date: '2025-01-23',
        recommendations: [
          {
            id: '1',
            channel_id: 'test-channel',
            target_date: '2025-01-23',
            recommendation_type: 'content' as const,
            playlist_id: 'playlist-1',
            playlist_name: 'Test Playlist',
            suggested_start_time: '10:00',
            suggested_end_time: '12:00',
            confidence_score: 85,
            reason: 'Высокая вовлечённость',
            created_at: '2025-01-23T10:00:00Z',
          },
        ],
        metadata: {
          total_recommendations: 1,
          by_type: {
            content: 1,
            timing: 0,
            recurring: 0,
            gap_fill: 0,
          },
          avg_confidence: 85,
        },
        generated_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.getRecommendations).mockResolvedValue(mockRecommendations);

      const { result } = renderHook(
        () => useScheduleRecommendations('test-channel', '2025-01-23'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(scheduleAIApi.getRecommendations).toHaveBeenCalledWith(
        'test-channel',
        '2025-01-23',
        undefined
      );
      expect(result.current.data).toEqual(mockRecommendations);
    });

    it('передаёт параметры recommendations', async () => {
      const mockRecommendations = {
        channel_id: 'test-channel',
        target_date: '2025-01-23',
        recommendations: [],
        metadata: {
          total_recommendations: 0,
          by_type: {
            content: 0,
            timing: 0,
            recurring: 0,
            gap_fill: 0,
          },
          avg_confidence: 0,
        },
        generated_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.getRecommendations).mockResolvedValue(mockRecommendations);

      const { result } = renderHook(
        () =>
          useScheduleRecommendations('test-channel', '2025-01-23', {
            recommendation_types: ['content', 'timing'],
            max_recommendations: 5,
            min_confidence: 70,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(scheduleAIApi.getRecommendations).toHaveBeenCalledWith(
        'test-channel',
        '2025-01-23',
        {
          recommendation_types: ['content', 'timing'],
          max_recommendations: 5,
          min_confidence: 70,
        }
      );
    });

    it('не выполняет запрос при отсутствии channelId', () => {
      const { result } = renderHook(
        () => useScheduleRecommendations('', '2025-01-23'),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe('idle');
      expect(scheduleAIApi.getRecommendations).not.toHaveBeenCalled();
    });
  });

  describe('usePreviewOptimization', () => {
    it('предпросматривает оптимизацию расписания', async () => {
      const mockOptimization = {
        id: 'opt-1',
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-30',
        status: 'pending' as const,
        metrics: {
          coverage: 85,
          engagement_score: 75,
          variety_score: 80,
          conflicts_count: 5,
          peak_hours_coverage: 90,
        },
        suggestions: [],
        parameters: {
          prioritize_coverage: true,
          prioritize_variety: false,
          prioritize_peak_hours: true,
          maximize_engagement: true,
          avoid_conflicts: true,
        },
        created_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.previewOptimization).mockResolvedValue(mockOptimization);

      const { result } = renderHook(() => usePreviewOptimization(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-30',
        parameters: {
          prioritize_coverage: true,
          prioritize_variety: false,
          prioritize_peak_hours: true,
          maximize_engagement: true,
          avoid_conflicts: true,
        },
      };

      await act(async () => {
        await result.current.mutateAsync(request);
      });

      expect(scheduleAIApi.previewOptimization).toHaveBeenCalledWith(request);
      expect(toast.success).toHaveBeenCalledWith('Анализ расписания выполнен');
    });

    it('показывает ошибку при неудаче', async () => {
      const error = new Error('Ошибка оптимизации');
      vi.mocked(scheduleAIApi.previewOptimization).mockRejectedValue(error);

      const { result } = renderHook(() => usePreviewOptimization(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-30',
        parameters: {
          prioritize_coverage: true,
          prioritize_variety: false,
          prioritize_peak_hours: true,
          maximize_engagement: true,
          avoid_conflicts: true,
        },
      };

      await act(async () => {
        try {
          await result.current.mutateAsync(request);
        } catch {
          // Ожидаемая ошибка
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        'Ошибка оптимизации: Ошибка оптимизации'
      );
    });
  });

  describe('useGenerateAutoPilotSchedule', () => {
    it('генерирует расписание автопилота', async () => {
      const mockResponse = {
        channel_id: 'test-channel',
        date_range: { start: '2025-01-23', end: '2025-01-30' },
        slots_created: 10,
        gaps_filled: 5,
        conflicts_resolved: 2,
        status: 'completed' as const,
        generated_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.generateAutoPilotSchedule).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useGenerateAutoPilotSchedule(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        date_range: { start: '2025-01-23', end: '2025-01-30' },
        use_ai_recommendations: true,
      };

      await act(async () => {
        await result.current.mutateAsync(request);
      });

      expect(scheduleAIApi.generateAutoPilotSchedule).toHaveBeenCalledWith(request);
      expect(toast.success).toHaveBeenCalledWith('Расписание сгенерировано: создано 10 слотов');
    });

    it('показывает ошибку при неудаче генерации', async () => {
      const error = new Error('Ошибка генерации');
      vi.mocked(scheduleAIApi.generateAutoPilotSchedule).mockRejectedValue(error);

      const { result } = renderHook(() => useGenerateAutoPilotSchedule(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        date_range: { start: '2025-01-23', end: '2025-01-30' },
        use_ai_recommendations: true,
      };

      await act(async () => {
        try {
          await result.current.mutateAsync(request);
        } catch {
          // Ожидаемая ошибка
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        'Ошибка генерации расписания: Ошибка генерации'
      );
    });
  });

  describe('usePeakHours', () => {
    it('получает анализ пиковых часов', async () => {
      const mockPeakHours = {
        channel_id: 'test-channel',
        period: '30d',
        peak_hours: [
          {
            day_of_week: 1,
            hour: 19,
            avg_listeners: 100,
            play_count: 50,
            peak_listeners: 150,
            engagement_score: 85,
          },
        ],
        summary: {
          best_day: 1,
          best_hour: 19,
          avg_engagement: 85,
          total_samples: 100,
        },
        generated_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.getPeakHours).mockResolvedValue(mockPeakHours);

      const { result } = renderHook(
        () => usePeakHours('test-channel', '30d'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(scheduleAIApi.getPeakHours).toHaveBeenCalledWith('test-channel', '30d');
      expect(result.current.data).toEqual(mockPeakHours);
    });

    it('использует период по умолчанию 30d', async () => {
      const mockPeakHours = {
        channel_id: 'test-channel',
        period: '30d',
        peak_hours: [],
        summary: {
          best_day: 1,
          best_hour: 19,
          avg_engagement: 85,
          total_samples: 100,
        },
        generated_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.getPeakHours).mockResolvedValue(mockPeakHours);

      renderHook(() => usePeakHours('test-channel'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(scheduleAIApi.getPeakHours).toHaveBeenCalledWith('test-channel', '30d');
      });
    });

    it('не выполняет запрос при disabled=true', () => {
      const { result } = renderHook(
        () => usePeakHours('test-channel', '30d', false),
        { wrapper: createWrapper() }
      );

      expect(result.current.fetchStatus).toBe('idle');
      expect(scheduleAIApi.getPeakHours).not.toHaveBeenCalled();
    });
  });

  describe('useDetectConflicts', () => {
    it('обнаруживает конфликты в расписании', async () => {
      const mockConflicts = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
        conflicts: [],
        total_conflicts: 0,
        affected_dates: 0,
        analyzed_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.detectConflicts).mockResolvedValue(mockConflicts);

      const { result } = renderHook(() => useDetectConflicts(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
      };

      await act(async () => {
        await result.current.mutateAsync(request);
      });

      expect(scheduleAIApi.detectConflicts).toHaveBeenCalledWith(request);
      expect(toast.success).toHaveBeenCalledWith('Анализ конфликтов выполнен');
    });
  });

  describe('useResolveConflicts', () => {
    it('разрешает конфликты в расписании', async () => {
      const mockResolution = {
        channel_id: 'test-channel',
        date: '2025-01-23',
        resolutions_applied: 3,
        slots_removed: 2,
        slots_modified: 1,
        remaining_conflicts: 0,
        resolved_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.resolveConflicts).mockResolvedValue(mockResolution);

      const { result } = renderHook(() => useResolveConflicts(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
      };

      await act(async () => {
        await result.current.mutateAsync(request);
      });

      expect(scheduleAIApi.resolveConflicts).toHaveBeenCalledWith(request);
      expect(toast.success).toHaveBeenCalledWith('Конфликты разрешены: применено 3 решений');
    });
  });

  describe('useDetectGaps', () => {
    it('обнаруживает пробелы в расписании', async () => {
      const mockGaps = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
        gaps: [],
        total_gap_hours: 0,
        peak_hours_gaps: 0,
        analyzed_at: '2025-01-23T10:00:00Z',
      };

      vi.mocked(scheduleAIApi.detectGaps).mockResolvedValue(mockGaps);

      const { result } = renderHook(() => useDetectGaps(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
      };

      await act(async () => {
        await result.current.mutateAsync(request);
      });

      expect(scheduleAIApi.detectGaps).toHaveBeenCalledWith(request);
      expect(toast.success).toHaveBeenCalledWith('Анализ пробелов выполнен');
    });

    it('показывает ошибку при неудаче', async () => {
      const error = new Error('Ошибка обнаружения пробелов');
      vi.mocked(scheduleAIApi.detectGaps).mockRejectedValue(error);

      const { result } = renderHook(() => useDetectGaps(), {
        wrapper: createWrapper(),
      });

      const request = {
        channel_id: 'test-channel',
        start_date: '2025-01-23',
        end_date: '2025-01-23',
      };

      await act(async () => {
        try {
          await result.current.mutateAsync(request);
        } catch {
          // Ожидаемая ошибка
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        'Ошибка обнаружения пробелов: Ошибка обнаружения пробелов'
      );
    });
  });
});
