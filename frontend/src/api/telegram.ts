import { client } from './client';

export interface TelegramAccount {
  id: string;
  phone: string;
  first_name?: string;
  username?: string;
  photo_url?: string;
}

export const telegramApi = {
  listAccounts: async () => {
    const response = await client.get<TelegramAccount[]>('/api/auth/telegram/accounts');
    return response.data;
  },
};
