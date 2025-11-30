/**
 * React Query Configuration
 * 
 * Централизованная конфигурация для data fetching и caching.
 */
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Время жизни данных в кэше (5 минут)
      staleTime: 5 * 60 * 1000,
      
      // Время хранения неактивных данных (30 минут)
      gcTime: 30 * 60 * 1000,
      
      // Повторные попытки при ошибке
      retry: (failureCount, error) => {
        // Не повторять для 4xx ошибок (кроме 429)
        if (error instanceof Error && 'status' in error) {
          const status = (error as any).status;
          if (status >= 400 && status < 500 && status !== 429) {
            return false;
          }
        }
        return failureCount < 3;
      },
      
      // Задержка между повторами
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      
      // Refetch при фокусе окна
      refetchOnWindowFocus: true,
      
      // Refetch при восстановлении сети
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry для mutations
      retry: 1,
      retryDelay: 1000,
    },
  },
});

/**
 * Query Keys — централизованные ключи для кэширования
 * 
 * Использование:
 * - useQuery({ queryKey: queryKeys.playlist.all })
 * - queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all })
 */
export const queryKeys = {
  // Auth
  auth: {
    all: ['auth'] as const,
    user: () => [...queryKeys.auth.all, 'user'] as const,
  },
  
  // Users
  users: {
    all: ['users'] as const,
    list: (filters?: { status?: string }) => [...queryKeys.users.all, 'list', filters] as const,
    detail: (id: string) => [...queryKeys.users.all, 'detail', id] as const,
    pending: () => [...queryKeys.users.all, 'pending'] as const,
  },
  
  // Playlist
  playlist: {
    all: ['playlist'] as const,
    list: (channelId?: string) => [...queryKeys.playlist.all, 'list', channelId] as const,
    detail: (id: string) => [...queryKeys.playlist.all, 'detail', id] as const,
  },
  
  // Channels
  channels: {
    all: ['channels'] as const,
    list: () => [...queryKeys.channels.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.channels.all, 'detail', id] as const,
  },
  
  // Stream Status
  stream: {
    all: ['stream'] as const,
    status: () => [...queryKeys.stream.all, 'status'] as const,
  },
  
  // Telegram Accounts
  telegram: {
    all: ['telegram'] as const,
    accounts: () => [...queryKeys.telegram.all, 'accounts'] as const,
  },
} as const;

/**
 * Утилиты для инвалидации кэша
 */
export const invalidateQueries = {
  playlist: () => queryClient.invalidateQueries({ queryKey: queryKeys.playlist.all }),
  users: () => queryClient.invalidateQueries({ queryKey: queryKeys.users.all }),
  channels: () => queryClient.invalidateQueries({ queryKey: queryKeys.channels.all }),
  stream: () => queryClient.invalidateQueries({ queryKey: queryKeys.stream.all }),
  all: () => queryClient.invalidateQueries(),
};
