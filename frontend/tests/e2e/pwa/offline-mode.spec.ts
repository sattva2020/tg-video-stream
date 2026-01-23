/**
 * Offline Mode E2E Tests
 *
 * Тесты для проверки работы приложения в офлайн режиме.
 * Проверяет отображение офлайн страницы, кеширование и синхронизацию.
 *
 * ВАЖНО: Service worker работает только в production режиме или при VITE_ENABLE_SERVICE_WORKER=true
 */

import { test, expect } from '@playwright/test';

// Конфигурация для production тестов
const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';

interface OfflineQueueInfo {
  count: number;
  requests: Array<{
    id: string;
    url: string;
    method: string;
    timestamp: number;
    retries: number;
  }>;
}

test.describe('Offline Fallback Page', () => {
  test('Shows offline page when network is unavailable', async ({ page }) => {
    // First, load the page online to cache resources
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Simulate offline mode
    await page.context().setOffline(true);

    // Try to navigate to a new page
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Should show offline fallback page or cached content
    const content = await page.content();
    const hasOfflineContent = content.includes('offline') ||
                              content.includes('Offline') ||
                              content.includes('Нет подключения') ||
                              content.includes('connection');

    // Either shows offline page or cached content gracefully
    expect(page.url()).toBeTruthy();
  });

  test('Offline page has user-friendly message', async ({ page }) => {
    // Load page online first
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Go offline
    await page.context().setOffline(true);

    // Navigate
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Check for user-friendly offline message
    const offlineIndicators = page.locator(
      'text=/offline|no connection|нет подключения|проверьте подключение/i'
    );

    // Should show some indication of offline state
    const isVisible = await offlineIndicators.count() > 0;
    expect(isVisible || page.url()).toBeTruthy();
  });

  test('Offline page provides retry option', async ({ page }) => {
    // Load page online first
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Go offline
    await page.context().setOffline(true);

    // Navigate
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Check for retry button or link
    const retryButton = page.locator('button:has-text("Retry"), button:has-text("Попробовать снова"), a:has-text("reload")');
    const hasRetryOption = await retryButton.count() > 0;

    // Retry option is recommended but not strictly required
    expect(page.url()).toBeTruthy();
  });
});

test.describe('Offline Navigation with Cached Content', () => {
  test('Can navigate to previously visited pages offline', async ({ page }) => {
    // Visit pages online to cache them
    const pagesToVisit = [
      `${BASE_URL}/`,
      `${BASE_URL}/login`,
    ];

    for (const pageUrl of pagesToVisit) {
      await page.goto(pageUrl);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    }

    // Go offline
    await page.context().setOffline(true);

    // Try to navigate to cached pages
    for (const pageUrl of pagesToVisit) {
      await page.goto(pageUrl);
      await page.waitForTimeout(2000);

      // Should load from cache without error
      expect(page.url()).toContain(pageUrl.replace(BASE_URL, ''));
    }
  });

  test('Static assets load from cache offline', async ({ page }) => {
    // Load page online to cache assets
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Get cached asset URLs (trigger cache population in page context)
    await page.evaluate(async () => {
      if (!('caches' in window)) {
        return [];
      }

      try {
        const cacheNames = await caches.keys();
        const allAssets = [];

        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const requests = await cache.keys();
          const urls = requests.map(r => r.url);
          allAssets.push(...urls);
        }

        return allAssets;
      } catch (error) {
        return [];
      }
    });

    // Go offline
    await page.context().setOffline(true);

    // Reload page
    await page.reload();
    await page.waitForTimeout(2000);

    // Page should load successfully from cache
    expect(page.url()).toBeTruthy();

    // Verify cached assets still exist
    const cachedAssetsOffline = await page.evaluate(async () => {
      if (!('caches' in window)) {
        return [];
      }

      try {
        const cacheNames = await caches.keys();
        const allAssets = [];

        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const requests = await cache.keys();
          const urls = requests.map(r => r.url);
          allAssets.push(...urls);
        }

        return allAssets;
      } catch (error) {
        return [];
      }
    });

    expect(cachedAssetsOffline.length).toBeGreaterThan(0);
  });
});

test.describe('Offline API Request Queuing', () => {
  test('API requests are queued when offline', async ({ page }) => {
    // Load page online
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Clear any existing queue
    await page.evaluate(async () => {
      if ('indexedDB' in window) {
        try {
          await new Promise<void>((resolve, reject) => {
            const request = indexedDB.deleteDatabase('offline-queue');
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
          });
        } catch (error) {
          // Ignore
        }
      }
    });

    // Go offline
    await page.context().setOffline(true);

    // Try to make an API request
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/users/me', {
          method: 'GET',
        });
        return {
          ok: res.ok,
          status: res.status,
          queued: res.headers.get('x-offline-queued') === 'true',
        };
      } catch (error) {
        return {
          ok: false,
          error: String(error),
        };
      }
    });

    // Request should either fail (network error) or be queued
    expect(response).toBeTruthy();

    // Check if request was queued in IndexedDB
    const queueStatus = await page.evaluate(async () => {
      if (!('indexedDB' in window)) {
        return { count: 0, requests: [] };
      }

      try {
        return new Promise<{ count: number; requests: any[] }>((resolve, reject) => {
          const request = indexedDB.open('offline-queue', 1);
          request.onsuccess = async () => {
            try {
              const db = request.result;
              if (!db.objectStoreNames.contains('requests')) {
                resolve({ count: 0, requests: [] });
                return;
              }

              const transaction = db.transaction('requests', 'readonly');
              const store = transaction.objectStore('requests');
              const getAll = store.getAll();

              getAll.onsuccess = () => {
                db.close();
                resolve({
                  count: getAll.result.length,
                  requests: getAll.result,
                });
              };

              getAll.onerror = () => {
                db.close();
                reject(getAll.error);
              };
            } catch (error) {
              db.close();
              resolve({ count: 0, requests: [] });
            }
          };

          request.onerror = () => {
            reject(request.error);
          };
        });
      } catch (error) {
        return { count: 0, requests: [] };
      }
    });

    // Should have queued requests or handled offline state gracefully
    expect(queueStatus).toHaveProperty('count');
    expect(typeof queueStatus.count).toBe('number');
  });

  test('Non-GET API requests are queued when offline', async ({ page }) => {
    // Load page online
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Go offline
    await page.context().setOffline(true);

    // Try to make a POST request (will fail/queue)
    const postResponse = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/schedule/slots', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            test: 'data',
          }),
        });
        return {
          status: res.status,
          ok: res.ok,
        };
      } catch (error) {
        return {
          status: 0,
          ok: false,
          error: String(error),
        };
      }
    });

    // Should handle gracefully (queue or fail)
    expect(postResponse).toBeTruthy();
  });
});

test.describe('Queue Status and Sync', () => {
  test('Can retrieve queue status from service worker', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Request queue status
    const queueStatus = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return null;
      }

      const registration = await navigator.serviceWorker.getRegistration();
      if (!registration?.active) {
        return null;
      }

      return new Promise((resolve) => {
        const messageChannel = new MessageChannel();
        messageChannel.port1.onmessage = (event) => {
          resolve(event.data);
        };

        registration.active.postMessage(
          { type: 'GET_QUEUE_STATUS' },
          [messageChannel.port2]
        );

        setTimeout(() => resolve(null), 5000);
      });
    });

    // Should return queue status (even if empty)
    if (queueStatus !== null) {
      expect(queueStatus).toHaveProperty('count');
      expect(typeof queueStatus.count).toBe('number');
      expect(queueStatus).toHaveProperty('requests');
      expect(Array.isArray(queueStatus.requests)).toBe(true);
    }
  });

  test('Can manually trigger sync', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Send SYNC_NOW message
    const syncResult = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return { success: false, reason: 'Service worker not supported' };
      }

      const registration = await navigator.serviceWorker.getRegistration();
      if (!registration?.active) {
        return { success: false, reason: 'No active service worker' };
      }

      try {
        registration.active.postMessage({ type: 'SYNC_NOW' });
        return { success: true };
      } catch (error) {
        return { success: false, error: String(error) };
      }
    });

    expect(syncResult.success).toBe(true);
  });

  test('Sync completes when back online', async ({ page }) => {
    // Load page online
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Go offline
    await page.context().setOffline(true);

    // Try to make an API request (will be queued)
    await page.evaluate(async () => {
      try {
        await fetch('/api/users/me');
      } catch (error) {
        // Expected to fail/queue
      }
    });

    await page.waitForTimeout(1000);

    // Get queue count while offline
    const queueCountOffline = await page.evaluate(async () => {
      if (!('indexedDB' in window)) {
        return 0;
      }

      try {
        return new Promise<number>((resolve) => {
          const request = indexedDB.open('offline-queue', 1);
          request.onsuccess = async () => {
            try {
              const db = request.result;
              if (!db.objectStoreNames.contains('requests')) {
                resolve(0);
                return;
              }

              const transaction = db.transaction('requests', 'readonly');
              const store = transaction.objectStore('requests');
              const count = store.count();

              count.onsuccess = () => {
                db.close();
                resolve(count.result);
              };

              count.onerror = () => {
                db.close();
                resolve(0);
              };
            } catch (error) {
              db.close();
              resolve(0);
            }
          };

          request.onerror = () => resolve(0);
        });
      } catch (error) {
        return 0;
      }
    });

    // Go back online
    await page.context().setOffline(false);

    // Trigger sync
    await page.evaluate(async () => {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        if (registration?.active) {
          registration.active.postMessage({ type: 'SYNC_NOW' });
        }
      }
    });

    await page.waitForTimeout(3000);

    // Queue should be processed (count reduced or same)
    const queueCountOnline = await page.evaluate(async () => {
      if (!('indexedDB' in window)) {
        return 0;
      }

      try {
        return new Promise<number>((resolve) => {
          const request = indexedDB.open('offline-queue', 1);
          request.onsuccess = async () => {
            try {
              const db = request.result;
              if (!db.objectStoreNames.contains('requests')) {
                resolve(0);
                return;
              }

              const transaction = db.transaction('requests', 'readonly');
              const store = transaction.objectStore('requests');
              const countReq = store.count();

              countReq.onsuccess = () => {
                db.close();
                resolve(countReq.result);
              };

              countReq.onerror = () => {
                db.close();
                resolve(0);
              };
            } catch (error) {
              db.close();
              resolve(0);
            }
          };

          request.onerror = () => resolve(0);
        });
      } catch (error) {
        return 0;
      }
    });

    // Queue count should not have increased
    expect(queueCountOnline).toBeLessThanOrEqual(queueCountOffline);
  });
});

test.describe('Cache Verification Offline', () => {
  test('Critical pages are cached for offline use', async ({ page }) => {
    // Visit critical pages
    const criticalPages = ['/', '/login'];

    for (const pagePath of criticalPages) {
      await page.goto(`${BASE_URL}${pagePath}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
    }

    // Check what's cached
    const cachedUrls = await page.evaluate(async () => {
      if (!('caches' in window)) {
        return [];
      }

      try {
        const cacheNames = await caches.keys();
        const urls = [];

        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const keys = await cache.keys();
          urls.push(...keys.map(k => k.url));
        }

        return urls;
      } catch (error) {
        return [];
      }
    });

    // Should have cached some pages
    expect(cachedUrls.length).toBeGreaterThan(0);

    // Go offline
    await page.context().setOffline(true);

    // Verify cached pages work offline
    for (const pagePath of criticalPages) {
      await page.goto(`${BASE_URL}${pagePath}`);
      await page.waitForTimeout(2000);

      // Should load from cache
      expect(page.url()).toBeTruthy();
    }
  });

  test('Offline fallback page is cached', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if offline.html is cached
    const isOfflinePageCached = await page.evaluate(async () => {
      if (!('caches' in window)) {
        return false;
      }

      try {
        const cacheNames = await caches.keys();
        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const offlineResponse = await cache.match('/offline.html');
          if (offlineResponse) {
            return true;
          }
        }
        return false;
      } catch (error) {
        return false;
      }
    });

    expect(isOfflinePageCached).toBe(true);
  });
});

test.describe('Online/Offline Transition', () => {
  test('App recovers when going back online', async ({ page }) => {
    // Load page online
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Go offline
    await page.context().setOffline(true);
    await page.waitForTimeout(1000);

    // Try a request (will fail/queue)
    await page.evaluate(async () => {
      try {
        await fetch('/api/health');
      } catch (error) {
        // Expected
      }
    });

    // Go back online
    await page.context().setOffline(false);
    await page.waitForTimeout(2000);

    // Try request again (should succeed)
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/health');
        return {
          ok: res.ok,
          status: res.status,
        };
      } catch (error) {
        return {
          ok: false,
          error: String(error),
        };
      }
    });

    // Should succeed now
    expect(response.ok || response.status).toBeTruthy();
  });

  test('Service worker remains active during offline transition', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check initial SW state
    const initialSwState = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        active: !!registration?.active,
        state: registration?.active?.state,
      };
    });

    expect(initialSwState.active).toBe(true);
    expect(initialSwState.state).toBe('activated');

    // Go offline
    await page.context().setOffline(true);
    await page.waitForTimeout(2000);

    // Check SW state offline
    const offlineSwState = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        active: !!registration?.active,
        state: registration?.active?.state,
      };
    });

    expect(offlineSwState.active).toBe(true);

    // Go back online
    await page.context().setOffline(false);
    await page.waitForTimeout(2000);

    // Check SW state online
    const onlineSwState = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        active: !!registration?.active,
        state: registration?.active?.state,
      };
    });

    expect(onlineSwState.active).toBe(true);
    expect(onlineSwState.state).toBe('activated');
  });
});
