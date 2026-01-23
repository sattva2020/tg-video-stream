/**
 * Mobile API endpoints
 *
 * Handles mobile-specific operations like device registration and push tokens.
 */

import { client } from './client';
import type { DeviceRegistration } from './types';

/**
 * Mobile API endpoints
 */
export const mobileApi = {
  /**
   * Register device for push notifications
   */
  registerDevice: async (registration: DeviceRegistration): Promise<void> => {
    await client.post('/api/mobile/devices/register', registration);
  },

  /**
   * Update push token for existing device
   */
  updatePushToken: async (deviceId: string, pushToken: string): Promise<void> => {
    await client.put(`/api/mobile/devices/${deviceId}/token`, { push_token: pushToken });
  },

  /**
   * Unregister device (logout or app uninstall)
   */
  unregisterDevice: async (deviceId: string): Promise<void> => {
    await client.delete(`/api/mobile/devices/${deviceId}`);
  },

  /**
   * Get device info
   */
  getDeviceInfo: async (deviceId: string): Promise<DeviceRegistration & { id: string }> => {
    const response = await client.get<DeviceRegistration & { id: string }>(
      `/api/mobile/devices/${deviceId}`
    );
    return response.data;
  },
};
