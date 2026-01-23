/**
 * Offline Storage Utilities
 *
 * Provides AsyncStorage-based storage for offline mode.
 * Handles configuration changes that sync when the device comes back online.
 *
 * Features:
 * - Store pending configuration changes
 * - Queue API requests for later sync
 * - Track sync status and conflicts
 * - Manage offline data lifecycle
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage keys
const PENDING_CHANGES_KEY = '@sattva_pending_changes';
const SYNC_QUEUE_KEY = '@sattva_sync_queue';
const LAST_SYNC_KEY = '@sattva_last_sync';

/**
 * Pending configuration change
 */
export interface PendingChange {
  id: string;
  timestamp: number;
  type: 'create' | 'update' | 'delete';
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data?: unknown;
  params?: Record<string, string>;
}

/**
 * Sync queue item
 */
export interface SyncQueueItem extends PendingChange {
  retryCount: number;
  lastError?: string;
}

/**
 * Sync status
 */
export interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  pendingChanges: number;
  lastSync: number | null;
  hasConflicts: boolean;
}

/**
 * Save a pending change to local storage
 */
export const savePendingChange = async (change: Omit<PendingChange, 'id' | 'timestamp'>): Promise<string> => {
  try {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const pendingChange: PendingChange = {
      ...change,
      id,
      timestamp: Date.now(),
    };

    const existingChanges = await getPendingChanges();
    const updatedChanges = [...existingChanges, pendingChange];

    await AsyncStorage.setItem(PENDING_CHANGES_KEY, JSON.stringify(updatedChanges));
    return id;
  } catch (error) {
    console.error('Failed to save pending change:', error);
    throw new Error('Failed to save pending change');
  }
};

/**
 * Get all pending changes from local storage
 */
export const getPendingChanges = async (): Promise<PendingChange[]> => {
  try {
    const data = await AsyncStorage.getItem(PENDING_CHANGES_KEY);
    if (!data) {
      return [];
    }
    return JSON.parse(data) as PendingChange[];
  } catch (error) {
    console.error('Failed to get pending changes:', error);
    return [];
  }
};

/**
 * Remove a pending change from local storage
 */
export const removePendingChange = async (id: string): Promise<void> => {
  try {
    const existingChanges = await getPendingChanges();
    const updatedChanges = existingChanges.filter((change) => change.id !== id);
    await AsyncStorage.setItem(PENDING_CHANGES_KEY, JSON.stringify(updatedChanges));
  } catch (error) {
    console.error('Failed to remove pending change:', error);
    throw new Error('Failed to remove pending change');
  }
};

/**
 * Clear all pending changes
 */
export const clearPendingChanges = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(PENDING_CHANGES_KEY);
  } catch (error) {
    console.error('Failed to clear pending changes:', error);
  }
};

/**
 * Add an item to the sync queue
 */
export const addToSyncQueue = async (item: SyncQueueItem): Promise<void> => {
  try {
    const existingQueue = await getSyncQueue();
    const updatedQueue = [...existingQueue, item];
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(updatedQueue));
  } catch (error) {
    console.error('Failed to add to sync queue:', error);
    throw new Error('Failed to add to sync queue');
  }
};

/**
 * Get all items from the sync queue
 */
export const getSyncQueue = async (): Promise<SyncQueueItem[]> => {
  try {
    const data = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
    if (!data) {
      return [];
    }
    return JSON.parse(data) as SyncQueueItem[];
  } catch (error) {
    console.error('Failed to get sync queue:', error);
    return [];
  }
};

/**
 * Update a sync queue item (e.g., increment retry count, add error)
 */
export const updateSyncQueueItem = async (
  id: string,
  updates: Partial<SyncQueueItem>
): Promise<void> => {
  try {
    const existingQueue = await getSyncQueue();
    const updatedQueue = existingQueue.map((item) =>
      item.id === id ? { ...item, ...updates } : item
    );
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(updatedQueue));
  } catch (error) {
    console.error('Failed to update sync queue item:', error);
    throw new Error('Failed to update sync queue item');
  }
};

/**
 * Remove an item from the sync queue
 */
export const removeFromSyncQueue = async (id: string): Promise<void> => {
  try {
    const existingQueue = await getSyncQueue();
    const updatedQueue = existingQueue.filter((item) => item.id !== id);
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(updatedQueue));
  } catch (error) {
    console.error('Failed to remove from sync queue:', error);
    throw new Error('Failed to remove from sync queue');
  }
};

/**
 * Clear all items from the sync queue
 */
export const clearSyncQueue = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(SYNC_QUEUE_KEY);
  } catch (error) {
    console.error('Failed to clear sync queue:', error);
  }
};

/**
 * Update the last sync timestamp
 */
export const updateLastSync = async (): Promise<void> => {
  try {
    await AsyncStorage.setItem(LAST_SYNC_KEY, Date.now().toString());
  } catch (error) {
    console.error('Failed to update last sync:', error);
  }
};

/**
 * Get the last sync timestamp
 */
export const getLastSync = async (): Promise<number | null> => {
  try {
    const data = await AsyncStorage.getItem(LAST_SYNC_KEY);
    return data ? parseInt(data, 10) : null;
  } catch (error) {
    console.error('Failed to get last sync:', error);
    return null;
  }
};

/**
 * Get current sync status
 */
export const getSyncStatus = async (isOnline: boolean): Promise<SyncStatus> => {
  try {
    const pendingChanges = await getPendingChanges();
    const syncQueue = await getSyncQueue();
    const lastSync = await getLastSync();

    return {
      isOnline,
      isSyncing: false, // This will be managed by the context
      pendingChanges: pendingChanges.length + syncQueue.length,
      lastSync,
      hasConflicts: false, // TODO: Implement conflict detection
    };
  } catch (error) {
    console.error('Failed to get sync status:', error);
    return {
      isOnline,
      isSyncing: false,
      pendingChanges: 0,
      lastSync: null,
      hasConflicts: false,
    };
  }
};

/**
 * Clear all offline data (useful for logout or debugging)
 */
export const clearAllOfflineData = async (): Promise<void> => {
  try {
    await AsyncStorage.multiRemove([PENDING_CHANGES_KEY, SYNC_QUEUE_KEY, LAST_SYNC_KEY]);
  } catch (error) {
    console.error('Failed to clear all offline data:', error);
  }
};
