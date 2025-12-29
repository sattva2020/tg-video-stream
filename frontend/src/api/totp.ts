import { client } from './client';

export interface TotpSetupResponse {
  secret: string;
  otpauth_url: string;
}

export const totpApi = {
  setup: async (): Promise<TotpSetupResponse> => {
    const response = await client.post<TotpSetupResponse>('/api/auth/totp/setup');
    return response.data;
  },
  verify: async (code: string): Promise<{ status: string }> => {
    const response = await client.post<{ status: string }>('/api/auth/totp/verify', { code });
    return response.data;
  },
  disable: async (code?: string): Promise<{ status: string }> => {
    const payload = code ? { code } : {};
    const response = await client.post<{ status: string }>('/api/auth/totp/disable', payload);
    return response.data;
  },
};
