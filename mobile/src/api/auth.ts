import { client, tokenStorage } from './client';
import type { User, LoginCredentials, AuthResponse } from './types';

/**
 * Authentication API endpoints
 */
export const authApi = {
  /**
   * Login with email and password
   */
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await client.post<AuthResponse>('/api/auth/login', credentials);
    return response.data;
  },

  /**
   * Get current user information
   */
  getMe: async (): Promise<User> => {
    const response = await client.get<User>('/api/users/me');
    return response.data;
  },

  /**
   * Logout current user
   */
  logout: async (): Promise<void> => {
    await client.post('/api/auth/logout');
  },

  /**
   * Refresh authentication token
   */
  refreshToken: async (): Promise<AuthResponse> => {
    const response = await client.post<AuthResponse>('/api/auth/refresh');
    return response.data;
  },

  /**
   * Verify email
   */
  verifyEmail: async (token: string): Promise<void> => {
    await client.post('/api/auth/verify-email', { token });
  },

  /**
   * Request password reset
   */
  requestPasswordReset: async (email: string): Promise<void> => {
    await client.post('/api/auth/password-reset-request', { email });
  },

  /**
   * Reset password with token
   */
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await client.post('/api/auth/password-reset', { token, new_password: newPassword });
  },
};

/**
 * Helper to save token after successful login
 */
export const saveToken = async (token: string): Promise<void> => {
  await tokenStorage.setToken(token);
};

/**
 * Helper to clear token on logout
 */
export const clearToken = async (): Promise<void> => {
  await tokenStorage.removeToken();
};
