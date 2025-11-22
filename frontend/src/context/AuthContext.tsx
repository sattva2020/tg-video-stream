import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { User, UserRole } from '../types/user';
import { authApi } from '../api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
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

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode<JwtPayload>(token);
        const currentTime = Date.now() / 1000;
        
        if (decoded.exp < currentTime) {
          logout();
          return;
        }

        try {
            const userData = await authApi.getMe();
            console.log('User data fetched:', userData);
            // Ensure role is present. If backend doesn't send it yet, fallback to token role or USER.
            // Note: userData might not strictly match User interface until T009 is done.
            const userWithRole: User = {
                id: userData.id,
                email: userData.email,
                full_name: userData.full_name,
                profile_picture_url: userData.profile_picture_url,
                role: (userData.role as UserRole) || (decoded.role as UserRole) || UserRole.USER
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
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (token: string) => {
    localStorage.setItem('token', token);
    await checkAuth();
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
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
