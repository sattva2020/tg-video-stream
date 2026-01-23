/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

// Cache names - versioned to allow for easy cache invalidation
const CACHE_NAMES = {
  static: 'static-cache-v1',
  assets: 'assets-cache-v1',
  offlineQueue: 'offline-queue-v1',
} as const;

// Assets to cache on install - static files and critical resources
const PRECACHE_URLS = [
  '/',
  '/offline.html', // Fallback page for offline navigation
] as const;

// IndexedDB database for offline request queue
const QUEUE_DB_NAME = 'offline-queue';
const QUEUE_STORE_NAME = 'requests';
const QUEUE_SYNC_TAG = 'offline-requests';
const MAX_RETRY_ATTEMPTS = 3;

// Interface for queued request
interface QueuedRequest {
  id: string;
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: string;
  timestamp: number;
  retries: number;
}

/**
 * Open IndexedDB for queue storage
 */
const openQueueDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(QUEUE_DB_NAME, 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(QUEUE_STORE_NAME)) {
        db.createObjectStore(QUEUE_STORE_NAME, { keyPath: 'id' });
      }
    };
  });
};

/**
 * Save a request to the offline queue
 */
const saveRequestToQueue = async (request: Request, requestBody?: string): Promise<void> => {
  try {
    const db = await openQueueDB();
    const transaction = db.transaction(QUEUE_STORE_NAME, 'readwrite');
    const store = transaction.objectStore(QUEUE_STORE_NAME);

    const queuedRequest: QueuedRequest = {
      id: crypto.randomUUID(),
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: requestBody,
      timestamp: Date.now(),
      retries: 0,
    };

    store.add(queuedRequest);

    // Register background sync
    if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
      await self.registration.sync.register(QUEUE_SYNC_TAG);
    }

    db.close();
  } catch (error) {
    // Silently fail - queue is best-effort
  }
};

/**
 * Get all queued requests
 */
const getQueuedRequests = async (): Promise<QueuedRequest[]> => {
  try {
    const db = await openQueueDB();
    const transaction = db.transaction(QUEUE_STORE_NAME, 'readonly');
    const store = transaction.objectStore(QUEUE_STORE_NAME);
    const request = store.getAll();

    return new Promise((resolve, reject) => {
      request.onsuccess = () => {
        db.close();
        resolve(request.result as QueuedRequest[]);
      };
      request.onerror = () => {
        db.close();
        reject(request.error);
      };
    });
  } catch (error) {
    return [];
  }
};

/**
 * Remove a request from the queue
 */
const removeRequestFromQueue = async (id: string): Promise<void> => {
  try {
    const db = await openQueueDB();
    const transaction = db.transaction(QUEUE_STORE_NAME, 'readwrite');
    const store = transaction.objectStore(QUEUE_STORE_NAME);
    store.delete(id);

    transaction.oncomplete = () => db.close();
    transaction.onerror = () => db.close();
  } catch (error) {
    // Silently fail
  }
};

/**
 * Update request retry count
 */
const updateRequestRetry = async (queuedRequest: QueuedRequest): Promise<void> => {
  try {
    const db = await openQueueDB();
    const transaction = db.transaction(QUEUE_STORE_NAME, 'readwrite');
    const store = transaction.objectStore(QUEUE_STORE_NAME);

    queuedRequest.retries += 1;
    store.put(queuedRequest);

    transaction.oncomplete = () => db.close();
    transaction.onerror = () => db.close();
  } catch (error) {
    // Silently fail
  }
};

/**
 * Sync all queued requests
 */
const syncQueuedRequests = async (): Promise<void> => {
  const queuedRequests = await getQueuedRequests();

  for (const queuedRequest of queuedRequests) {
    // Skip requests that have exceeded max retries
    if (queuedRequest.retries >= MAX_RETRY_ATTEMPTS) {
      await removeRequestFromQueue(queuedRequest.id);
      continue;
    }

    try {
      // Reconstruct the request
      const requestInit: RequestInit = {
        method: queuedRequest.method,
        headers: queuedRequest.headers,
      };

      if (queuedRequest.body) {
        requestInit.body = queuedRequest.body;
      }

      const response = await fetch(queuedRequest.url, requestInit);

      // If successful, remove from queue
      if (response.ok) {
        await removeRequestFromQueue(queuedRequest.id);
      } else {
        // If failed, increment retry count
        await updateRequestRetry(queuedRequest);
      }
    } catch (error) {
      // Network error or fetch failed - increment retry count
      await updateRequestRetry(queuedRequest);
    }
  }

  // Notify clients about sync completion
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({
      type: 'SYNC_COMPLETE',
      timestamp: Date.now(),
    });
  });
};

/**
 * Get queue status for client requests
 */
const getQueueStatus = async (): Promise<{ count: number; requests: QueuedRequest[] }> => {
  const requests = await getQueuedRequests();
  return {
    count: requests.length,
    requests,
  };
};

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
  // Skip chrome-extension and other non-http(s) requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  const url = new URL(event.request.url);

  // Handle API requests
  if (url.pathname.startsWith('/api')) {
    // For GET requests, use network-first strategy
    if (event.request.method === 'GET') {
      event.respondWith(networkFirst(event.request));
      return;
    }

    // For non-GET requests (POST, PUT, PATCH, DELETE), queue if offline
    event.respondWith(
      (async () => {
        try {
          const response = await fetch(event.request.clone());
          return response;
        } catch (error) {
          // Queue the request for background sync
          const requestBody = await event.request.clone().text();
          await saveRequestToQueue(event.request.clone(), requestBody);

          // Return a synthetic response indicating the request was queued
          return new Response(
            JSON.stringify({
              queued: true,
              message: 'Request queued for background sync',
            }),
            {
              status: 202,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
      })()
    );
    return;
  }

  // For non-API requests, skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  const strategy = getStrategyForRequest(event.request);
  event.respondWith(strategy());
});

/**
 * Sync event - handle background sync for offline requests
 */
self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === QUEUE_SYNC_TAG) {
    event.waitUntil(syncQueuedRequests());
  }
});

/**
 * Message event - handle messages from clients
 * Used for manual cache updates, skip waiting, sync status, etc.
 */
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'GET_QUEUE_STATUS') {
    event.waitUntil(
      (async () => {
        const status = await getQueueStatus();
        // Send response back to client
        event.ports[0]?.postMessage(status);
      })()
    );
  }

  if (event.data && event.data.type === 'SYNC_NOW') {
    event.waitUntil(syncQueuedRequests());
  }
});

export {};
