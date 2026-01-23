import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

type InstallStatus = 'unsupported' | 'installable' | 'installed' | 'prompting';

interface PWAInstallContextType {
  isInstallable: boolean;
  isInstalled: boolean;
  status: InstallStatus;
  promptInstall: () => Promise<boolean>;
}

const PWAInstallContext = createContext<PWAInstallContextType | undefined>(undefined);

const getInitialStatus = (): InstallStatus => {
  if (typeof window === 'undefined') {
    return 'unsupported';
  }
  if (!('serviceWorker' in navigator)) {
    return 'unsupported';
  }
  return 'installable';
};

const isAppInstalled = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }

  // Check if running as standalone app
  const isStandalone = (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true
  );

  // Check if already installed (some browsers set this flag)
  const hasInstalledFlag = window.localStorage.getItem('pwa-installed') === 'true';

  return isStandalone || hasInstalledFlag;
};

export const PWAInstallProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<InstallStatus>(getInitialStatus);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState<boolean>(isAppInstalled);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (!('serviceWorker' in navigator)) {
      setStatus('unsupported');
      return;
    }

    let mounted = true;

    // Check if already installed on mount
    if (isAppInstalled()) {
      if (mounted) {
        setIsInstalled(true);
        setStatus('installed');
      }
      return;
    }

    // Listen for beforeinstallprompt event
    const handleBeforeInstallPrompt = (event: Event) => {
      // Prevent Chrome 67 and earlier from automatically showing the prompt
      event.preventDefault();

      if (!mounted) {
        return;
      }

      // Store the event for later use
      setDeferredPrompt(event as BeforeInstallPromptEvent);
      setStatus('installable');
    };

    // Listen for appinstalled event
    const handleAppInstalled = () => {
      if (!mounted) {
        return;
      }

      // Clear the deferred prompt
      setDeferredPrompt(null);
      setIsInstalled(true);
      setStatus('installed');

      // Store installation flag
      window.localStorage.setItem('pwa-installed', 'true');
    };

    // Listen for display mode changes (user may install/uninstall)
    const handleDisplayModeChange = (event: MediaQueryListEvent) => {
      if (!mounted) {
        return;
      }

      if (event.matches) {
        // Running in standalone mode
        setIsInstalled(true);
        setStatus('installed');
        window.localStorage.setItem('pwa-installed', 'true');
      } else {
        // Not in standalone mode
        setIsInstalled(false);
        setStatus('installable');
        window.localStorage.removeItem('pwa-installed');
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    const displayModeQuery = window.matchMedia('(display-mode: standalone)');
    displayModeQuery.addEventListener('change', handleDisplayModeChange);

    return () => {
      mounted = false;
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
      displayModeQuery.removeEventListener('change', handleDisplayModeChange);
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (typeof window === 'undefined') {
      return false;
    }

    if (!deferredPrompt) {
      return false;
    }

    try {
      setStatus('prompting');

      // Show the install prompt
      await deferredPrompt.prompt();

      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.userChoice;

      // Clear the deferred prompt
      setDeferredPrompt(null);

      if (outcome === 'accepted') {
        setIsInstalled(true);
        setStatus('installed');
        window.localStorage.setItem('pwa-installed', 'true');
        return true;
      } else {
        setStatus('installable');
        return false;
      }
    } catch (error) {
      console.error('PWA install prompt failed:', error);
      setStatus('installable');
      return false;
    }
  }, [deferredPrompt]);

  const contextValue: PWAInstallContextType = {
    isInstallable: status === 'installable' && deferredPrompt !== null,
    isInstalled,
    status,
    promptInstall,
  };

  return (
    <PWAInstallContext.Provider value={contextValue}>
      {children}
    </PWAInstallContext.Provider>
  );
};

export const usePWAInstall = () => {
  const context = useContext(PWAInstallContext);
  if (!context) {
    throw new Error('usePWAInstall must be used within a PWAInstallProvider');
  }
  return context;
};
