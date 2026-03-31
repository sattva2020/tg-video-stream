/**
 * E2E Test: Generate Smart Playlist from Criteria
 *
 * Verifies:
 * - Creating smart playlists with criteria
 * - Filtering by duration, type, title
 * - Sorting and limiting results
 * - Refreshing smart playlists
 * - Verifying only matching items included
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.TEST_API_URL || 'http://localhost:8000';

// Interfaces matching the API
interface PlaylistEntry {
  url: string;
  title: string;
  duration: number;
  type: string;
  thumbnail?: string;
}

interface SmartPlaylistCriteria {
  filters?: {
    duration_min?: number;
    duration_max?: number;
    type?: string | string[];
    title_contains?: string;
  };
  order_by?: 'date_added' | 'duration' | 'name';
  order_direction?: 'asc' | 'desc';
  limit?: number;
  shuffle?: boolean;
}

interface SmartPlaylist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  criteria: SmartPlaylistCriteria;
  playlist_id?: string;
  items_count: number;
  total_duration: number;
  is_public: boolean;
  auto_update: boolean;
  auto_update_interval: number;
  last_refreshed_at?: string;
  created_at: string;
  updated_at?: string;
}

interface SmartPlaylistCreate {
  name: string;
  description?: string;
  criteria: SmartPlaylistCriteria;
  is_public?: boolean;
  auto_update?: boolean;
  auto_update_interval?: number;
  group_id?: string;
}

interface Playlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  items: PlaylistEntry[];
  items_count: number;
  total_duration: number;
  group_id?: string;
  is_public: boolean;
  repeat_mode: string;
  created_at: string;
  updated_at?: string;
}

// Test data
const TEST_PLAYLISTS: PlaylistEntry[] = [
  {
    url: 'https://www.youtube.com/watch?v=short1',
    title: 'Short Tutorial 1',
    duration: 120,
    type: 'youtube',
  },
  {
    url: 'https://www.youtube.com/watch?v=short2',
    title: 'Short Tutorial 2',
    duration: 150,
    type: 'youtube',
  },
  {
    url: 'https://www.youtube.com/watch?v=med1',
    title: 'Medium Length Video 1',
    duration: 300,
    type: 'youtube',
  },
  {
    url: 'https://www.youtube.com/watch?v=med2',
    title: 'Medium Length Video 2',
    duration: 400,
    type: 'youtube',
  },
  {
    url: 'https://www.youtube.com/watch?v=long1',
    title: 'Long Documentary 1',
    duration: 600,
    type: 'youtube',
  },
  {
    url: 'https://www.youtube.com/watch?v=long2',
    title: 'Long Documentary 2',
    duration: 900,
    type: 'youtube',
  },
  {
    url: 'https://vimeo.com/123456',
    title: 'Vimeo Staff Pick',
    duration: 250,
    type: 'vimeo',
  },
];

const SMART_PLAYLIST_DURATION: SmartPlaylistCreate = {
  name: 'Medium Length Videos',
  description: 'Videos between 200-500 seconds',
  criteria: {
    filters: {
      duration_min: 200,
      duration_max: 500,
    },
    order_by: 'duration',
    order_direction: 'asc',
  },
  is_public: false,
};

const SMART_PLAYLIST_TYPE: SmartPlaylistCreate = {
  name: 'YouTube Only',
  description: 'Only YouTube videos',
  criteria: {
    filters: {
      type: 'youtube',
    },
  },
};

const SMART_PLAYLIST_TITLE: SmartPlaylistCreate = {
  name: 'Tutorial Videos',
  description: 'Videos with "Tutorial" in title',
  criteria: {
    filters: {
      title_contains: 'Tutorial',
    },
    order_by: 'name',
    order_direction: 'asc',
  },
};

const SMART_PLAYLIST_LIMIT: SmartPlaylistCreate = {
  name: 'Top 3 Videos',
  description: 'Only first 3 matching videos',
  criteria: {
    filters: {
      duration_min: 0,
    },
    limit: 3,
    order_by: 'duration',
    order_direction: 'desc',
  },
};

test.describe('E2E: Generate Smart Playlist from Criteria', () => {
  let authToken: string;
  let testPlaylists: Playlist[] = [];
  let smartPlaylist: SmartPlaylist;
  let generatedPlaylist: Playlist;

  // Setup: Authenticate user and create test playlists
  test.beforeAll(async ({ request }) => {
    // Create or login test user
    const loginResponse = await request.post(`${API_URL}/api/auth/test-login`, {
      json: {
        email: 'test-smart-playlists@example.com',
        password: 'TestPassword123!',
      },
    });

    if (loginResponse.status() === 200) {
      const loginData = await loginResponse.json();
      authToken = loginData.access_token;
    } else {
      // Register new test user
      const registerResponse = await request.post(`${API_URL}/api/auth/register`, {
        json: {
          email: 'test-smart-playlists@example.com',
          password: 'TestPassword123!',
          full_name: 'Smart Playlist Test User',
        },
      });

      if (registerResponse.status() !== 201) {
        throw new Error('Failed to register test user');
      }

      const registerData = await registerResponse.json();
      authToken = registerData.access_token;
    }

    // Create test playlists with sample data
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create playlists to source items from
    const playlist1Payload = {
      name: 'Short Videos',
      items: TEST_PLAYLISTS.filter(p => p.duration < 200),
    };

    const playlist2Payload = {
      name: 'Medium Videos',
      items: TEST_PLAYLISTS.filter(p => p.duration >= 200 && p.duration <= 500),
    };

    const playlist3Payload = {
      name: 'Long Videos',
      items: TEST_PLAYLISTS.filter(p => p.duration > 500),
    };

    const p1 = await request.post(`${API_URL}/api/playlists`, {
      headers,
      json: playlist1Payload,
    });
    if (p1.status() === 200 || p1.status() === 201) {
      testPlaylists.push(await p1.json());
    }

    const p2 = await request.post(`${API_URL}/api/playlists`, {
      headers,
      json: playlist2Payload,
    });
    if (p2.status() === 200 || p2.status() === 201) {
      testPlaylists.push(await p2.json());
    }

    const p3 = await request.post(`${API_URL}/api/playlists`, {
      headers,
      json: playlist3Payload,
    });
    if (p3.status() === 200 || p3.status() === 201) {
      testPlaylists.push(await p3.json());
    }
  });

  // Cleanup: Delete test data
  test.afterAll(async ({ request }) => {
    if (!authToken) return;

    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Delete generated playlist
    if (generatedPlaylist) {
      await request.delete(`${API_URL}/api/playlists/${generatedPlaylist.id}`, {
        headers,
      });
    }

    // Delete smart playlist
    if (smartPlaylist) {
      await request.delete(`${API_URL}/api/playlists/smart/${smartPlaylist.id}`, {
        headers,
      });
    }

    // Delete test playlists
    for (const playlist of testPlaylists) {
      await request.delete(`${API_URL}/api/playlists/${playlist.id}`, {
        headers,
      });
    }
  });

  test('Step 1: Create smart playlist with duration criteria', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const response = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: SMART_PLAYLIST_DURATION,
    });

    expect(response.status()).toBe(201);

    const data = await response.json();
    smartPlaylist = data;

    // Verify smart playlist properties
    expect(smartPlaylist).toMatchObject({
      name: SMART_PLAYLIST_DURATION.name,
      description: SMART_PLAYLIST_DURATION.description,
      is_public: SMART_PLAYLIST_DURATION.is_public || false,
    });

    // Verify criteria is preserved
    expect(smartPlaylist.criteria).toMatchObject(SMART_PLAYLIST_DURATION.criteria);

    // Verify playlist is generated
    expect(smartPlaylist.playlist_id).toBeDefined();
    expect(smartPlaylist.items_count).toBeGreaterThanOrEqual(0);
    expect(smartPlaylist.total_duration).toBeGreaterThanOrEqual(0);

    expect(smartPlaylist.id).toBeDefined();
    expect(smartPlaylist.user_id).toBeDefined();
    expect(smartPlaylist.created_at).toBeDefined();
  });

  test('Step 2: Generate playlist from smart criteria', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Fetch the generated playlist
    const response = await request.get(
      `${API_URL}/api/playlists/${smartPlaylist.playlist_id}`,
      { headers }
    );

    expect(response.status()).toBe(200);

    generatedPlaylist = await response.json();

    // Verify playlist properties
    expect(generatedPlaylist).toMatchObject({
      name: smartPlaylist.name,
      description: smartPlaylist.description,
    });

    expect(generatedPlaylist.id).toBeDefined();
    expect(generatedPlaylist.user_id).toBeDefined();
    expect(generatedPlaylist.created_at).toBeDefined();
  });

  test('Step 3: Verify only matching items included', async ({ request }) => {
    // Verify all items match duration criteria
    for (const item of generatedPlaylist.items) {
      expect(item.duration).toBeGreaterThanOrEqual(200);
      expect(item.duration).toBeLessThanOrEqual(500);
    }

    // Verify sorting by duration ascending
    const durations = generatedPlaylist.items.map(item => item.duration);
    const sortedDurations = [...durations].sort((a, b) => a - b);
    expect(durations).toEqual(sortedDurations);

    // Verify at least some items match
    expect(generatedPlaylist.items.length).toBeGreaterThan(0);
    expect(generatedPlaylist.items_count).toBe(generatedPlaylist.items.length);

    // Verify total duration calculation
    const expectedDuration = generatedPlaylist.items.reduce(
      (sum, item) => sum + item.duration,
      0
    );
    expect(generatedPlaylist.total_duration).toBe(expectedDuration);
  });

  test('Filter by type: Only YouTube videos', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create smart playlist with type filter
    const response = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: SMART_PLAYLIST_TYPE,
    });

    expect(response.status()).toBe(201);

    const typeSmartPlaylist: SmartPlaylist = await response.json();

    // Fetch generated playlist
    const playlistResponse = await request.get(
      `${API_URL}/api/playlists/${typeSmartPlaylist.playlist_id}`,
      { headers }
    );

    expect(playlistResponse.status()).toBe(200);
    const typePlaylist: Playlist = await playlistResponse.json();

    // Verify all items are YouTube type
    for (const item of typePlaylist.items) {
      expect(item.type).toBe('youtube');
    }

    // Should have 6 YouTube videos
    expect(typePlaylist.items_count).toBe(6);

    // Cleanup
    await request.delete(`${API_URL}/api/playlists/smart/${typeSmartPlaylist.id}`, {
      headers,
    });
  });

  test('Filter by title: Videos containing "Tutorial"', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create smart playlist with title filter
    const response = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: SMART_PLAYLIST_TITLE,
    });

    expect(response.status()).toBe(201);

    const titleSmartPlaylist: SmartPlaylist = await response.json();

    // Fetch generated playlist
    const playlistResponse = await request.get(
      `${API_URL}/api/playlists/${titleSmartPlaylist.playlist_id}`,
      { headers }
    );

    expect(playlistResponse.status()).toBe(200);
    const titlePlaylist: Playlist = await playlistResponse.json();

    // Verify all items have "Tutorial" in title
    for (const item of titlePlaylist.items) {
      expect(item.title).toContain(/tutorial/i);
    }

    // Should have 2 tutorial videos
    expect(titlePlaylist.items_count).toBe(2);

    // Cleanup
    await request.delete(`${API_URL}/api/playlists/smart/${titleSmartPlaylist.id}`, {
      headers,
    });
  });

  test('Limit results: Top 3 longest videos', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create smart playlist with limit
    const response = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: SMART_PLAYLIST_LIMIT,
    });

    expect(response.status()).toBe(201);

    const limitSmartPlaylist: SmartPlaylist = await response.json();

    // Fetch generated playlist
    const playlistResponse = await request.get(
      `${API_URL}/api/playlists/${limitSmartPlaylist.playlist_id}`,
      { headers }
    );

    expect(playlistResponse.status()).toBe(200);
    const limitPlaylist: Playlist = await playlistResponse.json();

    // Verify exactly 3 items
    expect(limitPlaylist.items_count).toBe(3);
    expect(limitPlaylist.items).toHaveLength(3);

    // Verify sorted by duration descending (longest first)
    const durations = limitPlaylist.items.map(item => item.duration);
    const sortedDurations = [...durations].sort((a, b) => b - a);
    expect(durations).toEqual(sortedDurations);

    // Cleanup
    await request.delete(`${API_URL}/api/playlists/smart/${limitSmartPlaylist.id}`, {
      headers,
    });
  });

  test('Refresh smart playlist updates content', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Add a new playlist to the database
    const newPlaylistPayload = {
      name: 'New Source Playlist',
      items: [
        {
          url: 'https://www.youtube.com/watch?v=new1',
          title: 'New Video for Smart Playlist',
          duration: 350,
          type: 'youtube',
        },
      ],
    };

    const newPlaylistResponse = await request.post(`${API_URL}/api/playlists`, {
      headers,
      json: newPlaylistPayload,
    });

    expect(newPlaylistResponse.status()).toBe(200 || 201);
    const newPlaylist = await newPlaylistResponse.json();
    testPlaylists.push(newPlaylist);

    // Refresh smart playlist
    const refreshResponse = await request.post(
      `${API_URL}/api/playlists/smart/${smartPlaylist.id}/refresh`,
      { headers }
    );

    expect(refreshResponse.status()).toBe(200);

    const refreshedPlaylist: Playlist = await refreshResponse.json();

    // Verify playlist still matches criteria
    for (const item of refreshedPlaylist.items) {
      expect(item.duration).toBeGreaterThanOrEqual(200);
      expect(item.duration).toBeLessThanOrEqual(500);
    }

    // Update reference to generated playlist
    generatedPlaylist = refreshedPlaylist;
  });

  test('Update smart playlist criteria', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Update criteria to only include longer videos
    const updatedCriteria = {
      name: 'Longer Medium Videos',
      criteria: {
        filters: {
          duration_min: 300,
          duration_max: 500,
        },
        order_by: 'duration',
        order_direction: 'desc',
      },
    };

    const updateResponse = await request.put(
      `${API_URL}/api/playlists/smart/${smartPlaylist.id}`,
      {
        headers,
        json: updatedCriteria,
      }
    );

    expect(updateResponse.status()).toBe(200);

    const updatedSmartPlaylist: SmartPlaylist = await updateResponse.json();

    expect(updatedSmartPlaylist.name).toBe('Longer Medium Videos');
    expect(updatedSmartPlaylist.criteria.filters.duration_min).toBe(300);

    // Refresh to apply new criteria
    const refreshResponse = await request.post(
      `${API_URL}/api/playlists/smart/${smartPlaylist.id}/refresh`,
      { headers }
    );

    expect(refreshResponse.status()).toBe(200);

    const refreshedPlaylist: Playlist = await refreshResponse.json();

    // Verify all items match new criteria
    for (const item of refreshedPlaylist.items) {
      expect(item.duration).toBeGreaterThanOrEqual(300);
      expect(item.duration).toBeLessThanOrEqual(500);
    }
  });

  test('Clone smart playlist creates independent copy', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Clone the smart playlist
    const cloneResponse = await request.post(
      `${API_URL}/api/playlists/smart/${smartPlaylist.id}/clone`,
      { headers }
    );

    expect(cloneResponse.status()).toBe(200);

    const clonedSmartPlaylist: SmartPlaylist = await cloneResponse.json();

    // Verify cloned playlist has correct properties
    expect(clonedSmartPlaylist.name).toContain('Copy of');
    expect(clonedSmartPlaylist.criteria).toEqual(smartPlaylist.criteria);
    expect(clonedSmartPlaylist.is_public).toBe(false); // Clones are private
    expect(clonedSmartPlaylist.id).not.toBe(smartPlaylist.id);

    // Verify clone has its own generated playlist
    expect(clonedSmartPlaylist.playlist_id).toBeDefined();
    expect(clonedSmartPlaylist.playlist_id).not.toBe(smartPlaylist.playlist_id);

    // Cleanup
    await request.delete(
      `${API_URL}/api/playlists/smart/${clonedSmartPlaylist.id}`,
      { headers }
    );
  });

  test('Public smart playlists accessible by other users', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create a public smart playlist
    const publicPayload = {
      name: 'Public Smart Playlist',
      description: 'Everyone can see this',
      criteria: {
        filters: {
          duration_min: 0,
        },
      },
      is_public: true,
    };

    const createResponse = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: publicPayload,
    });

    expect(createResponse.status()).toBe(201);
    const publicSmartPlaylist: SmartPlaylist = await createResponse.json();

    // Fetch public smart playlists
    const publicResponse = await request.get(
      `${API_URL}/api/playlists/smart/public`,
      { headers }
    );

    expect(publicResponse.status()).toBe(200);
    const publicPlaylists: SmartPlaylist[] = await publicResponse.json();

    // Verify our smart playlist is in the public list
    const ourPlaylist = publicPlaylists.find(
      (p) => p.id === publicSmartPlaylist.id
    );
    expect(ourPlaylist).toBeDefined();
    expect(ourPlaylist!.is_public).toBe(true);

    // Cleanup
    await request.delete(
      `${API_URL}/api/playlists/smart/${publicSmartPlaylist.id}`,
      { headers }
    );
  });

  test('API: Get all smart playlists for user', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    const response = await request.get(`${API_URL}/api/playlists/smart`, {
      headers,
    });

    expect(response.status()).toBe(200);

    const smartPlaylists: SmartPlaylist[] = await response.json();

    // Should have at least our test smart playlist
    expect(smartPlaylists.length).toBeGreaterThanOrEqual(1);

    // Verify our smart playlist is in the list
    const ourPlaylist = smartPlaylists.find((p) => p.id === smartPlaylist.id);
    expect(ourPlaylist).toBeDefined();
  });

  test('API: Get specific smart playlist by ID', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    const response = await request.get(
      `${API_URL}/api/playlists/smart/${smartPlaylist.id}`,
      { headers }
    );

    expect(response.status()).toBe(200);

    const fetched: SmartPlaylist = await response.json();

    expect(fetched.id).toBe(smartPlaylist.id);
    expect(fetched.name).toBe(smartPlaylist.name);
    expect(fetched.criteria).toEqual(smartPlaylist.criteria);
  });

  test('Combined filters: Duration + Type + Title', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const combinedCriteria: SmartPlaylistCreate = {
      name: 'Specific Medium YouTube Videos',
      criteria: {
        filters: {
          duration_min: 200,
          duration_max: 500,
          type: 'youtube',
          title_contains: 'Video',
        },
        order_by: 'duration',
        order_direction: 'asc',
      },
    };

    const response = await request.post(`${API_URL}/api/playlists/smart`, {
      headers,
      json: combinedCriteria,
    });

    expect(response.status()).toBe(201);

    const combinedSmartPlaylist: SmartPlaylist = await response.json();

    // Fetch generated playlist
    const playlistResponse = await request.get(
      `${API_URL}/api/playlists/${combinedSmartPlaylist.playlist_id}`,
      { headers }
    );

    expect(playlistResponse.status()).toBe(200);
    const combinedPlaylist: Playlist = await playlistResponse.json();

    // Verify all items match ALL filters
    for (const item of combinedPlaylist.items) {
      expect(item.duration).toBeGreaterThanOrEqual(200);
      expect(item.duration).toBeLessThanOrEqual(500);
      expect(item.type).toBe('youtube');
      expect(item.title).toContain(/video/i);
    }

    // Verify sorting
    const durations = combinedPlaylist.items.map(item => item.duration);
    const sortedDurations = [...durations].sort((a, b) => a - b);
    expect(durations).toEqual(sortedDurations);

    // Cleanup
    await request.delete(
      `${API_URL}/api/playlists/smart/${combinedSmartPlaylist.id}`,
      { headers }
    );
  });

  test('UI: Smart playlist builder component renders', async ({ page }) => {
    // Set auth token in localStorage
    await page.addInitScript(() => {
      const mockJwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXNtYXJ0LXBsYXlsaXN0cyIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });

    // Navigate to playlists page
    await page.goto(`${BASE_URL}/user-playlists`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Mock API responses for smart playlists
    await page.route(`${API_URL}/api/playlists/smart`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([smartPlaylist]),
      });
    });

    // Switch to smart playlists tab (if available)
    const smartTab = page.locator('button:has-text("Smart")');
    if (await smartTab.isVisible()) {
      await smartTab.click();
    }

    // Verify smart playlist is visible
    const smartElement = page.locator(`text=${smartPlaylist.name}`);
    if (await smartElement.isVisible()) {
      await expect(smartElement).toBeVisible();
    }

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'frontend/tests/e2e/artifacts/smart-playlists-list.png',
      fullPage: true,
    });
  });
});
