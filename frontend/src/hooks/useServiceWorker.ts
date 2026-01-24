import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import {
  registerServiceWorker,
  unregisterServiceWorker,
  skipWaiting,
  getServiceWorkerRegistration,
  isUpdateAvailable,
} from '../service-worker-registration';

type ServiceWorkerStatus = 'unsupported' | 'registering' | 'registered' | 'error';

interface ServiceWorkerContextType {
  status: ServiceWorkerStatus;
  isUpdateAvailable: boolean;
  update: () => Promise<void>;
  skipWaiting: () => void;
  unregister: () => Promise<void>;
}

const ServiceWorkerContext = createContext<ServiceWorkerContextType | undefined>(undefined);

const getInitialStatus = (): ServiceWorkerStatus => {
  if (typeof window === 'undefined') {
    return 'unsupported';
  }
  if (!('serviceWorker' in navigator)) {
    return 'unsupported';
  }
  return 'registering';
};

const shouldEnableServiceWorker = (): boolean => {
  if (typeof window === 'undefined') {
    return false;
  }
  const isProduction = import.meta.env?.PROD;
  const enableSW = import.meta.env?.VITE_ENABLE_SERVICE_WORKER === 'true';
  return isProduction || enableSW;
};

export const ServiceWorkerProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<ServiceWorkerStatus>(getInitialStatus);
  const [updateAvailable, setUpdateAvailable] = useState<boolean>(false);
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (!shouldEnableServiceWorker()) {
      setStatus('unsupported');
      return;
    }

    let mounted = true;

    const initializeServiceWorker = async () => {
      try {
        const reg = await registerServiceWorker();
        if (!mounted) {
          return;
        }

        if (reg) {
          setRegistration(reg);
          setStatus('registered');

          // Check for updates
          const updateCheck = await isUpdateAvailable();
          if (mounted) {
            setUpdateAvailable(updateCheck);
          }

          // Listen for update found events
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  if (mounted) {
                    setUpdateAvailable(true);
                  }
                }
              });
            }
          });

          // Listen for controller changes (new service worker activated)
          navigator.serviceWorker.addEventListener('controllerchange', () => {
            if (mounted) {
              setUpdateAvailable(false);
              window.location.reload();
            }
          });

          // Listen for custom update events
          const handleUpdateAvailable = () => {
            if (mounted) {
              setUpdateAvailable(true);
            }
          };
          window.addEventListener('sw-update-available', handleUpdateAvailable);

          return () => {
            window.removeEventListener('sw-update-available', handleUpdateAvailable);
          };
        } else {
          setStatus('unsupported');
        }
      } catch (error) {
        if (mounted) {
          console.error('Service worker initialization failed:', error);
          setStatus('error');
        }
      }
    };

    initializeServiceWorker();

    return () => {
      mounted = false;
    };
  }, []);

  const update = useCallback(async () => {
    if (!registration) {
      return;
    }

    try {
      await registration.update();
      const hasUpdate = await isUpdateAvailable();
      setUpdateAvailable(hasUpdate);
    } catch (error) {
      console.error('Failed to update service worker:', error);
    }
  }, [registration]);

  const skipWaitingSW = useCallback(() => {
    skipWaiting();
  }, []);

  const unregister = useCallback(async () => {
    try {
      await unregisterServiceWorker();
      setStatus('unsupported');
      setUpdateAvailable(false);
      setRegistration(null);
    } catch (error) {
      console.error('Failed to unregister service worker:', error);
    }
  }, []);

  const contextValue: ServiceWorkerContextType = {
    status,
    isUpdateAvailable: updateAvailable,
    update,
    skipWaiting: skipWaitingSW,
    unregister,
  };

  return (
    <ServiceWorkerContext.Provider value={contextValue}>
      {children}
    </ServiceWorkerContext.Provider>
  );
};

export const useServiceWorker = () => {
  const context = useContext(ServiceWorkerContext);
  if (!context) {
    throw new Error('useServiceWorker must be used within a ServiceWorkerProvider');
  }
  return context;
};
