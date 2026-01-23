/**
 * Service Worker Registration Module
 * Handles registration and lifecycle of the service worker for PWA functionality.
 */

const SERVICE_WORKER_URL = '/service-worker.js';

/**
 * Register the service worker for PWA functionality.
 * Should be called in main.tsx after app initialization.
 *
 * @returns Promise that resolves when registration is complete or rejected on error
 */
export function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  // Check if service workers are supported
  if (!('serviceWorker' in navigator)) {
    console.warn('⚠️  Service workers are not supported in this browser');
    return Promise.resolve(null);
  }

  // Only register in production or when explicitly enabled
  const isProduction = import.meta.env.PROD;
  const enableSW = import.meta.env.VITE_ENABLE_SERVICE_WORKER === 'true';

  if (!isProduction && !enableSW) {
    console.log('ℹ️  Service worker registration skipped (development mode)');
    return Promise.resolve(null);
  }

  return navigator.serviceWorker
    .register(SERVICE_WORKER_URL)
    .then((registration) => {
      console.log('✅ Service worker registered successfully:', registration.scope);

      // Check for updates periodically
      setInterval(() => {
        registration.update();
      }, 60 * 60 * 1000); // Check every hour

      // Handle updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New version available
              console.log('🔄 New service worker available. Refresh to update.');

              // Notify the user (you could add a toast notification here)
              window.dispatchEvent(new CustomEvent('sw-update-available'));
            }
          });
        }
      });

      return registration;
    })
    .catch((error) => {
      // Handle registration errors
      console.error('❌ Service worker registration failed:', error);
      return null;
    });
}

/**
 * Unregister the service worker.
 * Useful for testing or disabling PWA functionality.
 */
export async function unregisterServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();

    await Promise.all(
      registrations.map((registration) => {
        console.log('🗑️  Unregistering service worker:', registration.scope);
        return registration.unregister();
      })
    );

    console.log('✅ All service workers unregistered');
  } catch (error) {
    console.error('❌ Failed to unregister service worker:', error);
  }
}

/**
 * Request the service worker to skip waiting and activate immediately.
 * Call this when you want to immediately activate a waiting service worker.
 */
export function skipWaiting(): void {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  navigator.serviceWorker.ready.then((registration) => {
    if (registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      console.log('🔄 Service worker skip waiting requested');
    }
  });
}

/**
 * Get the current service worker registration.
 * Useful for checking the status of the service worker.
 */
export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    return null;
  }

  try {
    return await navigator.serviceWorker.getRegistration();
  } catch (error) {
    console.error('❌ Failed to get service worker registration:', error);
    return null;
  }
}

/**
 * Check if a new service worker is waiting to be activated.
 */
export async function isUpdateAvailable(): Promise<boolean> {
  const registration = await getServiceWorkerRegistration();
  return registration?.waiting !== undefined;
}
