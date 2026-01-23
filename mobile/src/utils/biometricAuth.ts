/**
 * Biometric Authentication Utilities
 *
 * Provides utilities for biometric authentication (Face ID, Touch ID, fingerprint).
 * Uses expo-local-authentication for cross-platform biometric support.
 *
 * Features:
 * - Check biometric availability
 * - Check if biometrics are enrolled
 * - Authenticate with biometrics
 * - Get biometric type (Face ID, Touch ID, fingerprint)
 * - Local storage for biometric preference
 */

import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';

const BIOMETRIC_ENABLED_KEY = 'biometricEnabled';
const BIOMETRIC_EMAIL_KEY = 'biometricEmail';

/**
 * Biometric authentication result
 */
export interface BiometricResult {
  success: boolean;
  error?: string;
  biometricType?: BiometricType;
}

/**
 * Supported biometric types
 */
export type BiometricType = 'face' | 'fingerprint' | 'iris';

/**
 * Get the type of biometric authentication available on the device
 */
export const getBiometricType = async (): Promise<BiometricType | null> => {
  try {
    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();

    if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
      return 'face';
    }
    if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
      return 'fingerprint';
    }
    if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
      return 'iris';
    }

    return null;
  } catch (error) {
    return null;
  }
};

/**
 * Get human-readable biometric type name
 */
export const getBiometricTypeName = (type: BiometricType | null): string => {
  switch (type) {
    case 'face':
      return 'Face ID';
    case 'fingerprint':
      return 'fingerprint';
    case 'iris':
      return 'iris scan';
    default:
      return 'biometric authentication';
  }
};

/**
 * Check if biometric authentication is available on the device
 */
export const isBiometricAvailable = async (): Promise<boolean> => {
  try {
    return await LocalAuthentication.hasHardwareAsync();
  } catch (error) {
    return false;
  }
};

/**
 * Check if biometric authentication is enrolled (user has set up Face ID, fingerprint, etc.)
 */
export const isBiometricEnrolled = async (): Promise<boolean> => {
  try {
    return await LocalAuthentication.isEnrolledAsync();
  } catch (error) {
    return false;
  }
};

/**
 * Check if biometric login is enabled for the current user
 */
export const isBiometricEnabled = async (): Promise<boolean> => {
  try {
    const enabled = await SecureStore.getItemAsync(BIOMETRIC_ENABLED_KEY);
    return enabled === 'true';
  } catch (error) {
    return false;
  }
};

/**
 * Enable biometric authentication for the current user
 */
export const enableBiometric = async (email: string): Promise<void> => {
  try {
    await SecureStore.setItemAsync(BIOMETRIC_ENABLED_KEY, 'true');
    await SecureStore.setItemAsync(BIOMETRIC_EMAIL_KEY, email);
  } catch (error) {
    throw new Error('Failed to enable biometric authentication');
  }
};

/**
 * Disable biometric authentication for the current user
 */
export const disableBiometric = async (): Promise<void> => {
  try {
    await SecureStore.deleteItemAsync(BIOMETRIC_ENABLED_KEY);
    await SecureStore.deleteItemAsync(BIOMETRIC_EMAIL_KEY);
  } catch (error) {
    // Silently fail
  }
};

/**
 * Get the email associated with biometric authentication
 */
export const getBiometricEmail = async (): Promise<string | null> => {
  try {
    return await SecureStore.getItemAsync(BIOMETRIC_EMAIL_KEY);
  } catch (error) {
    return null;
  }
};

/**
 * Authenticate with biometrics
 *
 * @param promptMessage - Message to display in the biometric prompt
 * @param fallbackLabel - Label for the fallback button (e.g., "Use Password")
 * @param cancelLabel - Label for the cancel button
 */
export const authenticateWithBiometrics = async (
  promptMessage: string = 'Authenticate to continue',
  fallbackLabel?: string,
  cancelLabel?: string
): Promise<BiometricResult> => {
  try {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    if (!hasHardware) {
      return {
        success: false,
        error: 'Biometric authentication is not available on this device',
      };
    }

    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    if (!isEnrolled) {
      return {
        success: false,
        error: 'No biometric data enrolled. Please set up Face ID or fingerprint in your device settings.',
      };
    }

    const biometricType = await getBiometricType();

    const result = await LocalAuthentication.authenticateAsync({
      promptMessage,
      fallbackLabel,
      cancelLabel,
      disableDeviceFallback: false,
    });

    if (result.success) {
      return {
        success: true,
        biometricType: biometricType || undefined,
      };
    } else {
      return {
        success: false,
        error: result.error === 'user_cancel' ? 'Authentication cancelled' : 'Authentication failed',
        biometricType: biometricType || undefined,
      };
    }
  } catch (error: any) {
    return {
      success: false,
      error: error.message || 'Biometric authentication failed',
    };
  }
};

/**
 * Check if biometric authentication can be used (hardware available + enrolled + enabled)
 */
export const canUseBiometric = async (): Promise<boolean> => {
  try {
    const hasHardware = await isBiometricAvailable();
    const isEnrolled = await isBiometricEnrolled();
    const isEnabled = await isBiometricEnabled();

    return hasHardware && isEnrolled && isEnabled;
  } catch (error) {
    return false;
  }
};
