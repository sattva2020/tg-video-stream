/**
 * Tests for useSystemMetrics hook
 * Spec: 015-real-system-monitoring
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

import { useSystemMetrics, SYSTEM_METRICS_QUERY_KEY, METRICS_REFETCH_INTERVAL } from '@/hooks/useSystemMetrics';
import { systemApi } from '@/api/system';
import type { SystemMetrics } from '@/types/system';

// Mock API
vi.mock('@/api/system', () => ({
  systemApi: {
    getMetrics: vi.fn(),
    getActivity: vi.fn(),
  },
}));

// ==================== Test Fixtures ====================

const mockMetrics: SystemMetrics = {
  cpu_percent: 25.5,
  ram_percent: 45.2,
  disk_percent: 67.8,
  db_connections_active: 3,
  db_connections_idle: 2,
  uptime_seconds: 86400,
  collected_at: '2025-01-15T10:30:00Z',
};

const mockMetricsCritical: SystemMetrics = {
  cpu_percent: 95.0,
  ram_percent: 90.0,
  disk_percent: 92.0,
  db_connections_active: 10,
  db_connections_idle: 5,
  uptime_seconds: 172800,
  collected_at: '2025-01-15T10:30:00Z',
};

const mockMetricsWarning: SystemMetrics = {
  cpu_percent: 75.0,
  ram_percent: 72.0,
  disk_percent: 75.0,
  db_connections_active: 5,
  db_connections_idle: 3,
  uptime_seconds: 43200,
  collected_at: '2025-01-15T10:30:00Z',
};

// ==================== Test Helpers ====================

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

// ==================== Tests ====================

describe('useSystemMetrics', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('Query Behavior', () => {
    it('should fetch metrics on mount', async () => {
      vi.mocked(systemApi.getMetrics).mockResolvedValue(mockMetrics);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for data
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(systemApi.getMetrics).toHaveBeenCalledTimes(1);
      expect(result.current.metrics).toEqual(mockMetrics);
    });

    it('should return correct data structure', async () => {
      vi.mocked(systemApi.getMetrics).mockResolvedValue(mockMetrics);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Check all required fields
      expect(result.current.metrics?.cpu_percent).toBe(25.5);
      expect(result.current.metrics?.ram_percent).toBe(45.2);
      expect(result.current.metrics?.disk_percent).toBe(67.8);
      expect(result.current.metrics?.db_connections_active).toBe(3);
      expect(result.current.metrics?.db_connections_idle).toBe(2);
      expect(result.current.metrics?.uptime_seconds).toBe(86400);
      expect(result.current.metrics?.collected_at).toBe('2025-01-15T10:30:00Z');
    });

    it('should handle API errors gracefully', async () => {
      const error = new Error('Network error');
      vi.mocked(systemApi.getMetrics).mockRejectedValue(error);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.metrics).toBeUndefined();
    });
  });

  describe('Status Calculations', () => {
    it('should return healthy status for normal metrics', async () => {
      vi.mocked(systemApi.getMetrics).mockResolvedValue(mockMetrics);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.cpuStatus).toBe('healthy');
      expect(result.current.ramStatus).toBe('healthy');
      expect(result.current.diskStatus).toBe('healthy');
      expect(result.current.overallStatus).toBe('healthy');
      expect(result.current.hasCriticalIssues).toBe(false);
      expect(result.current.hasWarnings).toBe(false);
    });

    it('should return critical status for high metrics', async () => {
      vi.mocked(systemApi.getMetrics).mockResolvedValue(mockMetricsCritical);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.cpuStatus).toBe('critical');
      expect(result.current.ramStatus).toBe('critical');
      expect(result.current.diskStatus).toBe('critical');
      expect(result.current.overallStatus).toBe('critical');
      expect(result.current.hasCriticalIssues).toBe(true);
    });

    it('should return warning status for medium metrics', async () => {
      vi.mocked(systemApi.getMetrics).mockResolvedValue(mockMetricsWarning);

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.cpuStatus).toBe('warning');
      expect(result.current.ramStatus).toBe('warning');
      expect(result.current.diskStatus).toBe('warning');
      expect(result.current.overallStatus).toBe('warning');
      expect(result.current.hasWarnings).toBe(true);
      expect(result.current.hasCriticalIssues).toBe(false);
    });

    it('should return healthy status before data is loaded', async () => {
      vi.mocked(systemApi.getMetrics).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useSystemMetrics(), {
        wrapper: createWrapper(queryClient),
      });

      // Before data loads, statuses should default to healthy
      expect(result.current.cpuStatus).toBe('healthy');
      expect(result.current.ramStatus).toBe('healthy');
      expect(result.current.diskStatus).toBe('healthy');
      expect(result.current.overallStatus).toBe('healthy');
    });
  });

  describe('Query Key', () => {
    it('should use correct query key', () => {
      expect(SYSTEM_METRICS_QUERY_KEY).toEqual(['system', 'metrics']);
    });
  });

  describe('Refetch Interval', () => {
    it('should have 30 second refetch interval', () => {
      expect(METRICS_REFETCH_INTERVAL).toBe(30 * 1000);
    });
  });
});
