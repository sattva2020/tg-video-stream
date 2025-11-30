/**
 * React Query hooks для Playlist API
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../lib/queryClient';
import * as playlistService from '../services/playlist';
import type { PlaylistItem } from '../services/playlist';
import { useToast } from './useToast';

/**
 * Hook для получения списка плейлиста
 */
export function usePlaylist(channelId?: string) {
  return useQuery({
    queryKey: queryKeys.playlist.list(channelId),
    queryFn: () => playlistService.getPlaylist(channelId),
    staleTime: 30 * 1000, // 30 секунд — плейлист часто меняется
    refetchInterval: 30 * 1000, // Автообновление каждые 30 сек
  });
}

/**
 * Hook для добавления трека в плейлист
 */
export function useAddPlaylistItem() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: { url: string; title?: string; type?: string }) => 
      playlistService.addPlaylistItem(data),
    
    onSuccess: (newItem) => {
      // Инвалидируем кэш плейлиста
      queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all });
      toast.success(`Трек "${newItem.title || newItem.url}" добавлен`);
    },
    
    onError: (error: Error) => {
      toast.error(`Не удалось добавить трек: ${error.message}`);
    },
  });
}

/**
 * Hook для удаления трека из плейлиста
 */
export function useDeletePlaylistItem() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (itemId: string) => playlistService.deletePlaylistItem(itemId),
    
    // Optimistic update
    onMutate: async (itemId) => {
      // Отменяем текущие запросы
      await queryClient.cancelQueries({ queryKey: queryKeys.playlist.all });
      
      // Сохраняем предыдущее состояние
      const previousPlaylists = queryClient.getQueriesData({ queryKey: queryKeys.playlist.all });
      
      // Оптимистично удаляем из кэша
      queryClient.setQueriesData(
        { queryKey: queryKeys.playlist.all },
        (old: PlaylistItem[] | undefined) => 
          old?.filter(item => item.id !== itemId) ?? []
      );
      
      return { previousPlaylists };
    },
    
    onError: (error: Error, _itemId, context) => {
      // Восстанавливаем при ошибке
      if (context?.previousPlaylists) {
        context.previousPlaylists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
      toast.error(`Не удалось удалить трек: ${error.message}`);
    },
    
    onSuccess: () => {
      toast.success('Трек удалён');
    },
    
    onSettled: () => {
      // Перезагружаем данные в любом случае
      queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all });
    },
  });
}

/**
 * Hook для импорта YouTube плейлиста
 */
export function useImportPlaylist() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: async (data: { url: string; channelId?: string }) => {
      const response = await fetch('/api/playlist/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error('Не удалось импортировать плейлист');
      }
      
      return response.json();
    },
    
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message || 'Импорт плейлиста запущен');
        // Начинаем частое обновление пока идёт импорт
        queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all });
      } else {
        toast.error(result.message || 'Ошибка импорта');
      }
    },
    
    onError: (error: Error) => {
      toast.error(`Ошибка импорта: ${error.message}`);
    },
  });
}

/**
 * Hook для обновления метаданных трека
 */
export function useRefreshMetadata() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: async (itemId: string) => {
      const response = await fetch(`/api/playlist/${itemId}/refresh-metadata`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Не удалось обновить метаданные');
      }
      
      return response.json();
    },
    
    onSuccess: () => {
      toast.info('Обновление метаданных запущено');
      // Инвалидируем через небольшую задержку
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all });
      }, 2000);
    },
    
    onError: (error: Error) => {
      toast.error(`Ошибка: ${error.message}`);
    },
  });
}
