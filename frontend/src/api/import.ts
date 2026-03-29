import { client } from './client';
import type {
  ImportCreateRequest,
  ImportJob,
  ImportJobListResponse,
  ImportJobUpdateRequest,
  ImportSummary,
} from '../types/import';

const IMPORT_BASE = '/api/import';

export const importApi = {
  /**
   * Create a new import job
   * POST /api/import
   */
  createImport: async (data: ImportCreateRequest) => {
    const response = await client.post<ImportJob>(`${IMPORT_BASE}/`, data);
    return response.data;
  },

  /**
   * List all import jobs with optional filtering
   * GET /api/import
   */
  getImportJobs: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    platform?: string;
  }) => {
    const response = await client.get<ImportJobListResponse>(`${IMPORT_BASE}/`, {
      params,
    });
    return response.data;
  },

  /**
   * Get a specific import job by ID
   * GET /api/import/{id}
   */
  getImportJob: async (id: string) => {
    const response = await client.get<ImportJob>(`${IMPORT_BASE}/${id}`);
    return response.data;
  },

  /**
   * Cancel an import job
   * DELETE /api/import/{id}
   */
  cancelImportJob: async (id: string) => {
    await client.delete(`${IMPORT_BASE}/${id}`);
  },

  /**
   * Update import job status (pause/resume/cancel)
   * PATCH /api/import/{id}
   */
  updateImportJob: async (id: string, data: ImportJobUpdateRequest) => {
    const response = await client.patch<ImportJob>(`${IMPORT_BASE}/${id}`, data);
    return response.data;
  },

  /**
   * Get import summary with results
   * GET /api/import/{id}/summary
   */
  getImportSummary: async (id: string) => {
    const response = await client.get<ImportSummary>(`${IMPORT_BASE}/${id}/summary`);
    return response.data;
  },
};
