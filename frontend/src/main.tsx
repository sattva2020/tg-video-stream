import React from 'react';
import ReactDOM from 'react-dom/client';
import './i18n/index';  // Initialize i18n before anything else
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import HeroUIProviderSafe from './components/providers/HeroUIProviderSafe';
import App from './App';
import { queryClient } from './lib/queryClient';
import { ThemePreferenceProvider, useThemePreference } from './hooks/useThemePreference';
import { initSentry } from './instrumentation/sentry';
import { registerServiceWorker } from './service-worker-registration';
import './styles/tokens.css';
import './index.css';

// Инициализировать Sentry ПЕРЕД рендерингом приложения
initSentry();

// Register service worker for PWA functionality
registerServiceWorker().catch((error) => {
  // Service worker registration is non-critical - log but don't block app startup
  console.error('Failed to register service worker:', error);
});

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

const Root: React.FC = () => (
  <HeroUIProviderSafe>
    <App />
    <ThemedToaster />
  </HeroUIProviderSafe>
);

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
