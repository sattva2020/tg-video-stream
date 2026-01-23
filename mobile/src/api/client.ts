import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Use Constants.expoConfig?.extra for environment variables in Expo
// Fall back to hardcoded defaults for development
const getApiBaseUrl = () => {
  // In production, this should be configured in app.json under extra.apiBaseUrl
  // For now, use localhost default for development
  return 'http://localhost:8000';
};

const API_URL = getApiBaseUrl();

export const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage key for SecureStore
const TOKEN_KEY = 'user_token';

// Helper functions to get/set token from SecureStore
const getToken = async (): Promise<string | null> => {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch (error) {
    // Silently fail if SecureStore is not available (e.g., in web)
    return null;
  }
};

const setToken = async (token: string): Promise<void> => {
  try {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  } catch (error) {
    // Silently fail if SecureStore is not available
    console.error('Failed to save token:', error);
  }
};

const removeToken = async (): Promise<void> => {
  try {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch (error) {
    // Silently fail if SecureStore is not available
    console.error('Failed to remove token:', error);
  }
};

// Add a request interceptor to attach the token
client.interceptors.request.use(
  async (config) => {
    const token = await getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 errors and sliding session
client.interceptors.response.use(
  async (response) => {
    // Sliding Session: если сервер вернул новый токен — сохраняем его
    const newToken = response.headers['x-new-token'];
    if (newToken) {
      await setToken(newToken);
    }
    return response;
  },
  async (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token on 401
      await removeToken();
      // Note: Navigation to login screen will be handled by AuthContext
      // We don't redirect here to avoid tight coupling with navigation
    }
    return Promise.reject(error);
  }
);

// Export token helpers for use in AuthContext
export const tokenStorage = {
  getToken,
  setToken,
  removeToken,
};
