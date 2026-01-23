/**
 * useNetworkStatus Hook
 *
 * Custom hook for monitoring network connectivity status.
 * Provides real-time network state updates using NetInfo.
 *
 * Features:
 * - Monitor online/offline status
 * - Track connection type (wifi, cellular, none)
 * - Detect internet reachability
 * - Provide detailed network information
 *
 * Usage:
 * ```tsx
 * const { isOnline, connectionType, isInternetReachable } = useNetworkStatus();
 * ```
 */

import { useState, useEffect, useCallback } from 'react';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

export interface NetworkStatus {
  isOnline: boolean;
  isInternetReachable: boolean | null;
  connectionType: string | null;
  connectionDetails: {
    isConnectionExpensive: boolean | null;
    ipAddress: string | null;
    subnet: string | null;
  } | null;
}

interface UseNetworkStatusReturn extends NetworkStatus {
  retry: () => Promise<void>;
}

const initialState: NetworkStatus = {
  isOnline: true,
  isInternetReachable: null,
  connectionType: null,
  connectionDetails: null,
};

export const useNetworkStatus = (): UseNetworkStatusReturn => {
  const [networkState, setNetworkState] = useState<NetInfoState | null>(null);

  /**
   * Convert NetInfo state to our simplified NetworkStatus interface
   */
  const getNetworkStatus = useCallback((state: NetInfoState | null): NetworkStatus => {
    if (!state) {
      return initialState;
    }

    return {
      isOnline: state.isConnected ?? false,
      isInternetReachable: state.isInternetReachable ?? null,
      connectionType: state.type,
      connectionDetails: {
        isConnectionExpensive: state.details.isConnectionExpensive ?? null,
        ipAddress: state.details.ipAddress ?? null,
        subnet: state.details.subnet ?? null,
      },
    };
  }, []);

  /**
   * Manually retry network connection check
   */
  const retry = useCallback(async (): Promise<void> => {
    const state = await NetInfo.fetch();
    setNetworkState(state);
  }, []);

  useEffect(() => {
    // Initialize network status on mount
    const initializeNetwork = async (): Promise<void> => {
      const state = await NetInfo.fetch();
      setNetworkState(state);
    };

    void initializeNetwork();

    // Subscribe to network state changes
    const unsubscribe = NetInfo.addEventListener((state) => {
      setNetworkState(state);
    });

    // Cleanup subscription on unmount
    return () => {
      unsubscribe();
    };
  }, []);

  const networkStatus = getNetworkStatus(networkState);

  return {
    ...networkStatus,
    retry,
  };
};
