import type { AxiosError } from 'axios';
import { client } from '../../api/client';
import i18next from '../../i18n';

export const AUTH_ENDPOINTS = {
  login: '/api/auth/login',
  register: '/api/auth/register',
  me: '/api/users/me',
} as const;

export type AuthErrorCode = 'pending' | 'rejected' | 'conflict' | 'server';

export interface AuthErrorPayload {
  code: AuthErrorCode;
  // server may return either a localized message OR a message_key for client-side localization
  message?: string;
  message_key?: string;
  hint?: string;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface RegisterPayload extends AuthCredentials {
  full_name?: string;
}

export interface CurrentUserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  status: 'approved' | 'pending' | 'rejected';
}

export class AuthClientError extends Error {
  public readonly status: number;
  public readonly payload: AuthErrorPayload;

  constructor(status: number, payload: AuthErrorPayload) {
    super(payload.message);
    this.status = status;
    this.payload = payload;
  }
}

const isAuthErrorPayload = (value: unknown): value is AuthErrorPayload => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.code === 'string' &&
    (typeof record.message === 'string' || typeof record.message_key === 'string')
  );
};

const fallbackError: AuthErrorPayload = {
  code: 'server',
  message: 'Что-то пошло не так. Попробуйте ещё раз или обратитесь в поддержку.',
  hint: 'Если ошибка повторяется, свяжитесь с администратором стрима.',
};

const normalizeAuthError = (error: unknown): AuthClientError => {
  if (typeof window === 'undefined') {
    return new AuthClientError(0, fallbackError);
  }

  if ((error as AxiosError)?.isAxiosError) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status ?? 0;
    const data = axiosError.response?.data;
    if (isAuthErrorPayload(data)) {
      const payload = data as AuthErrorPayload;
      // normalize: ensure 'message' is present for consumers by resolving message_key via i18next
      if (!payload.message && payload.message_key) {
        try {
          payload.message = i18next.t(payload.message_key);
        } catch (e) {
          payload.message = payload.message_key;
        }
      }
      return new AuthClientError(status, payload as Required<AuthErrorPayload & {message: string}>);
    }
    return new AuthClientError(status, fallbackError);
  }

  return new AuthClientError(0, fallbackError);
};

const post = async <T>(url: string, payload: unknown): Promise<T> => {
  try {
    const response = await client.post<T>(url, payload);
    return response.data;
  } catch (error) {
    throw normalizeAuthError(error);
  }
};

const get = async <T>(url: string): Promise<T> => {
  try {
    const response = await client.get<T>(url);
    return response.data;
  } catch (error) {
    throw normalizeAuthError(error);
  }
};

export const authClient = {
  login: (payload: AuthCredentials) => post<AuthSession>(AUTH_ENDPOINTS.login, payload),
  register: (payload: RegisterPayload) => post<Record<string, unknown>>(AUTH_ENDPOINTS.register, payload),
  currentUser: () => get<CurrentUserProfile>(AUTH_ENDPOINTS.me),
};

export const isAuthClientError = (error: unknown): error is AuthClientError => error instanceof AuthClientError;
