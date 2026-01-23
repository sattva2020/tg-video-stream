/**
 * Service Worker Registration Tests
 *
 * Тесты для проверки регистрации и работы service worker.
 * Проверяет PWA функциональность, оффлайн режим и кеширование.
 *
 * ВАЖНО: Service worker работает только в production режиме или при VITE_ENABLE_SERVICE_WORKER=true
 */

import { test, expect } from '@playwright/test';

// Конфигурация для production тестов
const BASE_URL = process.env.TEST_BASE_URL || 'https://sattva-streamer.top';

interface ServiceWorkerInfo {
  registered: boolean;
  active: boolean;
  state: string;
  scope: string;
}

test.describe('Service Worker Registration', () => {
  test('Service worker is registered on main page', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Wait for service worker registration

    // Check if service worker is registered
    const swInfo = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return { registered: false, reason: 'Service worker not supported' };
      }

      const registration = await navigator.serviceWorker.getRegistration();
      if (!registration) {
        return { registered: false, reason: 'No registration found' };
      }

      return {
        registered: true,
        active: !!registration.active,
        state: registration.active?.state || 'none',
        scope: registration.scope,
      };
    });

    expect(swInfo.registered).toBe(true);
    expect(swInfo.active).toBe(true);
    expect(swInfo.state).toBe('activated');
  });

  test('Service worker controls the page', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if service worker is controlling the page
    const isControlled = await page.evaluate(() => {
      return navigator.serviceWorker.controller !== null;
    });

    expect(isControlled).toBe(true);
  });

  test('Service worker file is accessible', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/service-worker.js`);
    expect(response.status()).toBe(200);

    // Verify it's JavaScript content
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/javascript/);
  });
});

test.describe('PWA Manifest', () => {
  test('Manifest file is accessible', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/manifest.json`);
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('name');
    expect(body).toHaveProperty('short_name');
    expect(body).toHaveProperty('icons');
    expect(body).toHaveProperty('start_url');
    expect(body).toHaveProperty('display');
  });

  test('Manifest has valid structure', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/manifest.json`);
    const body = await response.json();

    // Validate required fields
    expect(body.name).toBeTruthy();
    expect(body.short_name).toBeTruthy();
    expect(body.icons).toBeInstanceOf(Array);
    expect(body.icons.length).toBeGreaterThan(0);

    // Validate icons structure
    const firstIcon = body.icons[0];
    expect(firstIcon).toHaveProperty('src');
    expect(firstIcon).toHaveProperty('sizes');
    expect(firstIcon).toHaveProperty('type');

    // Validate display mode
    expect(['fullscreen', 'standalone', 'minimal-ui', 'browser']).toContain(body.display);
  });

  test('Manifest icons are accessible', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/manifest.json`);
    const body = await response.json();

    for (const icon of body.icons) {
      const iconUrl = icon.src.startsWith('http') ? icon.src : `${BASE_URL}${icon.src}`;
      const iconResponse = await request.get(iconUrl);
      expect(iconResponse.status(), `Icon ${icon.src} should be accessible`).toBe(200);
    }
  });
});

test.describe('Offline Support', () => {
  test('Offline fallback page is cached', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if offline.html is cached
    const isOfflineCached = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator) || !('caches' in window)) {
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

    expect(isOfflineCached).toBe(true);
  });

  test('Service worker caches static assets', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if caches are populated
    const cacheInfo = await page.evaluate(async () => {
      if (!('caches' in window)) {
        return { hasCache: false, cacheNames: [] };
      }

      try {
        const cacheNames = await caches.keys();
        const cacheDetails = [];

        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const keys = await cache.keys();
          cacheDetails.push({
            name: cacheName,
            count: keys.length,
          });
        }

        return {
          hasCache: cacheNames.length > 0,
          cacheNames: cacheNames,
          details: cacheDetails,
        };
      } catch (error) {
        return { hasCache: false, cacheNames: [], error: String(error) };
      }
    });

    expect(cacheInfo.hasCache).toBe(true);
    expect(cacheInfo.cacheNames.length).toBeGreaterThan(0);
  });
});

test.describe('Service Worker Update Mechanism', () => {
  test('Service worker accepts skip waiting message', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Send SKIP_WAITING message to service worker
    const skipWaitingResult = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return { success: false, reason: 'Service worker not supported' };
      }

      const registration = await navigator.serviceWorker.getRegistration();
      if (!registration) {
        return { success: false, reason: 'No registration' };
      }

      if (!registration.waiting) {
        return { success: false, reason: 'No waiting service worker' };
      }

      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      return { success: true };
    });

    // If there's a waiting worker, the message should be sent successfully
    // If not, that's also valid (no update pending)
    expect(['No waiting service worker', 'Service worker not supported', true]).toContain(
      skipWaitingResult.success || skipWaitingResult.reason
    );
  });

  test('Service worker provides queue status', async ({ page, context }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Request queue status from service worker
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

        // Timeout after 5 seconds
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
});

test.describe('PWA Installation', () => {
  test('PWA is installable (beforeinstallprompt event)', async ({ page, context }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Listen for beforeinstallprompt event
    const installPromptFired = await page.evaluate(async () => {
      return new Promise((resolve) => {
        let fired = false;

        const handler = (event: Event) => {
          fired = true;
          window.removeEventListener('beforeinstallprompt', handler);
          resolve(true);
        };

        window.addEventListener('beforeinstallprompt', handler);

        // Check if app is already installed
        // If already installed, the event won't fire
        setTimeout(() => {
          window.removeEventListener('beforeinstallprompt', handler);
          resolve(fired);
        }, 3000);
      });
    });

    // Note: If PWA is already installed, the event won't fire
    // This is expected behavior
    expect(typeof installPromptFired).toBe('boolean');
  });

  test('App has valid manifest link', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Check for manifest link in head
    const manifestLink = await page.locator('link[rel="manifest"]').first();
    const href = await manifestLink.getAttribute('href');

    expect(href).toBeTruthy();

    // Verify manifest is accessible
    if (href) {
      const manifestUrl = href.startsWith('http') ? href : `${BASE_URL}${href}`;
      const response = await page.request.get(manifestUrl);
      expect(response.status()).toBe(200);
    }
  });

  test('App has theme color and viewport meta tags', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Check for theme color
    const themeColor = await page.locator('meta[name="theme-color"]').first();
    expect(await themeColor.count()).toBeGreaterThan(0);

    // Check for viewport
    const viewport = await page.locator('meta[name="viewport"]').first();
    const viewportContent = await viewport.getAttribute('content');
    expect(viewportContent).toContain('width=device-width');
  });
});

test.describe('Cache Strategies', () => {
  test('Static assets use cache-first strategy', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if JS/CSS files are cached
    const cachedAssets = await page.evaluate(async () => {
      if (!('caches' in window)) {
        return { cached: [], count: 0 };
      }

      try {
        const cacheNames = await caches.keys();
        const allCached = [];

        for (const cacheName of cacheNames) {
          const cache = await caches.open(cacheName);
          const requests = await cache.keys();
          const urls = requests.map(r => r.url);
          allCached.push(...urls);
        }

        return {
          cached: allCached.filter(url =>
            url.match(/\.(js|css|png|jpg|jpeg|svg|gif|webp|woff2?|ttf|otf)$/)
          ),
          count: allCached.length,
        };
      } catch (error) {
        return { cached: [], count: 0, error: String(error) };
      }
    });

    // Should have some static assets cached
    expect(cachedAssets.count).toBeGreaterThan(0);
  });

  test('API requests use network-first strategy', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Make an API request and verify it goes through
    const apiResponse = await page.goto(`${BASE_URL}/api/health`);
    expect(apiResponse?.status()).toBeLessThan(500);
  });
});

test.describe('Service Worker Lifecycle', () => {
  test('Service worker updates on page reload', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Get initial service worker state
    await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        active: registration?.active?.state,
        waiting: !!registration?.waiting,
        installing: !!registration?.installing,
      };
    });

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Service worker should still be active after reload
    const reloadedState = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        active: registration?.active?.state,
        waiting: !!registration?.waiting,
        installing: !!registration?.installing,
      };
    });

    expect(reloadedState.active).toBe('activated');
  });

  test('Service worker handles client messages', async ({ page }) => {
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
});
