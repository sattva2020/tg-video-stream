/**
 * API клиент для авторизации через Telegram Login Widget.
 */
import axios from 'axios';
import { config } from '../config';

const apiClient = axios.create({
  baseURL: config.apiBaseUrl,
  withCredentials: true, // Для работы с HttpOnly cookies
});

/**
 * Данные от Telegram Login Widget.
 */
export interface TelegramAuthData {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
  turnstile_token?: string;
}

/**
 * Ответ пользователя.
 */
export interface UserResponse {
  id: string;
  email?: string;
  full_name?: string;
  profile_picture_url?: string;
  role: string;
  status: string;
  telegram_id?: number;
  telegram_username?: string;
}

/**
 * Ответ успешной авторизации.
 */
export interface TelegramAuthResponse {
  success: boolean;
  user: UserResponse;
  is_new_user: boolean;
  message: string;
}

/**
 * Ответ связывания Telegram.
 */
export interface TelegramLinkResponse {
  success: boolean;
  message: string;
  telegram_id: number;
  telegram_username?: string;
}

/**
 * Ответ отвязки Telegram.
 */
export interface TelegramUnlinkResponse {
  success: boolean;
  message: string;
}

/**
 * Авторизация или регистрация через Telegram.
 */
export async function telegramAuth(data: TelegramAuthData): Promise<TelegramAuthResponse> {
  const response = await apiClient.post<TelegramAuthResponse>('/api/auth/telegram-widget', data);
  return response.data;
}

/**
 * Привязка Telegram к существующему аккаунту.
 */
export async function linkTelegram(data: TelegramAuthData): Promise<TelegramLinkResponse> {
  const response = await apiClient.post<TelegramLinkResponse>('/api/auth/telegram-widget/link', data);
  return response.data;
}

/**
 * Отвязка Telegram от аккаунта.
 */
export async function unlinkTelegram(): Promise<TelegramUnlinkResponse> {
  const response = await apiClient.delete<TelegramUnlinkResponse>('/api/auth/telegram-widget/unlink');
  return response.data;
}

export const telegramAuthApi = {
  auth: telegramAuth,
  link: linkTelegram,
  unlink: unlinkTelegram,
};
