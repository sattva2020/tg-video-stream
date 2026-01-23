import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  alertsApi,
  AlertRuleCreate,
  AlertRuleUpdate,
  AlertInstanceFilters,
  AlertGroupFilters,
  ResolveGroupRequest,
} from '../api/alerts';
import { alertQueryKeys } from '../lib/queryClient';
import { useToast } from './useToast';

// ============================================================================
// Alert Rules Hooks
// ============================================================================

export const useAlertRules = (filters?: { enabled?: boolean; alert_type?: string; severity?: string }) =>
  useQuery({
    queryKey: alertQueryKeys.rules(),
    queryFn: () => alertsApi.listRules(filters),
  });

export const useAlertRule = (id: string) =>
  useQuery({
    queryKey: alertQueryKeys.rule(id),
    queryFn: () => alertsApi.getRule(id),
    enabled: !!id,
  });

export const useCreateAlertRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (data: AlertRuleCreate) => alertsApi.createRule(data),
    onSuccess: () => {
      toast.success('Правило создано');
      queryClient.invalidateQueries({ queryKey: alertQueryKeys.rules() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось создать правило');
    },
  });
};

export const useUpdateAlertRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlertRuleUpdate }) =>
      alertsApi.updateRule(id, data),
    onSuccess: () => {
      toast.success('Правило обновлено');
      queryClient.invalidateQueries({ queryKey: alertQueryKeys.rules() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось обновить правило');
    },
  });
};

export const useDeleteAlertRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (id: string) => alertsApi.deleteRule(id),
    onSuccess: () => {
      toast.success('Правило удалено');
      queryClient.invalidateQueries({ queryKey: alertQueryKeys.rules() });
    },
    onError: () => {
      toast.error('Не удалось удалить правило');
    },
  });
};

// ============================================================================
// Alert Instances Hooks
// ============================================================================

export const useAlertInstances = (filters?: AlertInstanceFilters) =>
  useQuery({
    queryKey: alertQueryKeys.instances(filters),
    queryFn: () => alertsApi.listInstances(filters),
  });

export const useAlertInstance = (id: string) =>
  useQuery({
    queryKey: alertQueryKeys.instance(id),
    queryFn: () => alertsApi.getInstance(id),
    enabled: !!id,
  });

// ============================================================================
// Alert Groups Hooks
// ============================================================================

export const useAlertGroups = (filters?: AlertGroupFilters) =>
  useQuery({
    queryKey: alertQueryKeys.groups(filters),
    queryFn: () => alertsApi.listGroups(filters),
  });

export const useAlertGroup = (id: string) =>
  useQuery({
    queryKey: alertQueryKeys.group(id),
    queryFn: () => alertsApi.getGroup(id),
    enabled: !!id,
  });

export const useResolveAlertGroup = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: ResolveGroupRequest }) =>
      alertsApi.resolveGroup(id, request),
    onSuccess: () => {
      toast.success('Группа разрешена');
      queryClient.invalidateQueries({ queryKey: alertQueryKeys.groups() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось разрешить группу');
    },
  });
};

// ============================================================================
// Alert Statistics Hooks
// ============================================================================

export const useAlertStatistics = () =>
  useQuery({
    queryKey: alertQueryKeys.statistics(),
    queryFn: () => alertsApi.getStatistics(),
  });

// ============================================================================
// Alert Test Hooks
// ============================================================================

export const useTestAlert = () => {
  const toast = useToast();
  return useMutation({
    mutationFn: (request: { alert_type: string; metric: string; value: number; severity?: string; context?: Record<string, unknown> }) =>
      alertsApi.testAlert(request),
    onSuccess: (data) => {
      toast.success(`Тестовый алерт поставлен в очередь (${data.instance_id || data.event_id})`);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось выполнить тест алерта');
    },
  });
};
