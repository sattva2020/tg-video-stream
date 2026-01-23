import { client } from './client';

export interface APIKey {
  id: string;
  owner_id: string;
  name: string;
  scopes: string[];
  rate_limit?: { requests: number; window: number } | null;
  is_active: boolean;
  expires_at: string | null;
  last_used: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CreateAPIKeyData {
  name: string;
  scopes: string[];
  rate_limit?: { requests: number; window: number } | null;
  expires_at?: string | null;
}

export interface APIKeyResponse extends APIKey {
  key?: string | null;
}

export interface APIKeyListResponse {
  items: APIKey[];
  total: number;
  page: number;
  page_size: number;
}

export const apiKeysApi = {
  list: async () => {
    const response = await client.get<APIKey[]>('/api/v1/keys/');
    return response.data;
  },

  create: async (data: CreateAPIKeyData) => {
    const response = await client.post<APIKeyResponse>('/api/v1/keys/', data);
    return response.data;
  },

  get: async (keyId: string) => {
    const response = await client.get<APIKey>(`/api/v1/keys/${keyId}`);
    return response.data;
  },

  update: async (keyId: string, data: Partial<CreateAPIKeyData> & { is_active?: boolean }) => {
    const response = await client.patch<APIKey>(`/api/v1/keys/${keyId}`, data);
    return response.data;
  },

  delete: async (keyId: string) => {
    const response = await client.delete(`/api/v1/keys/${keyId}`);
    return response.data;
  },

  revoke: async (keyId: string) => {
    const response = await client.post<APIKey>(`/api/v1/keys/${keyId}/revoke`);
    return response.data;
  },
};
