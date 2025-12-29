import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { HeroUIProvider } from "@heroui/react";
import App from './App';
import { queryClient } from './lib/queryClient';
import { ThemePreferenceProvider, useThemePreference } from './hooks/useThemePreference';
import { initSentry } from './instrumentation/sentry';  // ← Добавлено
import './styles/tokens.css';
import './index.css';
import './i18n/index';  // Явно указываем путь к новому файлу i18n

// Инициализировать Sentry ПЕРЕД рендерингом приложения
initSentry();

// Компонент-обёртка для Toaster с учётом темы
const ThemedToaster: React.FC = () => {
  const { theme } = useThemePreference();
  
  return (
    <Toaster
      theme={theme}
      position="top-right"
      richColors
      closeButton
      toastOptions={{
        style: {
          fontFamily: 'var(--font-body)',
        },
        classNames: {
          toast: 'shadow-lg',
          success: 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800',
          error: 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800',
          warning: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800',
          info: 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800',
        },
      }}
    />
  );
};

const Root: React.FC = () => {
  const { theme } = useThemePreference();
  
  return (
    <HeroUIProvider className={theme}>
      <App />
      <ThemedToaster />
    </HeroUIProvider>
  );
};

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemePreferenceProvider>
          <Root />
        </ThemePreferenceProvider>
      </QueryClientProvider>
    </React.StrictMode>
  );
} catch (error) {
  console.error("Caught error:", error);
}
