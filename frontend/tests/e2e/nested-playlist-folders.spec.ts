/**
 * E2E Test: Nested Playlist Folder Structures
 *
 * Verifies:
 * - Creating parent playlist groups
 * - Creating child groups inside parent groups
 * - Creating playlists in nested groups
 * - Folder tree displays correct nesting hierarchy
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.TEST_API_URL || 'http://localhost:8000';

// Interfaces matching the API
interface PlaylistGroup {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  parent_id?: string | null;
  position: number;
  color?: string;
  icon?: string;
  is_expanded: boolean;
  playlists_count: number;
  created_at: string;
  updated_at?: string;
}

interface PlaylistGroupCreate {
  name: string;
  description?: string;
  parent_id?: string | null;
  position?: number;
  color?: string;
  icon?: string;
}

interface Playlist {
  id: string;
  user_id: string;
  name: string;
  group_id?: string;
  items_count: number;
  total_duration: number;
  created_at: string;
}

// Test data
const TEST_GROUPS = {
  parent: {
    name: 'Parent Music Folder',
    description: 'Top level folder for music',
    position: 0,
    color: '#FF5733',
  },
  child: {
    name: 'Rock Classics',
    description: 'Classic rock music subfolder',
    position: 0,
    color: '#33FF57',
  },
};

const TEST_PLAYLIST = {
  name: 'Best Rock Songs',
  description: 'Collection of classic rock hits',
  items: [
    {
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      title: 'Never Gonna Give You Up',
      duration: 212,
      type: 'youtube',
    },
  ],
};

test.describe('E2E: Nested Playlist Folders', () => {
  let authToken: string;
  let parentGroup: PlaylistGroup;
  let childGroup: PlaylistGroup;
  let testPlaylist: Playlist;

  // Setup: Authenticate user
  test.beforeAll(async ({ request }) => {
    // Create or login test user
    const loginResponse = await request.post(`${API_URL}/api/auth/test-login`, {
      json: {
        email: 'test-folders@example.com',
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
          email: 'test-folders@example.com',
          password: 'TestPassword123!',
          full_name: 'Folder Test User',
        },
      });

      if (registerResponse.status() !== 201) {
        throw new Error('Failed to register test user');
      }
    }
  });

  // Cleanup: Delete test data
  test.afterAll(async ({ request }) => {
    if (!authToken) return;

    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Delete playlist if created
    if (testPlaylist) {
      await request.delete(`${API_URL}/api/playlists/${testPlaylist.id}`, {
        headers,
      });
    }

    // Delete child group if created
    if (childGroup) {
      await request.delete(`${API_URL}/api/playlists/groups/${childGroup.id}`, {
        headers,
      });
    }

    // Delete parent group if created
    if (parentGroup) {
      await request.delete(`${API_URL}/api/playlists/groups/${parentGroup.id}`, {
        headers,
      });
    }
  });

  test('Step 1: Create parent playlist group', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const response = await request.post(`${API_URL}/api/playlists/groups`, {
      headers,
      json: TEST_GROUPS.parent,
    });

    expect(response.status()).toBe(201);

    const data = await response.json();
    parentGroup = data;

    // Verify parent group properties
    expect(parentGroup).toMatchObject({
      name: TEST_GROUPS.parent.name,
      description: TEST_GROUPS.parent.description,
      parent_id: null, // Root level has no parent
      position: TEST_GROUPS.parent.position,
      color: TEST_GROUPS.parent.color,
    });

    expect(parentGroup.id).toBeDefined();
    expect(parentGroup.user_id).toBeDefined();
    expect(parentGroup.created_at).toBeDefined();
  });

  test('Step 2: Create child group inside parent', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const childGroupData: PlaylistGroupCreate = {
      ...TEST_GROUPS.child,
      parent_id: parentGroup.id, // Set parent to the group created in Step 1
    };

    const response = await request.post(`${API_URL}/api/playlists/groups`, {
      headers,
      json: childGroupData,
    });

    expect(response.status()).toBe(201);

    const data = await response.json();
    childGroup = data;

    // Verify child group properties
    expect(childGroup).toMatchObject({
      name: TEST_GROUPS.child.name,
      description: TEST_GROUPS.child.description,
      parent_id: parentGroup.id, // Should have parent_id set
      position: TEST_GROUPS.child.position,
      color: TEST_GROUPS.child.color,
    });

    expect(childGroup.id).toBeDefined();
    expect(childGroup.user_id).toBeDefined();
    expect(childGroup.created_at).toBeDefined();
  });

  test('Step 3: Create playlist in child group', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    const playlistData = {
      ...TEST_PLAYLIST,
      group_id: childGroup.id, // Place playlist in child group
    };

    const response = await request.post(`${API_URL}/api/playlists/`, {
      headers,
      json: playlistData,
    });

    expect(response.status()).toBe(201);

    const data = await response.json();
    testPlaylist = data;

    // Verify playlist properties
    expect(testPlaylist).toMatchObject({
      name: TEST_PLAYLIST.name,
      group_id: childGroup.id, // Playlist should be in child group
    });

    expect(testPlaylist.id).toBeDefined();
    expect(testPlaylist.user_id).toBeDefined();
    expect(testPlaylist.created_at).toBeDefined();
  });

  test('Step 4: Verify folder tree shows correct nesting', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
    };

    // Fetch all groups
    const response = await request.get(`${API_URL}/api/playlists/groups`, {
      headers,
    });

    expect(response.status()).toBe(200);

    const groups: PlaylistGroup[] = await response.json();

    // Verify we have our groups
    expect(groups.length).toBeGreaterThanOrEqual(2);

    // Find our groups
    const fetchedParent = groups.find((g) => g.id === parentGroup.id);
    const fetchedChild = groups.find((g) => g.id === childGroup.id);

    expect(fetchedParent).toBeDefined();
    expect(fetchedChild).toBeDefined();

    // Verify nesting structure
    expect(fetchedParent!.parent_id).toBeNull(); // Parent has no parent
    expect(fetchedChild!.parent_id).toBe(parentGroup.id); // Child's parent is the parent group

    // Fetch playlists and verify it's in the child group
    const playlistResponse = await request.get(`${API_URL}/api/playlists/`, {
      headers,
    });

    expect(playlistResponse.status()).toBe(200);

    const playlists: Playlist[] = await playlistResponse.json();
    const fetchedPlaylist = playlists.find((p) => p.id === testPlaylist.id);

    expect(fetchedPlaylist).toBeDefined();
    expect(fetchedPlaylist!.group_id).toBe(childGroup.id); // Playlist is in child group
  });

  test('UI: Folder tree displays nested structure correctly', async ({ page }) => {
    // Set auth token in localStorage
    await page.addInitScript(() => {
      const mockJwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWZvbGRlcnMiLCJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJ1c2VyIn0.dummy_signature';
      localStorage.setItem('token', mockJwt);
    });

    // Navigate to playlists page
    await page.goto(`${BASE_URL}/user-playlists`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Mock API responses for groups
    await page.route(`${API_URL}/api/playlists/groups`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([parentGroup, childGroup]),
      });
    });

    // Mock API responses for playlists
    await page.route(`${API_URL}/api/playlists/**`, async (route) => {
      if (route.request().url().includes('/groups')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([parentGroup, childGroup]),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([testPlaylist]),
        });
      }
    });

    // Verify parent group is visible
    const parentGroupElement = page.locator(`text=${TEST_GROUPS.parent.name}`);
    await expect(parentGroupElement).toBeVisible();

    // Parent group should be at root level (not deeply nested in another folder)
    const parentNesting = page.locator(
      `text=${TEST_GROUPS.parent.name}`
    ).locator('xpath=ancestor::*[contains(@class, "folder-node")]');
    await expect(parentNesting).toHaveCount(1); // Only one level deep

    // Expand parent group to see child
    const parentExpandButton = page.locator(
      `text=${TEST_GROUPS.parent.name}`
    ).locator('xpath=ancestor::*[contains(@class, "folder-node")]//button[contains(@class, "expand")]').first();

    if (await parentExpandButton.isVisible()) {
      await parentExpandButton.click();
    }

    // Verify child group is visible and nested under parent
    const childGroupElement = page.locator(`text=${TEST_GROUPS.child.name}`);
    await expect(childGroupElement).toBeVisible();

    // Verify nesting by checking DOM hierarchy
    // Child should appear after parent in the tree
    const childNesting = page.locator(
      `text=${TEST_GROUPS.child.name}`
    ).locator('xpath=ancestor::*[contains(@class, "folder-node")]');
    await expect(childNesting).toHaveCount_greaterThan(1); // More than one level deep (nested)

    // Expand child group to see playlist
    const childExpandButton = page.locator(
      `text=${TEST_GROUPS.child.name}`
    ).locator('xpath=ancestor::*[contains(@class, "folder-node")]//button[contains(@class, "expand")]').first();

    if (await childExpandButton.isVisible()) {
      await childExpandButton.click();
    }

    // Verify playlist is visible in child group
    const playlistElement = page.locator(`text=${TEST_PLAYLIST.name}`);
    await expect(playlistElement).toBeVisible();

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'frontend/tests/e2e/artifacts/nested-folders-structure.png',
      fullPage: true,
    });
  });

  test('API: Verify circular reference prevention', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    };

    // Try to create a circular reference: set parent's parent to child
    const response = await request.post(
      `${API_URL}/api/playlists/groups/${parentGroup.id}/move`,
      {
        headers,
        params: {
          parent_id: childGroup.id, // This should fail - circular reference
        },
      }
    );

    // Should fail with 400 or 422 error
    expect([400, 422]).toContain(response.status());

    if (response.status() === 400) {
      const error = await response.json();
      expect(error.detail).toMatch(/circular|reference|invalid/i);
    }
  });
});
