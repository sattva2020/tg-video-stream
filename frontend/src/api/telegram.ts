import { client } from './client';

export interface TelegramAccount {
  id: string;
  phone: string;
  first_name?: string;
  username?: string;
  photo_url?: string;
}

export interface TelegramDialog {
  id: number;
  title: string;
  type: 'channel' | 'supergroup' | 'group';
  username?: string;
  members_count?: number;
  photo_url?: string;
  is_creator: boolean;
  is_admin: boolean;
}

export const telegramApi = {
  listAccounts: async () => {
    const response = await client.get<TelegramAccount[]>('/api/auth/telegram/accounts');
    return response.data;
  },
  
  /**
   * Получить список каналов и групп для указанного аккаунта
   * @param accountId - ID аккаунта
   * @param filterType - 'channels' | 'groups' | 'all'
   */
  getDialogs: async (accountId: string, filterType?: 'channels' | 'groups' | 'all') => {
    const params = filterType ? { filter_type: filterType } : {};
    const response = await client.get<TelegramDialog[]>(
      `/api/auth/telegram/accounts/${accountId}/dialogs`,
      { params }
    );
    return response.data;
  },
};
