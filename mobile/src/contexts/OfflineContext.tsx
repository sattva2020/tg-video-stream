/**
 * Offline Context
 *
 * React Context for managing offline state and synchronization.
 * Provides offline-aware API utilities and sync status tracking.
 *
 * Features:
 * - Track online/offline status
 * - Manage pending changes and sync queue
 * - Automatically sync when coming back online
 * - Provide offline-aware API wrapper
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import NetInfo from '@react-native-community/netinfo';
import {
  savePendingChange,
  getPendingChanges,
  removePendingChange,
  clearPendingChanges,
  addToSyncQueue,
  getSyncQueue,
  updateSyncQueueItem,
  removeFromSyncQueue,
  clearSyncQueue,
  updateLastSync,
  getLastSync,
  getSyncStatus,
  clearAllOfflineData,
  type PendingChange,
  type SyncStatus,
  type SyncQueueItem,
} from '../utils/offlineStorage';
import { client } from '../api/client';

interface OfflineState {
  isOnline: boolean;
  isSyncing: boolean;
  pendingChangesCount: number;
  lastSync: number | null;
  hasConflicts: boolean;
  sync: () => Promise<void>;
  saveChange: (change: Omit<PendingChange, 'id' | 'timestamp'>) => Promise<string>;
  clearPending: () => Promise<void>;
}

const OfflineContext = createContext<OfflineState | undefined>(undefined);

interface OfflineProviderProps {
  children: ReactNode;
}

export const OfflineProvider: React.FC<OfflineProviderProps> = ({ children }) => {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [pendingChangesCount, setPendingChangesCount] = useState<number>(0);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const [hasConflicts, setHasConflicts] = useState<boolean>(false);

  /**
   * Update sync status from storage
   */
  const updateSyncStatus = useCallback(async () => {
    const status = await getSyncStatus(isOnline);
    setPendingChangesCount(status.pendingChanges);
    setLastSync(status.lastSync);
    setHasConflicts(status.hasConflicts);
  }, [isOnline]);

  /**
   * Sync all pending changes and queued items
   */
  const sync = useCallback(async (): Promise<void> => {
    if (!isOnline || isSyncing) {
      return;
    }

    setIsSyncing(true);

    try {
      // Process pending changes
      const pendingChanges = await getPendingChanges();
      const syncQueue = await getSyncQueue();

      const allItems = [...pendingChanges, ...syncQueue];

      if (allItems.length === 0) {
        setIsSyncing(false);
        return;
      }

      // Process each item
      for (const item of allItems) {
        try {
          // Execute the API request
          await client.request({
            method: item.method,
            url: item.endpoint,
            data: item.data,
            params: item.params,
          });

          // Remove from both pending changes and sync queue
          await removePendingChange(item.id);
          await removeFromSyncQueue(item.id);
        } catch (error: any) {
          // On failure, move to sync queue with retry count if not already there
          const isAlreadyQueued = syncQueue.some((queued) => queued.id === item.id);

          if (!isAlreadyQueued) {
            const queueItem: SyncQueueItem = {
              ...item,
              retryCount: 0,
              lastError: error?.message || 'Unknown error',
            };
            await addToSyncQueue(queueItem);
            await removePendingChange(item.id);
          } else {
            // Update retry count
            const existingItem = syncQueue.find((queued) => queued.id === item.id);
            if (existingItem) {
              await updateSyncQueueItem(item.id, {
                retryCount: existingItem.retryCount + 1,
                lastError: error?.message || 'Unknown error',
              });
            }
          }

          // If retry count exceeds limit, log error but keep in queue
          const updatedItem = await getSyncQueue();
          const failedItem = updatedItem.find((i) => i.id === item.id);
          if (failedItem && failedItem.retryCount >= 3) {
            console.error(`Sync failed after 3 retries for item ${item.id}:`, error);
          }
        }
      }

      // Update last sync timestamp
      await updateLastSync();

      // Update sync status
      await updateSyncStatus();
    } catch (error) {
      console.error('Sync error:', error);
    } finally {
      setIsSyncing(false);
    }
  }, [isOnline, isSyncing, updateSyncStatus]);

  /**
   * Save a pending change
   */
  const saveChange = useCallback(
    async (change: Omit<PendingChange, 'id' | 'timestamp'>): Promise<string> => {
      const id = await savePendingChange(change);
      await updateSyncStatus();

      // If online, try to sync immediately
      if (isOnline) {
        void sync();
      }

      return id;
    },
    [isOnline, sync, updateSyncStatus]
  );

  /**
   * Clear all pending changes
   */
  const clearPending = useCallback(async (): Promise<void> => {
    await clearPendingChanges();
    await clearSyncQueue();
    await updateSyncStatus();
  }, [updateSyncStatus]);

  /**
   * Monitor network status
   */
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const isConnected = state.isConnected ?? false;
      setIsOnline(isConnected);
    });

    // Initialize network status
    NetInfo.fetch().then((state) => {
      setIsOnline(state.isConnected ?? false);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  /**
   * Auto-sync when coming back online
   */
  useEffect(() => {
    if (isOnline && !isSyncing) {
      // Delay sync slightly to ensure network is fully ready
      const syncTimer = setTimeout(() => {
        void sync();
      }, 1000);

      return () => clearTimeout(syncTimer);
    }
  }, [isOnline, isSyncing, sync]);

  /**
   * Initialize sync status on mount
   */
  useEffect(() => {
    void updateSyncStatus();
  }, [updateSyncStatus]);

  return (
    <OfflineContext.Provider
      value={{
        isOnline,
        isSyncing,
        pendingChangesCount,
        lastSync,
        hasConflicts,
        sync,
        saveChange,
        clearPending,
      }}
    >
      {children}
    </OfflineContext.Provider>
  );
};

export const useOffline = (): OfflineState => {
  const context = useContext(OfflineContext);
  if (context === undefined) {
    throw new Error('useOffline must be used within an OfflineProvider');
  }
  return context;
};

/**
 * Offline-aware API wrapper
 * Automatically queues requests when offline
 */
export const offlineApi = {
  async get<T>(url: string, params?: Record<string, string>): Promise<T> {
    const response = await client.get<T>(url, { params });
    return response.data;
  },

  async post<T>(url: string, data?: unknown): Promise<T> {
    try {
      const response = await client.post<T>(url, data);
      return response.data;
    } catch (error: any) {
      // If offline, queue the request
      if (!NetInfo.fetch().then((state) => state.isConnected ?? false)) {
        throw error; // Let caller handle offline case
      }
      throw error;
    }
  },

  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await client.put<T>(url, data);
    return response.data;
  },

  async patch<T>(url: string, data?: unknown): Promise<T> {
    const response = await client.patch<T>(url, data);
    return response.data;
  },

  async delete<T>(url: string): Promise<T> {
    const response = await client.delete<T>(url);
    return response.data;
  },
};
