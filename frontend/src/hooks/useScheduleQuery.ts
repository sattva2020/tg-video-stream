/**
 * React Query хуки для работы с расписанием и плейлистами.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scheduleApi, ScheduleSlotCreate, ScheduleSlotUpdate, ScheduleTemplateCreate, PlaylistCreate, PlaylistUpdate, BulkCopyRequest, ApplyTemplateRequest } from '../api/schedule';
import { useToast } from './useToast';

// ==================== Query Keys ====================

export const scheduleQueryKeys = {
  all: ['schedule'] as const,
  slots: (channelId: string, startDate: string, endDate: string) => 
    [...scheduleQueryKeys.all, 'slots', channelId, startDate, endDate] as const,
  calendar: (channelId: string, year: number, month: number) => 
    [...scheduleQueryKeys.all, 'calendar', channelId, year, month] as const,
  templates: (channelId?: string) => 
    [...scheduleQueryKeys.all, 'templates', channelId] as const,
  playlists: (channelId?: string) => 
    [...scheduleQueryKeys.all, 'playlists', channelId] as const,
};

// ==================== Schedule Slots Hooks ====================

/**
 * Получить слоты расписания за период
 */
export function useScheduleSlots(channelId: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: scheduleQueryKeys.slots(channelId, startDate, endDate),
    queryFn: () => scheduleApi.getSlots(channelId, startDate, endDate),
    enabled: !!channelId && !!startDate && !!endDate,
    staleTime: 30 * 1000, // 30 секунд
  });
}

/**
 * Получить календарное представление на месяц
 */
export function useScheduleCalendar(channelId: string, year: number, month: number) {
  return useQuery({
    queryKey: scheduleQueryKeys.calendar(channelId, year, month),
    queryFn: () => scheduleApi.getCalendar(channelId, year, month),
    enabled: !!channelId && year > 0 && month > 0,
    staleTime: 60 * 1000, // 1 минута
  });
}

/**
 * Создать слот расписания
 */
export function useCreateSlot() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: ScheduleSlotCreate) => scheduleApi.createSlot(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.all });
      toast.success('Слот добавлен в расписание');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Обновить слот расписания
 */
export function useUpdateSlot() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ slotId, data }: { slotId: string; data: ScheduleSlotUpdate }) => 
      scheduleApi.updateSlot(slotId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.all });
      toast.success('Слот обновлён');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Удалить слот расписания
 */
export function useDeleteSlot() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (slotId: string) => scheduleApi.deleteSlot(slotId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.all });
      toast.success('Слот удалён');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Копировать расписание на другие даты
 */
export function useCopySchedule() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: BulkCopyRequest) => scheduleApi.copySchedule(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.all });
      toast.success(`Скопировано ${result.created} слотов${result.skipped > 0 ? `, пропущено ${result.skipped} (конфликты)` : ''}`);
    },
    onError: (error: Error) => {
      toast.error(`Ошибка копирования: ${error.message}`);
    },
  });
}

// ==================== Templates Hooks ====================

/**
 * Получить список шаблонов
 */
export function useScheduleTemplates(channelId?: string) {
  return useQuery({
    queryKey: scheduleQueryKeys.templates(channelId),
    queryFn: () => scheduleApi.getTemplates(channelId),
    staleTime: 5 * 60 * 1000, // 5 минут
  });
}

/**
 * Создать шаблон расписания
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: ScheduleTemplateCreate) => scheduleApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.templates() });
      toast.success('Шаблон создан');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Применить шаблон к датам
 */
export function useApplyTemplate() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: ApplyTemplateRequest) => scheduleApi.applyTemplate(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.all });
      toast.success(`Шаблон применён: создано ${result.created} слотов`);
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Удалить шаблон
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (templateId: string) => scheduleApi.deleteTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.templates() });
      toast.success('Шаблон удалён');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

// ==================== Playlists Hooks ====================

/**
 * Получить список плейлистов
 */
export function usePlaylists(channelId?: string) {
  return useQuery({
    queryKey: scheduleQueryKeys.playlists(channelId),
    queryFn: () => scheduleApi.getPlaylists(channelId),
    staleTime: 60 * 1000, // 1 минута
  });
}

/**
 * Создать плейлист
 */
export function useCreatePlaylist() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: PlaylistCreate) => scheduleApi.createPlaylist(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.playlists() });
      toast.success('Плейлист создан');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Обновить плейлист
 */
export function useUpdatePlaylist() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ playlistId, data }: { playlistId: string; data: PlaylistUpdate }) => 
      scheduleApi.updatePlaylist(playlistId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.playlists() });
      toast.success('Плейлист обновлён');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}

/**
 * Удалить плейлист
 */
export function useDeletePlaylist() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (playlistId: string) => scheduleApi.deletePlaylist(playlistId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleQueryKeys.playlists() });
      toast.success('Плейлист удалён');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}
