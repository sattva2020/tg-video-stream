/**
 * React Query hooks для Channels API
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../lib/queryClient';
import { channelsApi, Channel, CreateChannelData } from '../api/channels';
import { telegramApi } from '../api/telegram';
import { useToast } from './useToast';

/**
 * Hook для получения списка каналов
 */
export function useChannels() {
  return useQuery({
    queryKey: queryKeys.channels.list(),
    queryFn: channelsApi.list,
    staleTime: 60 * 1000, // 1 минута
  });
}

/**
 * Hook для получения Telegram аккаунтов
 */
export function useTelegramAccounts() {
  return useQuery({
    queryKey: queryKeys.telegram.accounts(),
    queryFn: telegramApi.listAccounts,
    staleTime: 5 * 60 * 1000, // 5 минут — редко меняется
  });
}

/**
 * Hook для создания канала
 */
export function useCreateChannel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (data: CreateChannelData) => channelsApi.create(data),
    
    onSuccess: (newChannel) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
      toast.success(`Канал "${newChannel.name}" создан`);
    },
    
    onError: (error: Error) => {
      toast.error(`Не удалось создать канал: ${error.message}`);
    },
  });
}

/**
 * Hook для запуска канала
 */
export function useStartChannel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (channelId: string) => channelsApi.start(channelId),
    
    onMutate: async (channelId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.channels.list() });
      
      const previousChannels = queryClient.getQueryData<Channel[]>(queryKeys.channels.list());
      
      if (previousChannels) {
        queryClient.setQueryData(
          queryKeys.channels.list(),
          previousChannels.map(ch => 
            ch.id === channelId ? { ...ch, status: 'starting' } : ch
          )
        );
      }
      
      return { previousChannels };
    },
    
    onError: (error: Error, _channelId, context) => {
      if (context?.previousChannels) {
        queryClient.setQueryData(queryKeys.channels.list(), context.previousChannels);
      }
      toast.error(`Не удалось запустить канал: ${error.message}`);
    },
    
    onSuccess: (_data, channelId) => {
      const channels = queryClient.getQueryData<Channel[]>(queryKeys.channels.list());
      const channel = channels?.find(ch => ch.id === channelId);
      toast.success(`Трансляция "${channel?.name || 'Канал'}" запущена`);
    },
    
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
    },
  });
}

/**
 * Hook для остановки канала
 */
export function useStopChannel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (channelId: string) => channelsApi.stop(channelId),
    
    onMutate: async (channelId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.channels.list() });
      
      const previousChannels = queryClient.getQueryData<Channel[]>(queryKeys.channels.list());
      
      if (previousChannels) {
        queryClient.setQueryData(
          queryKeys.channels.list(),
          previousChannels.map(ch => 
            ch.id === channelId ? { ...ch, status: 'stopping' } : ch
          )
        );
      }
      
      return { previousChannels };
    },
    
    onError: (error: Error, _channelId, context) => {
      if (context?.previousChannels) {
        queryClient.setQueryData(queryKeys.channels.list(), context.previousChannels);
      }
      toast.error(`Не удалось остановить канал: ${error.message}`);
    },
    
    onSuccess: (_data, channelId) => {
      const channels = queryClient.getQueryData<Channel[]>(queryKeys.channels.list());
      const channel = channels?.find(ch => ch.id === channelId);
      toast.success(`Трансляция "${channel?.name || 'Канал'}" остановлена`);
    },
    
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
    },
  });
}

/**
 * Hook для удаления канала
 */
export function useDeleteChannel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (channelId: string) => channelsApi.delete(channelId),
    
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
      toast.success('Канал удален');
    },
    
    onError: (error: Error) => {
      toast.error(`Не удалось удалить канал: ${error.message}`);
    },
  });
}

/**
 * Hook для обновления канала
 */
export function useUpdateChannel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CreateChannelData }) => 
      channelsApi.update(id, data),
    
    onSuccess: (updatedChannel) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
      toast.success(`Канал "${updatedChannel.name}" обновлен`);
    },
    
    onError: (error: Error) => {
      toast.error(`Не удалось обновить канал: ${error.message}`);
    },
  });
}

/**
 * Hook для загрузки заглушки
 */
export function useUploadPlaceholder() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ channelId, file }: { channelId: string; file: File }) => 
      channelsApi.uploadPlaceholder(channelId, file),
    
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
      toast.success('Заглушка обновлена');
    },
    
    onError: (error: Error) => {
      toast.error(`Не удалось загрузить заглушку: ${error.message}`);
    },
  });
}

/**
 * Hook для статуса стрима
 */
export function useStreamStatus() {
  return useQuery({
    queryKey: queryKeys.stream.status(),
    queryFn: async () => {
      const response = await fetch('/api/admin/stream/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (!response.ok) throw new Error('Failed to fetch stream status');
      return response.json();
    },
    staleTime: 10 * 1000, // 10 секунд
    refetchInterval: 15 * 1000, // Автообновление каждые 15 сек
  });
}
