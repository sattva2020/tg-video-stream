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

// =============================================================================
// Session Management Types
// =============================================================================

export interface TelegramSession {
  id: string;
  user_id: string;
  phone: string;
  username?: string;
  first_name?: string;
  tg_user_id?: number;
  is_active: boolean;

  // Session health fields
  session_health_status?: string;
  last_health_check?: string;
  session_expires_at?: string;
  auto_refresh_enabled: boolean;
  refresh_before_expires_hours: number;
  last_refreshed_at?: string;
  refresh_error_message?: string;

  // Real-time health from monitor
  is_healthy?: boolean;
  health_status?: string;
  consecutive_failures?: number;
}

export interface SessionHealth {
  account_id: string;
  is_healthy: boolean;
  health_status: string;
  last_check: string;
  consecutive_failures: number;
  session_expires_at?: string;
  time_until_expiry_seconds?: number;
  last_failure_type?: string;
  last_error_message?: string;
}

export interface SessionConfig {
  account_id: string;
  auto_refresh_enabled: boolean;
  refresh_before_expires_hours: number;
  phone: string;
  username?: string;
}

export interface SessionRefreshResponse {
  success: boolean;
  message: string;
  session_expires_at?: string;
}

export interface SessionBackupResponse {
  success: boolean;
  message: string;
  backup_path?: string;
}

export interface TOTPSetupResponse {
  secret: string;
  otpauth_url: string;
}

export interface TOTPVerifyRequest {
  code: string;
}

export interface TOTPDisableRequest {
  code?: string;
}

export interface TOTPStatusResponse {
  status: 'enabled' | 'disabled';
  message: string;
}

export interface TestAlertResponse {
  success: boolean;
  message: string;
  event_id: string;
  tasks_enqueued: number;
}

export const telegramApi = {
  // -------------------------------------------------------------------------
  // Existing Telegram API methods
  // -------------------------------------------------------------------------

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

  // -------------------------------------------------------------------------
  // Session Management API methods
  // -------------------------------------------------------------------------

  /**
   * Получить список всех Telegram сессий текущего пользователя
   */
  listSessions: async () => {
    const response = await client.get<TelegramSession[]>('/api/telegram/sessions');
    return response.data;
  },

  /**
   * Получить детальную информацию о Telegram сессии
   * @param accountId - UUID аккаунта
   */
  getSession: async (accountId: string) => {
    const response = await client.get<TelegramSession>(`/api/telegram/sessions/${accountId}`);
    return response.data;
  },

  /**
   * Получить текущий статус здоровья Telegram сессии
   * @param accountId - UUID аккаунта
   */
  getSessionHealth: async (accountId: string) => {
    const response = await client.get<SessionHealth>(`/api/telegram/sessions/${accountId}/health`);
    return response.data;
  },

  /**
   * Ручной refresh Telegram сессии
   * @param accountId - UUID аккаунта
   */
  refreshSession: async (accountId: string) => {
    const response = await client.post<SessionRefreshResponse>(`/api/telegram/sessions/${accountId}/refresh`);
    return response.data;
  },

  /**
   * Создать бэкап Telegram сессии
   * @param accountId - UUID аккаунта
   */
  backupSession: async (accountId: string) => {
    const response = await client.post<SessionBackupResponse>(`/api/telegram/sessions/${accountId}/backup`);
    return response.data;
  },

  /**
   * Восстановить Telegram сессию из бэкапа
   * @param accountId - UUID аккаунта
   * @param backupPath - Путь к файлу бэкапа
   */
  restoreSession: async (accountId: string, backupPath: string) => {
    const response = await client.post<SessionRefreshResponse>(`/api/telegram/sessions/${accountId}/restore`, {
      backup_path: backupPath,
    });
    return response.data;
  },

  /**
   * Получить конфигурацию автоматического refresh для Telegram сессии
   * @param accountId - UUID аккаунта
   */
  getSessionConfig: async (accountId: string) => {
    const response = await client.get<SessionConfig>(`/api/telegram/sessions/${accountId}/config`);
    return response.data;
  },

  /**
   * Обновить конфигурацию автоматического refresh для Telegram сессии
   * @param accountId - UUID аккаунта
   * @param config - Новые параметры конфигурации
   */
  updateSessionConfig: async (
    accountId: string,
    config: {
      auto_refresh_enabled?: boolean;
      refresh_before_expires_hours?: number;
    }
  ) => {
    const response = await client.put<SessionConfig>(`/api/telegram/sessions/${accountId}/config`, config);
    return response.data;
  },

  /**
   * Настроить TOTP 2FA для Telegram аккаунта
   * Генерирует секрет и otpauth URI для сканирования QR кода
   * @param accountId - UUID аккаунта
   */
  setup2FA: async (accountId: string) => {
    const response = await client.post<TOTPSetupResponse>(`/api/telegram/sessions/${accountId}/2fa/setup`);
    return response.data;
  },

  /**
   * Верифицировать TOTP код и активировать 2FA для автоматического refresh
   * @param accountId - UUID аккаунта
   * @param code - TOTP код из authenticator app
   */
  verify2FA: async (accountId: string, code: string) => {
    const response = await client.post<TOTPStatusResponse>(
      `/api/telegram/sessions/${accountId}/2fa/verify`,
      { code }
    );
    return response.data;
  },

  /**
   * Отключить TOTP 2FA для Telegram аккаунта
   * @param accountId - UUID аккаунта
   * @param code - Опциональный TOTP код для подтверждения
   */
  disable2FA: async (accountId: string, code?: string) => {
    const response = await client.post<TOTPStatusResponse>(
      `/api/telegram/sessions/${accountId}/2fa/disable`,
      code ? { code } : {}
    );
    return response.data;
  },

  /**
   * Отправить тестовый алерт для проверки webhook интеграций
   */
  sendTestAlert: async () => {
    const response = await client.post<TestAlertResponse>('/api/telegram/sessions/test-alert');
    return response.data;
  },
};
