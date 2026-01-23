/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

// Cache names - versioned to allow for easy cache invalidation
const CACHE_NAMES = {
  static: 'static-cache-v1',
  assets: 'assets-cache-v1',
} as const;

// Assets to cache on install - static files and critical resources
const PRECACHE_URLS = [
  '/',
  '/offline.html', // Fallback page for offline navigation
] as const;

/**
 * Cache-first strategy for static assets
 * Checks cache first, falls back to network if not found
 */
const cacheFirst = async (request: Request): Promise<Response> => {
  const cache = await caches.open(CACHE_NAMES.static);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    // Cache successful responses for future use
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Return offline fallback for HTML requests
    if (request.headers.get('accept')?.includes('text/html')) {
      const cache = await caches.open(CACHE_NAMES.static);
      const offlineFallback = await cache.match('/offline.html');
      if (offlineFallback) {
        return offlineFallback;
      }
    }
    throw error;
  }
};

/**
 * Network-first strategy for API requests
 * Tries network first, falls back to cache if offline
 */
const networkFirst = async (request: Request): Promise<Response> => {
  const cache = await caches.open(CACHE_NAMES.static);

  try {
    const networkResponse = await fetch(request);
    // Cache successful responses for offline use
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
};

/**
 * Determine which caching strategy to use based on the request
 */
const getStrategyForRequest = (request: Request): (() => Promise<Response>) => {
  const url = new URL(request.url);

  // API requests - use network-first
  if (url.pathname.startsWith('/api')) {
    return () => networkFirst(request);
  }

  // Static assets - use cache-first
  // This includes JS, CSS, images, fonts, etc.
  if (
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'image' ||
    request.destination === 'font' ||
    url.pathname.match(/\.(js|css|png|jpg|jpeg|svg|gif|webp|woff2?|ttf|otf)$/)
  ) {
    return () => cacheFirst(request);
  }

  // HTML navigation requests - use network-first
  if (request.mode === 'navigate') {
    return () => networkFirst(request);
  }

  // Default to network-first
  return () => networkFirst(request);
};

/**
 * Install event - precache critical static assets
 */
self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAMES.static);
      // Cache critical URLs
      await cache.addAll(PRECACHE_URLS);
      // Skip waiting to activate immediately
      self.skipWaiting();
    })()
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    (async () => {
      // Get all cache names
      const cacheNames = await caches.keys();
      // Delete old caches that aren't in our current cache names
      await Promise.all(
        cacheNames
          .filter((name) => !Object.values(CACHE_NAMES).includes(name as keyof typeof CACHE_NAMES))
          .map((name) => caches.delete(name))
      );
      // Take control of all clients immediately
      self.clients.claim();
    })()
  );
});

/**
 * Fetch event - handle requests with appropriate caching strategies
 */
self.addEventListener('fetch', (event: FetchEvent) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  const strategy = getStrategyForRequest(event.request);
  event.respondWith(strategy());
});

/**
 * Message event - handle messages from clients
 * Used for manual cache updates, skip waiting, etc.
 */
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

export {};
