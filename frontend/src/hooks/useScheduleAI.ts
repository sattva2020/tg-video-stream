/**
 * React Query хуки для работы с AI-функционалом расписания.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  scheduleAIApi,
  ScheduleOptimizationRequest,
  AutoPilotRequest,
  ConflictDetectionRequest,
  GapDetectionRequest,
} from '../api/scheduleAI';
import { useToast } from './useToast';

// ==================== Error Handling ====================

interface ApiErrorResponse {
  detail?: string;
}

/**
 * Преобразует ошибку API в понятное сообщение на русском
 * @param error - Ошибка от API или JavaScript
 * @param prefix - Опциональный префикс для сообщения
 */
function getErrorMessage(error: unknown, prefix?: string): string {
  let message = 'Произошла неизвестная ошибка';

  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const detail = (error.response?.data as ApiErrorResponse)?.detail;

    if (status === 409) {
      message = 'Конфликт данных. Попробуйте обновить страницу.';
    } else if (status === 404) {
      message = 'Элемент не найден. Возможно, он был удалён.';
    } else if (status === 400) {
      message = detail || 'Неверные данные. Проверьте заполненные поля.';
    } else if (status === 401) {
      message = 'Сессия истекла. Пожалуйста, войдите снова.';
    } else if (status === 403) {
      message = 'У вас нет прав для этого действия.';
    } else if (status === 500) {
      message = 'Ошибка сервера. Попробуйте позже.';
    } else if (detail) {
      message = detail;
    }
  } else if (error instanceof Error) {
    message = error.message;
  }

  return prefix ? `${prefix}: ${message}` : message;
}

// ==================== Query Keys ====================

export const scheduleAIQueryKeys = {
  all: ['scheduleAI'] as const,
  recommendations: (channelId: string, date: string) =>
    [...scheduleAIQueryKeys.all, 'recommendations', channelId, date] as const,
  optimization: (channelId: string, startDate: string, endDate: string) =>
    [...scheduleAIQueryKeys.all, 'optimization', channelId, startDate, endDate] as const,
  peakHours: (channelId: string, period: string) =>
    [...scheduleAIQueryKeys.all, 'peakHours', channelId, period] as const,
  conflicts: (channelId: string, startDate: string, endDate: string) =>
    [...scheduleAIQueryKeys.all, 'conflicts', channelId, startDate, endDate] as const,
  gaps: (channelId: string, startDate: string, endDate: string) =>
    [...scheduleAIQueryKeys.all, 'gaps', channelId, startDate, endDate] as const,
};

// ==================== Recommendations Hooks ====================

/**
 * Получить AI-рекомендации для расписания
 */
export function useScheduleRecommendations(
  channelId: string,
  date: string,
  params?: {
    recommendation_types?: string[];
    max_recommendations?: number;
    min_confidence?: number;
  }
) {
  return useQuery({
    queryKey: scheduleAIQueryKeys.recommendations(channelId, date),
    queryFn: () => scheduleAIApi.getRecommendations(channelId, date, params),
    enabled: !!channelId && !!date,
    staleTime: 10 * 60 * 1000, // 10 минут
  });
}

// ==================== Optimization Hooks ====================

/**
 * Предпросмотр оптимизации расписания
 */
export function usePreviewOptimization() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: ScheduleOptimizationRequest) =>
      scheduleAIApi.previewOptimization(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleAIQueryKeys.all });
      toast.success('Анализ расписания выполнен');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка оптимизации'));
    },
  });
}

// ==================== Auto-Pilot Hooks ====================

/**
 * Сгенерировать расписание в режиме автопилота
 */
export function useGenerateAutoPilotSchedule() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: AutoPilotRequest) =>
      scheduleAIApi.generateAutoPilotSchedule(request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'slots'] });
      queryClient.invalidateQueries({ queryKey: scheduleAIQueryKeys.all });
      toast.success(
        `Расписание сгенерировано: создано ${data.slots_created} слотов`
      );
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка генерации расписания'));
    },
  });
}

/**
 * Предпросмотр расписания автопилота без применения
 */
export function usePreviewAutoPilotSchedule() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: AutoPilotRequest) =>
      scheduleAIApi.previewAutoPilotSchedule(request),
    onSuccess: () => {
      toast.success('Предпросмотр создан');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка предпросмотра'));
    },
  });
}

// ==================== Peak Hours Hooks ====================

/**
 * Получить анализ пиковых часов
 */
export function usePeakHours(
  channelId: string,
  period: string = '30d',
  enabled: boolean = true
) {
  return useQuery({
    queryKey: scheduleAIQueryKeys.peakHours(channelId, period),
    queryFn: () => scheduleAIApi.getPeakHours(channelId, period),
    enabled: !!channelId && enabled,
    staleTime: 60 * 60 * 1000, // 1 час
  });
}

// ==================== Conflict Detection & Resolution Hooks ====================

/**
 * Обнаружить конфликты в расписании
 */
export function useDetectConflicts() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: ConflictDetectionRequest) =>
      scheduleAIApi.detectConflicts(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleAIQueryKeys.conflicts() });
      toast.success('Анализ конфликтов выполнен');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка обнаружения конфликтов'));
    },
  });
}

/**
 * Разрешить конфликты в расписании
 */
export function useResolveConflicts() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: ConflictDetectionRequest) =>
      scheduleAIApi.resolveConflicts(request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'slots'] });
      queryClient.invalidateQueries({ queryKey: scheduleAIQueryKeys.all });
      toast.success(
        `Конфликты разрешены: применено ${data.resolutions_applied} решений`
      );
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка разрешения конфликтов'));
    },
  });
}

// ==================== Gap Detection Hooks ====================

/**
 * Обнаружить пробелы в расписании
 */
export function useDetectGaps() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (request: GapDetectionRequest) =>
      scheduleAIApi.detectGaps(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleAIQueryKeys.gaps() });
      toast.success('Анализ пробелов выполнен');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка обнаружения пробелов'));
    },
  });
}
