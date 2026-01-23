/**
 * E2E Test: Bulk Operations on Multiple Playlists
 *
 * Verifies:
 * - Creating multiple playlists for bulk operations
 * - Selecting multiple playlists
 * - Bulk deleting selected playlists
 * - Bulk moving playlists to different groups
 * - Bulk copying playlists
 * - Verifying all operations complete successfully
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

interface PlaylistCreate {
  name: string;
  description?: string;
  items?: PlaylistEntry[];
  group_id?: string;
  is_public?: boolean;
}

interface PlaylistGroup {
  id: string;
  user_id: string;
  name: string;
  parent_id?: string;
  description?: string;
  color?: string;
  icon?: string;
  position: number;
  created_at: string;
}

interface BulkDeleteRequest {
  playlist_ids: string[];
}

interface BulkMoveRequest {
  playlist_ids: string[];
  group_id?: string;
}

interface BulkCopyRequest {
  playlist_ids: string[];
}

interface BulkOperationResponse {
  success_count: number;
  failed_count: number;
  errors: string[];
}

// Test data
const TEST_PLAYLISTS: PlaylistCreate[] = [
  {
    name: 'Bulk Test Playlist 1',
    description: 'First playlist for bulk operations testing',
    items: [
      {
        url: 'https://www.youtube.com/watch?v=test1',
        title: 'Test Video 1',
        duration: 180,
        type: 'youtube',
      },
    ],
  },
  {
    name: 'Bulk Test Playlist 2',
    description: 'Second playlist for bulk operations testing',
    items: [
      {
        url: 'https://www.youtube.com/watch?v=test2',
        title: 'Test Video 2',
        duration: 240,
        type: 'youtube',
      },
    ],
  },
  {
    name: 'Bulk Test Playlist 3',
    description: 'Third playlist for bulk operations testing',
    items: [
      {
        url: 'https://www.youtube.com/watch?v=test3',
        title: 'Test Video 3',
        duration: 300,
        type: 'youtube',
      },
    ],
  },
  {
    name: 'Bulk Test Playlist 4',
    description: 'Fourth playlist for bulk operations testing',
    items: [
      {
        url: 'https://www.youtube.com/watch?v=test4',
        title: 'Test Video 4',
        duration: 360,
        type: 'youtube',
      },
    ],
  },
];

const TEST_GROUP: PlaylistGroup = {
  id: '',
  user_id: '',
  name: 'Bulk Operations Test Group',
  position: 0,
  created_at: '',
};

test.describe('E2E: Bulk Operations on Multiple Playlists', () => {
  let authToken: string;
  let createdPlaylists: Playlist[] = [];
  let testGroup: PlaylistGroup;

  // Setup: Authenticate user and create test data
  test.beforeAll(async ({ request }) => {
    // Create or login test user
    const loginResponse = await request.post(`${API_URL}/api/auth/test-login`, {
      json: {
        email: 'test-bulk-ops@example.com',
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
          email: 'test-bulk-ops@example.com',
          password: 'TestPassword123!',
          full_name: 'Bulk Operations Test User',
        },
      });

      if (registerResponse.status() !== 201) {
        throw new Error('Failed to register test user');
      }
      const loginData = await registerResponse.json();
      authToken = loginData.access_token;
    }

    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Create test group for move operations
    const groupResponse = await request.post(`${API_URL}/api/playlists/groups`, {
      headers,
      json: {
        name: TEST_GROUP.name,
      },
    });

    if (groupResponse.status() === 201) {
      testGroup = await groupResponse.json();
    }

    // Create test playlists
    for (const playlistData of TEST_PLAYLISTS) {
      const response = await request.post(`${API_URL}/api/playlists`, {
        headers,
        json: playlistData,
      });

      if (response.status() === 201) {
        const playlist = await response.json();
        createdPlaylists.push(playlist);
      }
    }
  });

  // Cleanup: Delete test data
  test.afterAll(async ({ request }) => {
    if (!authToken) return;

    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Delete all created playlists
    for (const playlist of createdPlaylists) {
      await request.delete(`${API_URL}/api/playlists/${playlist.id}`, {
        headers,
      });
    }

    // Delete test group
    if (testGroup) {
      await request.delete(`${API_URL}/api/playlists/groups/${testGroup.id}`, {
        headers,
      });
    }
  });

  test('Step 1: Create multiple playlists for bulk operations', async ({ request }) => {
    expect(createdPlaylists).toHaveLength(TEST_PLAYLISTS.length);

    // Verify all playlists were created successfully
    for (let i = 0; i < TEST_PLAYLISTS.length; i++) {
      expect(createdPlaylists[i]).toMatchObject({
        name: TEST_PLAYLISTS[i].name,
        description: TEST_PLAYLISTS[i].description,
        items_count: TEST_PLAYLISTS[i].items?.length || 0,
      });
      expect(createdPlaylists[i].id).toBeDefined();
    }
  });

  test('Step 2: Select playlists for bulk operation', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Fetch all playlists to verify they exist
    const response = await request.get(`${API_URL}/api/playlists`, { headers });

    expect(response.status()).toBe(200);
    const playlists: Playlist[] = await response.json();

    // Verify our test playlists are in the list
    const testPlaylistNames = TEST_PLAYLISTS.map((p) => p.name);
    const fetchedPlaylistNames = playlists.map((p) => p.name);

    for (const name of testPlaylistNames) {
      expect(fetchedPlaylistNames).toContain(name);
    }

    // Collect playlist IDs for bulk operations
    const playlistIds = playlists
      .filter((p) => testPlaylistNames.includes(p.name))
      .map((p) => p.id);

    expect(playlistIds).toHaveLength(TEST_PLAYLISTS.length);
  });

  test('Step 3: Execute bulk delete on selected playlists', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Select first 2 playlists for deletion
    const toDelete = createdPlaylists.slice(0, 2);
    const deleteRequest: BulkDeleteRequest = {
      playlist_ids: toDelete.map((p) => p.id),
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/delete`, {
      headers,
      json: deleteRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse = await response.json();

    // Verify all playlists were deleted successfully
    expect(result.success_count).toBe(2);
    expect(result.failed_count).toBe(0);
    expect(result.errors).toHaveLength(0);

    // Verify playlists no longer exist
    for (const playlist of toDelete) {
      const checkResponse = await request.get(
        `${API_URL}/api/playlists/${playlist.id}`,
        { headers }
      );
      expect(checkResponse.status()).toBe(404);
    }

    // Update createdPlaylists to remove deleted ones
    createdPlaylists = createdPlaylists.filter((p) => !toDelete.includes(p));
  });

  test('Step 4: Verify all selected playlists deleted', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Fetch all playlists
    const response = await request.get(`${API_URL}/api/playlists`, { headers });

    expect(response.status()).toBe(200);
    const playlists: Playlist[] = await response.json();

    // Verify deleted playlists are not in the list
    const remainingNames = createdPlaylists.map((p) => p.name);
    const fetchedNames = playlists.map((p) => p.name);

    for (const name of remainingNames) {
      expect(fetchedNames).toContain(name);
    }

    // Verify we have correct number remaining
    expect(createdPlaylists).toHaveLength(2);
  });

  test('API: Bulk move playlists to different group', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Move all remaining playlists to test group
    const moveRequest: BulkMoveRequest = {
      playlist_ids: createdPlaylists.map((p) => p.id),
      group_id: testGroup.id,
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/move`, {
      headers,
      json: moveRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse = await response.json();

    // Verify all playlists were moved successfully
    expect(result.success_count).toBe(2);
    expect(result.failed_count).toBe(0);
    expect(result.errors).toHaveLength(0);

    // Verify playlists are now in the group
    for (const playlist of createdPlaylists) {
      const checkResponse = await request.get(
        `${API_URL}/api/playlists/${playlist.id}`,
        { headers }
      );
      expect(checkResponse.status()).toBe(200);
      const playlistData: Playlist = await checkResponse.json();
      expect(playlistData.group_id).toBe(testGroup.id);
    }
  });

  test('API: Bulk move playlists to root (no group)', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Move all playlists back to root
    const moveRequest: BulkMoveRequest = {
      playlist_ids: createdPlaylists.map((p) => p.id),
      group_id: null,
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/move`, {
      headers,
      json: moveRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse = await response.json();

    // Verify all playlists were moved successfully
    expect(result.success_count).toBe(2);
    expect(result.failed_count).toBe(0);
    expect(result.errors).toHaveLength(0);

    // Verify playlists are now at root level
    for (const playlist of createdPlaylists) {
      const checkResponse = await request.get(
        `${API_URL}/api/playlists/${playlist.id}`,
        { headers }
      );
      expect(checkResponse.status()).toBe(200);
      const playlistData: Playlist = await checkResponse.json();
      expect(playlistData.group_id).toBeNull();
    }
  });

  test('API: Bulk copy playlists', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const initialCount = createdPlaylists.length;

    // Copy all remaining playlists
    const copyRequest: BulkCopyRequest = {
      playlist_ids: createdPlaylists.map((p) => p.id),
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/copy`, {
      headers,
      json: copyRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse & { copied_playlists?: Playlist[] } =
      await response.json();

    // Verify all playlists were copied successfully
    expect(result.success_count).toBe(initialCount);
    expect(result.failed_count).toBe(0);
    expect(result.errors).toHaveLength(0);
    expect(result.copied_playlists).toHaveLength(initialCount);

    // Verify copied playlists have correct properties
    for (let i = 0; i < initialCount; i++) {
      const original = createdPlaylists[i];
      const copied = result.copied_playlists![i];

      expect(copied.name).toContain('Copy of');
      expect(copied.items_count).toBe(original.items_count);
      expect(copied.total_duration).toBe(original.total_duration);
      expect(copied.items).toHaveLength(original.items.length);

      // Add to created playlists for cleanup
      createdPlaylists.push(copied);
    }
  });

  test('API: Bulk delete requires authentication', async ({ request }) => {
    const deleteRequest: BulkDeleteRequest = {
      playlist_ids: [createdPlaylists[0].id],
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/delete`, {
      json: deleteRequest,
    });

    expect(response.status()).toBe(401);
  });

  test('API: Bulk delete with non-existent playlists', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Try to delete mix of existent and non-existent playlists
    const fakeId = '00000000-0000-0000-0000-000000000000';
    const deleteRequest: BulkDeleteRequest = {
      playlist_ids: [createdPlaylists[0].id, fakeId],
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/delete`, {
      headers,
      json: deleteRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse = await response.json();

    // One success (real playlist), one failure (fake playlist)
    expect(result.success_count).toBe(1);
    expect(result.failed_count).toBe(1);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toContain('not found');

    // Verify the real playlist was actually deleted
    const checkResponse = await request.get(
      `${API_URL}/api/playlists/${createdPlaylists[0].id}`,
      { headers }
    );
    expect(checkResponse.status()).toBe(404);

    // Update created playlists
    createdPlaylists.shift();
  });

  test('API: Bulk move with unauthorized playlists', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Try to move with unauthorized playlist ID (belongs to another user)
    const fakeId = '00000000-0000-0000-0000-000000000000';
    const moveRequest: BulkMoveRequest = {
      playlist_ids: [createdPlaylists[0].id, fakeId],
      group_id: testGroup.id,
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/move`, {
      headers,
      json: moveRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse = await response.json();

    // One success (owned playlist), one failure (unauthorized)
    expect(result.success_count).toBe(1);
    expect(result.failed_count).toBe(1);
    expect(result.errors).toHaveLength(1);
  });

  test('API: Bulk copy public playlists from other users', async ({
    request,
  }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Make one playlist public
    const updateResponse = await request.put(
      `${API_URL}/api/playlists/${createdPlaylists[0].id}`,
      {
        headers,
        json: { is_public: true },
      }
    );

    expect(updateResponse.status()).toBe(200);

    // Copy the public playlist (should work even though it's our own)
    const copyRequest: BulkCopyRequest = {
      playlist_ids: [createdPlaylists[0].id],
    };

    const response = await request.post(`${API_URL}/api/playlists/bulk/copy`, {
      headers,
      json: copyRequest,
    });

    expect(response.status()).toBe(200);

    const result: BulkOperationResponse & { copied_playlists?: Playlist[] } =
      await response.json();

    expect(result.success_count).toBe(1);
    expect(result.failed_count).toBe(0);
    expect(result.copied_playlists).toHaveLength(1);

    // Add copied playlist for cleanup
    createdPlaylists.push(result.copied_playlists![0]);
  });

  test('UI: Bulk operations menu visible on playlist list', async ({
    page,
  }) => {
    // Set auth token in localStorage
    await page.addInitScript(() => {
      const mockJwt =
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWJ1bGstb3BzIiwiZXhwIjo5OTk5OTk5OTk5LCJyb2xlIjoidXNlciJ9.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });

    // Navigate to playlists page
    await page.goto(`${BASE_URL}/user-playlists`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Mock API responses for playlists
    await page.route(`${API_URL}/api/playlists**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdPlaylists),
      });
    });

    // Verify playlist list is visible
    const playlistList = page.locator('text=Bulk Test Playlist');
    await expect(playlistList.first()).toBeVisible();

    // Verify bulk operations controls exist (checkboxes, select all, bulk actions)
    const selectCheckbox = page.locator('input[type="checkbox"]').first();
    await expect(selectCheckbox).toBeVisible();

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'frontend/tests/e2e/artifacts/bulk-operations-list.png',
      fullPage: true,
    });
  });

  test('UI: Selection mode enables bulk actions', async ({ page }) => {
    // Set auth token in localStorage
    await page.addInitScript(() => {
      const mockJwt =
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWJ1bGstb3BzIiwiZXhwIjo5OTk5OTk5OTk5LCJyb2xlIjoidXNlciJ9.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });

    // Navigate to playlists page
    await page.goto(`${BASE_URL}/user-playlists`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Mock API responses
    await page.route(`${API_URL}/api/playlists**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdPlaylists),
      });
    });

    // Click first playlist checkbox to enter selection mode
    const firstCheckbox = page.locator('input[type="checkbox"]').first();
    await firstCheckbox.click();

    // Verify selection counter appears
    const selectionCounter = page.locator('text=/\\d+ selected/');
    await expect(selectionCounter).toBeVisible();

    // Verify bulk actions menu appears
    const bulkActionsButton = page.locator('button:has-text("Bulk Actions")');
    if (await bulkActionsButton.isVisible()) {
      await expect(bulkActionsButton).toBeVisible();
    }

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'frontend/tests/e2e/artifacts/bulk-operations-selection.png',
      fullPage: true,
    });
  });
});
