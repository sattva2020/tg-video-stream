/**
 * useOfflineSync Hook
 *
 * Custom hook for synchronizing data when the device comes back online.
 * Provides utilities for managing offline changes and syncing them to the backend.
 *
 * Usage:
 * ```tsx
 * const { saveChange, isOnline, pendingCount, sync } = useOfflineSync();
 * ```
 */

import { useCallback } from 'react';
import { useOffline } from '../contexts/OfflineContext';
import type { PendingChange } from '../utils/offlineStorage';

interface UseOfflineSyncReturn {
  isOnline: boolean;
  isSyncing: boolean;
  pendingCount: number;
  lastSync: number | null;
  sync: () => Promise<void>;
  saveChange: (change: Omit<PendingChange, 'id' | 'timestamp'>) => Promise<string>;
  clearPending: () => Promise<void>;
  queueCreate: (endpoint: string, data: unknown) => Promise<string>;
  queueUpdate: (endpoint: string, data: unknown) => Promise<string>;
  queueDelete: (endpoint: string, params?: Record<string, string>) => Promise<string>;
}

/**
 * Hook for managing offline synchronization
 */
export const useOfflineSync = (): UseOfflineSyncReturn => {
  const { isOnline, isSyncing, pendingChangesCount, lastSync, sync, saveChange, clearPending } =
    useOffline();

  /**
   * Queue a CREATE request for later sync
   */
  const queueCreate = useCallback(
    async (endpoint: string, data: unknown): Promise<string> => {
      return saveChange({
        type: 'create',
        endpoint,
        method: 'POST',
        data,
      });
    },
    [saveChange]
  );

  /**
   * Queue an UPDATE request for later sync
   */
  const queueUpdate = useCallback(
    async (endpoint: string, data: unknown): Promise<string> => {
      return saveChange({
        type: 'update',
        endpoint,
        method: 'PUT',
        data,
      });
    },
    [saveChange]
  );

  /**
   * Queue a DELETE request for later sync
   */
  const queueDelete = useCallback(
    async (endpoint: string, params?: Record<string, string>): Promise<string> => {
      return saveChange({
        type: 'delete',
        endpoint,
        method: 'DELETE',
        params,
      });
    },
    [saveChange]
  );

  return {
    isOnline,
    isSyncing,
    pendingCount: pendingChangesCount,
    lastSync,
    sync,
    saveChange,
    clearPending,
    queueCreate,
    queueUpdate,
    queueDelete,
  };
};
