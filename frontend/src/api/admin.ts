import { client } from './client';

export const adminApi = {
  restartStream: async () => {
    const response = await client.post('/api/admin/restart_stream');
    return response.data;
  },
  listUsers: async (status?: string) => {
    const params = status ? { status } : undefined;
    const response = await client.get('/api/admin/users', { params });
    return response.data;
  },
  approveUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/approve`);
    return response.data;
  },
  rejectUser: async (id: string) => {
    const response = await client.post(`/api/admin/users/${id}/reject`);
    return response.data;
  }
};
