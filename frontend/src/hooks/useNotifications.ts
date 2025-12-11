import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  notificationsApi,
  NotificationChannelCreate,
  NotificationChannelUpdate,
  NotificationTemplateCreate,
  NotificationTemplateUpdate,
  NotificationRecipientCreate,
  NotificationRecipientUpdate,
  NotificationRuleCreate,
  NotificationRuleUpdate,
  RuleTestRequest,
  ChannelTestRequest,
  DeliveryLogFilters,
} from '../api/notifications';
import { notificationQueryKeys } from '../lib/queryClient';
import { useToast } from './useToast';

export const useNotificationChannels = () =>
  useQuery({
    queryKey: notificationQueryKeys.channels(),
    queryFn: notificationsApi.listChannels,
  });

export const useCreateNotificationChannel = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (data: NotificationChannelCreate) => notificationsApi.createChannel(data),
    onSuccess: () => {
      toast.success('Канал создан');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.channels() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось создать канал');
    },
  });
};

export const useUpdateNotificationChannel = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: NotificationChannelUpdate }) =>
      notificationsApi.updateChannel(id, data),
    onSuccess: () => {
      toast.success('Канал обновлен');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.channels() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось обновить канал');
    },
  });
};

export const useDeleteNotificationChannel = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deleteChannel(id),
    onSuccess: () => {
      toast.success('Канал удален');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.channels() });
    },
    onError: () => {
      toast.error('Не удалось удалить канал');
    },
  });
};

export const useTestNotificationChannel = () => {
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ChannelTestRequest }) =>
      notificationsApi.testChannel(id, payload),
    onSuccess: (data) => {
      toast.success(`Тестовая отправка поставлена в очередь (${data.event_id})`);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось выполнить тестовую отправку');
    },
  });
};

export const useNotificationTemplates = () =>
  useQuery({
    queryKey: notificationQueryKeys.templates(),
    queryFn: notificationsApi.listTemplates,
  });

export const useCreateNotificationTemplate = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (data: NotificationTemplateCreate) => notificationsApi.createTemplate(data),
    onSuccess: () => {
      toast.success('Шаблон создан');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.templates() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось создать шаблон');
    },
  });
};

export const useUpdateNotificationTemplate = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: NotificationTemplateUpdate }) =>
      notificationsApi.updateTemplate(id, data),
    onSuccess: () => {
      toast.success('Шаблон обновлен');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.templates() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось обновить шаблон');
    },
  });
};

export const useDeleteNotificationTemplate = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deleteTemplate(id),
    onSuccess: () => {
      toast.success('Шаблон удален');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.templates() });
    },
    onError: () => {
      toast.error('Не удалось удалить шаблон');
    },
  });
};

export const useNotificationRecipients = () =>
  useQuery({
    queryKey: notificationQueryKeys.recipients(),
    queryFn: notificationsApi.listRecipients,
  });

export const useCreateNotificationRecipient = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (data: NotificationRecipientCreate) => notificationsApi.createRecipient(data),
    onSuccess: () => {
      toast.success('Получатель создан');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.recipients() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось создать получателя');
    },
  });
};

export const useUpdateNotificationRecipient = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: NotificationRecipientUpdate }) =>
      notificationsApi.updateRecipient(id, data),
    onSuccess: () => {
      toast.success('Получатель обновлен');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.recipients() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось обновить получателя');
    },
  });
};

export const useDeleteNotificationRecipient = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deleteRecipient(id),
    onSuccess: () => {
      toast.success('Получатель удален');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.recipients() });
    },
    onError: () => {
      toast.error('Не удалось удалить получателя');
    },
  });
};

export const useNotificationRules = () =>
  useQuery({
    queryKey: notificationQueryKeys.rules(),
    queryFn: notificationsApi.listRules,
  });

export const useCreateNotificationRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (data: NotificationRuleCreate) => notificationsApi.createRule(data),
    onSuccess: () => {
      toast.success('Правило создано');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.rules() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось создать правило');
    },
  });
};

export const useUpdateNotificationRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: NotificationRuleUpdate }) =>
      notificationsApi.updateRule(id, data),
    onSuccess: () => {
      toast.success('Правило обновлено');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.rules() });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось обновить правило');
    },
  });
};

export const useDeleteNotificationRule = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deleteRule(id),
    onSuccess: () => {
      toast.success('Правило удалено');
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.rules() });
    },
    onError: () => {
      toast.error('Не удалось удалить правило');
    },
  });
};

export const useTestNotificationRule = () => {
  const toast = useToast();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: RuleTestRequest }) =>
      notificationsApi.testRule(id, payload),
    onSuccess: (data) => {
      toast.success(`Тестовое событие поставлено в очередь (${data.event_id})`);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Не удалось выполнить тест правила');
    },
  });
};

export const useNotificationLogs = (filters?: DeliveryLogFilters) =>
  useQuery({
    queryKey: notificationQueryKeys.logs(filters),
    queryFn: () => notificationsApi.listLogs(filters),
  });
