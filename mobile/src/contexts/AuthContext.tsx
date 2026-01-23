import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { User, UserRole } from '../api/types';
import { authApi, tokenStorage } from '../api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isPendingApproval: boolean;
  pendingApprovalMessage: string | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  clearPendingStatus: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

interface JwtPayload {
  sub: string;
  role?: string;
  exp: number;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPendingApproval, setIsPendingApproval] = useState<boolean>(false);
  const [pendingApprovalMessage, setPendingApprovalMessage] = useState<string | null>(null);

  const logout = useCallback(async () => {
    try {
      await tokenStorage.removeToken();
    } catch (error) {
      // Silently fail if secure store is not available
    }
    setUser(null);
    setIsAuthenticated(false);
    setIsPendingApproval(false);
    setPendingApprovalMessage(null);
  }, []);

  const clearPendingStatus = useCallback(() => {
    setIsPendingApproval(false);
    setPendingApprovalMessage(null);
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      const token = await tokenStorage.getToken();
      if (token) {
        try {
          const decoded = jwtDecode<JwtPayload>(token);
          const currentTime = Date.now() / 1000;

          if (decoded.exp < currentTime) {
            await logout();
            setIsLoading(false);
            return;
          }

          try {
            const userData = await authApi.getMe();
            // Ensure role is present. If backend doesn't send it yet, fallback to token role or USER.
            const userWithRole: User = {
              id: userData.id,
              email: userData.email,
              full_name: userData.full_name,
              profile_picture_url: userData.profile_picture_url,
              role: (userData.role as UserRole) || (decoded.role as UserRole) || UserRole.USER,
              status: userData.status,
              last_login: userData.last_login,
              email_verified: userData.email_verified,
              google_id: userData.google_id,
              telegram_id: userData.telegram_id,
              telegram_username: userData.telegram_username,
              totp_enabled: userData.totp_enabled,
            };
            setUser(userWithRole);
            setIsAuthenticated(true);
            setIsPendingApproval(false);
            setPendingApprovalMessage(null);
          } catch (error: any) {
            // Check if it's a 403 error with pending status
            if (error?.response?.status === 403) {
              const detail = error?.response?.data?.detail;
              if (detail && (detail.code === 'pending' || detail.code === 'rejected')) {
                // User is authenticated but not approved yet
                const message = detail.message || detail.message_key || 'Аккаунт ожидает одобрения администратора';
                setIsPendingApproval(true);
                setPendingApprovalMessage(message);
                setIsAuthenticated(false);
                setUser(null);
                // Don't clear token - user might be approved later
                setIsLoading(false);
                return;
              }
            }

            // For other errors, logout completely
            await logout();
          }
        } catch (error) {
          // Invalid token
          await logout();
        }
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      // Secure store not available or other error
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    void checkAuth();
  }, [checkAuth]);

  const login = async (token: string) => {
    await tokenStorage.setToken(token);
    await checkAuth();
  };

  const refreshUser = useCallback(async () => {
    await checkAuth();
  }, [checkAuth]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        isPendingApproval,
        pendingApprovalMessage,
        login,
        logout,
        refreshUser,
        clearPendingStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
