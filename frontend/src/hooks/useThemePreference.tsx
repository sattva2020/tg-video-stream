import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type ThemeMode = 'light' | 'dark';

interface ThemeContextType {
  theme: ThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const normalizeConfiguredTheme = (value: unknown): 'light' | 'dark' | 'system' => {
  if (typeof value !== 'string') {
    return 'light';
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === 'dark' || normalized === 'system') {
    return normalized;
  }
  return 'light';
};

const getConfiguredTheme = (): ThemeMode | 'system' => {
  const envValue = import.meta.env?.VITE_DEFAULT_THEME;
  return normalizeConfiguredTheme(envValue);
};

const resolveSystemTheme = (): ThemeMode => {
  if (typeof window === 'undefined') {
    return 'light';
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const resolveInitialTheme = (configured: ThemeMode | 'system'): ThemeMode => {
  if (typeof window === 'undefined') {
    return configured === 'system' ? 'light' : configured;
  }

  const stored = window.localStorage.getItem('theme-preference') as ThemeMode | null;
  if (stored === 'light' || stored === 'dark') {
    return stored;
  }

  if (configured === 'system') {
    return resolveSystemTheme();
  }

  return configured;
};

const hasStoredPreference = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  const stored = window.localStorage.getItem('theme-preference');
  return stored === 'light' || stored === 'dark';
};

export const ThemePreferenceProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const configuredTheme = React.useMemo(getConfiguredTheme, []);
  const [theme, setTheme] = useState<ThemeMode>(() => resolveInitialTheme(configuredTheme));
  const [explicitPreference, setExplicitPreference] = useState<boolean>(hasStoredPreference);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }
    const root = document.documentElement;
    root.dataset.theme = theme;
    if (explicitPreference) {
      window.localStorage.setItem('theme-preference', theme);
    } else {
      window.localStorage.removeItem('theme-preference');
    }
  }, [theme, explicitPreference]);

  useEffect(() => {
    if (configuredTheme !== 'system' || typeof window === 'undefined') {
      return undefined;
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (event: MediaQueryListEvent) => {
      if (!explicitPreference) {
        setTheme(event.matches ? 'dark' : 'light');
      }
    };

    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, [explicitPreference, configuredTheme]);

  const toggleTheme = () => {
    setExplicitPreference(true);
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useThemePreference = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemePreference must be used within a ThemePreferenceProvider');
  }
  return context;
};
