/**
 * React Query hooks для Telegram Sessions API
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../lib/queryClient';
import { telegramApi, TelegramSession } from '../api/telegram';
import { useToast } from './useToast';

/**
 * Hook для получения списка всех Telegram сессий
 */
export function useSessions(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['telegram', 'sessions'],
    queryFn: () => telegramApi.listSessions(),
    staleTime: 30 * 1000, // 30 секунд
    refetchInterval: 30 * 1000, // Автообновление каждые 30 секунд
    enabled: options?.enabled,
  });
}

/**
 * Hook для получения статистики сессий
 */
export function useSessionStats(options?: { enabled?: boolean }) {
  const { data: sessions, isLoading } = useSessions(options);

  const stats = {
    total: sessions?.length || 0,
    healthy: sessions?.filter(s => {
      const status = s.health_status || s.session_health_status;
      return status === 'healthy' || status === 'HEALTHY';
    }).length || 0,
    unhealthy: sessions?.filter(s => {
      const status = s.health_status || s.session_health_status;
      return status !== 'healthy' && status !== 'HEALTHY' && status !== 'unknown';
    }).length || 0,
    expiring: sessions?.filter(s => {
      const status = s.health_status || s.session_health_status;
      return status === 'expiring' || status === 'EXPIRING' || status === 'expiring_soon';
    }).length || 0,
    expired: sessions?.filter(s => {
      const status = s.health_status || s.session_health_status;
      return status === 'expired' || status === 'EXPIRED';
    }).length || 0,
    needs2FA: sessions?.filter(s => {
      const status = s.health_status || s.session_health_status;
      return status === 'needs_2fa' || status === 'NEEDS_2FA';
    }).length || 0,
    autoRefreshEnabled: sessions?.filter(s => s.auto_refresh_enabled).length || 0,
  };

  return { stats, isLoading, sessions: sessions || [] };
}

/**
 * Hook для обновления сессии
 */
export function useRefreshSession() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (accountId: string) => telegramApi.refreshSession(accountId),

    onError: (error: Error) => {
      toast.error(`Не удалось обновить сессию: ${error.message}`);
    },

    onSuccess: () => {
      toast.success('Сессия обновлена');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram', 'sessions'] });
    },
  });
}

/**
 * Hook для массового обновления сессий
 */
export function useRefreshAllSessions() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const refreshSession = useRefreshSession();

  const refreshAll = async (sessions: TelegramSession[]) => {
    const results = {
      success: 0,
      failed: 0,
    };

    // Обновляем только активные сессии
    const activeSessions = sessions.filter(s => s.is_active);

    for (const session of activeSessions) {
      try {
        await telegramApi.refreshSession(session.id);
        results.success++;
      } catch (error) {
        results.failed++;
      }
    }

    if (results.success > 0) {
      toast.success(`Обновлено ${results.success} сессий`);
    }
    if (results.failed > 0) {
      toast.error(`Не удалось обновить ${results.failed} сессий`);
    }

    queryClient.invalidateQueries({ queryKey: ['telegram', 'sessions'] });

    return results;
  };

  return refreshAll;
}

/**
 * Hook для создания бэкапа сессии
 */
export function useBackupSession() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (accountId: string) => telegramApi.backupSession(accountId),

    onError: (error: Error) => {
      toast.error(`Не удалось создать бэкап: ${error.message}`);
    },

    onSuccess: () => {
      toast.success('Бэкап создан');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram', 'sessions'] });
    },
  });
}

/**
 * Hook для массового бэкапа сессий
 */
export function useBackupAllSessions() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const backupSession = useBackupSession();

  const backupAll = async (sessions: TelegramSession[]) => {
    const results = {
      success: 0,
      failed: 0,
    };

    // Бэкапим только активные сессии
    const activeSessions = sessions.filter(s => s.is_active);

    for (const session of activeSessions) {
      try {
        await telegramApi.backupSession(session.id);
        results.success++;
      } catch (error) {
        results.failed++;
      }
    }

    if (results.success > 0) {
      toast.success(`Создано бэкапов: ${results.success}`);
    }
    if (results.failed > 0) {
      toast.error(`Не удалось создать бэкап: ${results.failed}`);
    }

    queryClient.invalidateQueries({ queryKey: ['telegram', 'sessions'] });

    return results;
  };

  return backupAll;
}
