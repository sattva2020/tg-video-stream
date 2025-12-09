/**
 * React Query хуки для работы с расписанием и плейлистами.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { scheduleApi, ScheduleSlotCreate, ScheduleSlotUpdate, ScheduleTemplateCreate, PlaylistCreate, PlaylistUpdate, PlaylistGroupCreate, PlaylistGroupUpdate, BulkCopyRequest, ApplyTemplateRequest } from '../api/schedule';
import { useToast } from './useToast';

// ==================== Error Handling ====================

interface ApiErrorResponse {
  detail?: string;
}

/**
 * Преобразует ошибку API в понятное сообщение на русском
 * @param error - Ошибка от API или JavaScript
 * @param prefix - Опциональный префикс для сообщения (например, "Ошибка копирования")
 */
function getErrorMessage(error: unknown, prefix?: string): string {
  let message = 'Произошла неизвестная ошибка';
  
  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const detail = (error.response?.data as ApiErrorResponse)?.detail;
    
    // Специфичные ошибки по статус-кодам
    if (status === 409) {
      if (detail?.includes('overlaps')) {
        message = 'Слот на это время уже существует. Выберите другое время.';
      } else if (detail?.includes('in use')) {
        message = 'Плейлист используется и не может быть удалён.';
      } else {
        message = 'Конфликт данных. Попробуйте обновить страницу.';
      }
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
      // Если есть detail от сервера
      message = detail;
    }
  } else if (error instanceof Error) {
    message = error.message;
  }
  
  return prefix ? `${prefix}: ${message}` : message;
}

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
  groups: (channelId?: string) => 
    [...scheduleQueryKeys.all, 'groups', channelId] as const,
  groupsWithPlaylists: (channelId?: string) => 
    [...scheduleQueryKeys.all, 'groupsWithPlaylists', channelId] as const,
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Ошибка копирования'));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
      queryClient.invalidateQueries({ queryKey: ['schedule', 'playlists'] });
      toast.success('Плейлист создан');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
      queryClient.invalidateQueries({ queryKey: ['schedule', 'playlists'] });
      toast.success('Плейлист обновлён');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
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
      queryClient.invalidateQueries({ queryKey: ['schedule', 'playlists'] });
      queryClient.invalidateQueries({ queryKey: ['schedule', 'groups'] });
      toast.success('Плейлист удалён');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Переместить плейлист в группу
 */
export function useMovePlaylistToGroup() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ playlistId, groupId, position }: { playlistId: string; groupId?: string; position?: number }) => 
      scheduleApi.movePlaylistToGroup(playlistId, groupId, position),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'playlists'] });
      queryClient.invalidateQueries({ queryKey: ['schedule', 'groups'] });
      toast.success('Плейлист перемещён');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

// ==================== Playlist Groups Hooks ====================

/**
 * Получить список групп плейлистов
 */
export function usePlaylistGroups(channelId?: string) {
  return useQuery({
    queryKey: scheduleQueryKeys.groups(channelId),
    queryFn: () => scheduleApi.getGroups(channelId),
    staleTime: 60 * 1000,
  });
}

/**
 * Получить группы с вложенными плейлистами
 */
export function usePlaylistGroupsWithPlaylists(channelId?: string) {
  return useQuery({
    queryKey: scheduleQueryKeys.groupsWithPlaylists(channelId),
    queryFn: () => scheduleApi.getGroupsWithPlaylists(channelId),
    staleTime: 60 * 1000,
  });
}

/**
 * Создать группу плейлистов
 */
export function useCreatePlaylistGroup() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: PlaylistGroupCreate) => scheduleApi.createGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'groups'] });
      toast.success('Группа создана');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Обновить группу плейлистов
 */
export function useUpdatePlaylistGroup() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: PlaylistGroupUpdate }) => 
      scheduleApi.updateGroup(groupId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'groups'] });
      toast.success('Группа обновлена');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Удалить группу плейлистов
 */
export function useDeletePlaylistGroup() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (groupId: string) => scheduleApi.deleteGroup(groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', 'groups'] });
      queryClient.invalidateQueries({ queryKey: ['schedule', 'playlists'] });
      toast.success('Группа удалена');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}
