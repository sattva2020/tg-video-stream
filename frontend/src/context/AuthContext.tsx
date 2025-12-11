import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { User, UserRole } from '../types/user';
import { authApi } from '../api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
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

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode<JwtPayload>(token);
        const currentTime = Date.now() / 1000;
        
        if (decoded.exp < currentTime) {
          logout();
          setIsLoading(false);
          return;
        }

        try {
            const userData = await authApi.getMe();
            console.log('User data fetched:', userData);
            // Ensure role is present. If backend doesn't send it yet, fallback to token role or USER.
            const userWithRole: User = {
                id: userData.id,
                email: userData.email,
                full_name: userData.full_name,
                profile_picture_url: userData.profile_picture_url,
                role: (userData.role as UserRole) || (decoded.role as UserRole) || UserRole.USER,
                status: userData.status,
                google_id: userData.google_id,
                telegram_id: userData.telegram_id,
                telegram_username: userData.telegram_username,
            };
            setUser(userWithRole);
            setIsAuthenticated(true);
        } catch (error) {
            console.error("Failed to fetch user", error);
          logout();
        }

      } catch (error) {
        console.error("Invalid token", error);
        logout();
      }
    } else {
        setIsAuthenticated(false);
        setUser(null);
    }
    setIsLoading(false);
  }, [logout]);

  useEffect(() => {
    void checkAuth();
  }, [checkAuth]);

  const login = async (token: string) => {
    localStorage.setItem('token', token);
    await checkAuth();
  };

  const refreshUser = useCallback(async () => {
    await checkAuth();
  }, [checkAuth]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout, refreshUser }}>
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
