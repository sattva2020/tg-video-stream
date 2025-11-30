/**
 * React Query hooks для Users API с пагинацией
 */
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { queryKeys } from '../lib/queryClient';
import { adminApi, User, UsersListParams } from '../api/admin';
import { useToast } from './useToast';
import { useState, useCallback } from 'react';

/**
 * Hook для получения списка пользователей с пагинацией
 */
export function useUsers(params?: UsersListParams) {
  return useQuery({
    queryKey: queryKeys.users.list(params || {}),
    queryFn: () => adminApi.listUsers(params),
    staleTime: 60 * 1000, // 1 минута
    placeholderData: keepPreviousData, // Сохраняем предыдущие данные при смене страницы
  });
}

/**
 * Hook для пагинированного списка пользователей с управлением состоянием
 */
export function usePaginatedUsers(initialParams?: Partial<UsersListParams>) {
  const [params, setParams] = useState<UsersListParams>({
    page: 1,
    page_size: 10,
    ...initialParams,
  });

  const query = useQuery({
    queryKey: queryKeys.users.list(params),
    queryFn: () => adminApi.listUsers(params),
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
  });

  const goToPage = useCallback((page: number) => {
    setParams(prev => ({ ...prev, page }));
  }, []);

  const nextPage = useCallback(() => {
    if (query.data && params.page && params.page < query.data.total_pages) {
      setParams(prev => ({ ...prev, page: (prev.page || 1) + 1 }));
    }
  }, [query.data, params.page]);

  const prevPage = useCallback(() => {
    if (params.page && params.page > 1) {
      setParams(prev => ({ ...prev, page: (prev.page || 1) - 1 }));
    }
  }, [params.page]);

  const setPageSize = useCallback((page_size: number) => {
    setParams(prev => ({ ...prev, page_size, page: 1 }));
  }, []);

  const setStatus = useCallback((status?: string) => {
    setParams(prev => ({ ...prev, status, page: 1 }));
  }, []);

  const setSearch = useCallback((search?: string) => {
    setParams(prev => ({ ...prev, search, page: 1 }));
  }, []);

  return {
    ...query,
    params,
    goToPage,
    nextPage,
    prevPage,
    setPageSize,
    setStatus,
    setSearch,
    pagination: query.data ? {
      page: query.data.page,
      pageSize: query.data.page_size,
      total: query.data.total,
      totalPages: query.data.total_pages,
      hasNext: query.data.page < query.data.total_pages,
      hasPrev: query.data.page > 1,
    } : null,
  };
}

/**
 * Hook для получения pending пользователей
 */
export function usePendingUsers() {
  return useQuery({
    queryKey: queryKeys.users.pending(),
    queryFn: () => adminApi.listUsers({ status: 'pending' }),
    staleTime: 30 * 1000, // 30 секунд — важно видеть новых
    refetchInterval: 60 * 1000, // Автообновление каждую минуту
  });
}

/**
 * Hook для одобрения пользователя
 */
export function useApproveUser() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (userId: string) => adminApi.approveUser(userId),
    
    onError: (error: Error) => {
      toast.error(`Не удалось одобрить пользователя: ${error.message}`);
    },
    
    onSuccess: () => {
      toast.success('Пользователь одобрен');
    },
    
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

/**
 * Hook для отклонения пользователя
 */
export function useRejectUser() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (userId: string) => adminApi.rejectUser(userId),
    
    onError: (error: Error) => {
      toast.error(`Не удалось отклонить заявку: ${error.message}`);
    },
    
    onSuccess: () => {
      toast.success('Заявка отклонена');
    },
    
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

/**
 * Hook для статистики пользователей
 */
export function useUserStats() {
  const { data, isLoading } = useUsers({ page: 1, page_size: 1000 });
  
  const users = data?.items || [];
  
  const stats = {
    total: data?.total || 0,
    pending: users.filter((u: User) => u.status === 'pending').length,
    approved: users.filter((u: User) => u.status === 'approved').length,
    rejected: users.filter((u: User) => u.status === 'rejected').length,
  };
  
  return { stats, isLoading };
}
