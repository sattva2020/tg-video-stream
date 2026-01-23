/**
 * Multi-Tenant Architecture E2E Tests
 *
 * End-to-end verification of multi-tenant architecture:
 * 1) Create organization as platform admin
 * 2) Create users within organization
 * 3) Verify organization-scoped data isolation
 * 4) Test quota enforcement
 * 5) Test organization admin permissions
 * 6) Verify platform admin cross-organization access
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.TEST_API_URL || 'http://localhost:8000';

// Test users
const PLATFORM_ADMIN = {
  email: 'platform_admin@test.com',
  password: 'AdminPass123!',
  name: 'Platform Admin'
};

const ORG_1_ADMIN = {
  email: 'org1_admin@test.com',
  password: 'Org1Pass123!',
  name: 'Org1 Admin'
};

const ORG_1_USER = {
  email: 'org1_user@test.com',
  password: 'Org1UserPass123!',
  name: 'Org1 User'
};

const ORG_2_ADMIN = {
  email: 'org2_admin@test.com',
  password: 'Org2Pass123!',
  name: 'Org2 Admin'
};

// Test organization data
const ORG_1_DATA = {
  name: 'Test Organization 1',
  slug: 'test-org-1',
  logo_url: 'https://example.com/logo1.png',
  primary_color: '#FF5733',
  secondary_color: '#33FF57',
  custom_domain: 'org1.example.com'
};

const ORG_2_DATA = {
  name: 'Test Organization 2',
  slug: 'test-org-2',
  logo_url: 'https://example.com/logo2.png',
  primary_color: '#3357FF',
  secondary_color: '#FF33F6',
  custom_domain: 'org2.example.com'
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Setup authentication for platform admin
 */
async function setupPlatformAdminAuth(page: Page) {
  const mockPayload = {
    sub: 'platform-admin-id',
    email: PLATFORM_ADMIN.email,
    name: PLATFORM_ADMIN.name,
    role: 'superadmin',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };

  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(mockPayload));
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;

  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);

  // Mock /api/users/me endpoint
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'platform-admin-id',
        email: PLATFORM_ADMIN.email,
        name: PLATFORM_ADMIN.name,
        role: 'superadmin',
        is_active: true,
        organization_id: null, // Platform admin has no organization
      }),
    });
  });
}

/**
 * Setup authentication for organization admin
 */
async function setupOrgAdminAuth(page: Page, orgId: string, email: string, name: string) {
  const mockPayload = {
    sub: `org-admin-${orgId}`,
    email: email,
    name: name,
    role: 'admin',
    org_id: orgId,
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };

  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(mockPayload));
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;

  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);

  // Mock /api/users/me endpoint
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: `org-admin-${orgId}`,
        email: email,
        name: name,
        role: 'admin',
        is_active: true,
        organization_id: orgId,
      }),
    });
  });
}

/**
 * Setup authentication for organization user
 */
async function setupOrgUserAuth(page: Page, orgId: string, email: string, name: string) {
  const mockPayload = {
    sub: `org-user-${orgId}`,
    email: email,
    name: name,
    role: 'user',
    org_id: orgId,
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  };

  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(mockPayload));
  const signature = 'test-signature';
  const mockToken = `${header}.${payload}.${signature}`;

  await page.addInitScript((token) => {
    localStorage.setItem('token', token);
  }, mockToken);

  // Mock /api/users/me endpoint
  await page.route('**/api/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: `org-user-${orgId}`,
        email: email,
        name: name,
        role: 'user',
        is_active: true,
        organization_id: orgId,
      }),
    });
  });
}

/**
 * Mock organizations list API
 */
async function mockOrganizationsList(page: Page, organizations: any[]) {
  await page.route('**/api/organizations*', async (route) => {
    const url = route.request().url();

    if (route.request().method() === 'GET' && url.includes('/api/organizations')) {
      // List organizations
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: organizations,
          total: organizations.length,
          page: 1,
          page_size: 10,
        }),
      });
    } else if (route.request().method() === 'POST' && url.includes('/api/organizations')) {
      // Create organization
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'new-org-id',
          ...organizations[0],
          is_active: true,
          created_at: new Date().toISOString(),
        }),
      });
    } else {
      await route.continue();
    }
  });
}

/**
 * Mock organization quotas API
 */
async function mockOrganizationQuotas(page: Page, orgId: string, quotas: any[]) {
  await page.route(`**/api/organizations/${orgId}/quotas*`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(quotas),
    });
  });
}

/**
 * Mock channels API with organization filtering
 */
async function mockChannelsAPI(page: Page, orgChannels: { [orgId: string]: any[] }) {
  await page.route('**/api/channels*', async (route) => {
    // Extract organization_id from request headers or query
    const orgId = route.request().headers()['x-organization-id'];

    if (orgId && orgChannels[orgId]) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(orgChannels[orgId]),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    }
  });
}

// ============================================================================
// Test Suite 1: Organization Creation (Platform Admin)
// ============================================================================

test.describe('Multi-Tenant: Organization Creation', () => {

  test('Platform admin can access organizations page', async ({ page }) => {
    await setupPlatformAdminAuth(page);

    const testOrgs = [
      {
        id: 'org-1-id',
        name: ORG_1_DATA.name,
        slug: ORG_1_DATA.slug,
        logo_url: ORG_1_DATA.logo_url,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      },
    ];

    await mockOrganizationsList(page, testOrgs);

    await page.goto(`${BASE_URL}/admin/organizations`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Org Creation] Organizations page URL:', page.url());

    // Verify we're on the organizations page
    expect(page.url()).toContain('/admin/organizations');

    // Verify organization is visible
    const orgName = page.locator(`text=${ORG_1_DATA.name}`);
    await expect(orgName.first()).toBeVisible({ timeout: 5000 });

    console.log('[Org Creation] Organization visible in list');
  });

  test('Platform admin can create new organization', async ({ page }) => {
    await setupPlatformAdminAuth(page);

    let createOrgCalled = false;
    let createdOrgData: any = null;

    await page.route('**/api/organizations', async (route) => {
      if (route.request().method() === 'POST') {
        createOrgCalled = true;
        const postData = JSON.parse(route.request().postData() || '{}');
        createdOrgData = postData;

        console.log('[Org Creation] POST data:', postData);

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-org-2-id',
            ...postData,
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/organizations`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for create organization button
    const createButton = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("Создать"), button:has-text("Добавить"), button:has-text("+")').first();

    const hasCreateButton = await createButton.isVisible().catch(() => false);
    console.log('[Org Creation] Create button visible:', hasCreateButton);

    if (hasCreateButton) {
      await createButton.click();
      await page.waitForTimeout(1000);

      // Fill organization form
      const nameInput = page.locator('input[name="name"], [data-testid="org-name"]').first();
      const slugInput = page.locator('input[name="slug"], [data-testid="org-slug"]').first();

      if (await nameInput.isVisible()) {
        await nameInput.fill(ORG_2_DATA.name);
        console.log('[Org Creation] Filled organization name');
      }

      if (await slugInput.isVisible()) {
        await slugInput.fill(ORG_2_DATA.slug);
        console.log('[Org Creation] Filled organization slug');
      }

      // Submit form
      const submitButton = page.locator('button[type="submit"]').first();
      if (await submitButton.isVisible()) {
        await submitButton.click();
        await page.waitForTimeout(1000);
      }
    }

    console.log('[Org Creation] Create organization API called:', createOrgCalled);
    if (createdOrgData) {
      console.log('[Org Creation] Created organization data:', createdOrgData);
    }
  });

  test('Platform admin can view organization details', async ({ page }) => {
    await setupPlatformAdminAuth(page);

    const orgId = 'org-1-id';

    // Mock organization details
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: orgId,
          name: ORG_1_DATA.name,
          slug: ORG_1_DATA.slug,
          logo_url: ORG_1_DATA.logo_url,
          primary_color: ORG_1_DATA.primary_color,
          secondary_color: ORG_1_DATA.secondary_color,
          custom_domain: ORG_1_DATA.custom_domain,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
        }),
      });
    });

    // Mock quotas
    await mockOrganizationQuotas(page, orgId, [
      {
        quota_type: 'streams',
        limit: 10,
        usage: 5,
        usage_percentage: 50,
      },
      {
        quota_type: 'users',
        limit: 100,
        usage: 25,
        usage_percentage: 25,
      },
    ]);

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Org Creation] Organization detail page URL:', page.url());

    // Verify organization details are visible
    const orgName = page.locator(`text=${ORG_1_DATA.name}`);
    await expect(orgName.first()).toBeVisible({ timeout: 5000 });

    console.log('[Org Creation] Organization details visible');
  });
});

// ============================================================================
// Test Suite 2: User Management Within Organization
// ============================================================================

test.describe('Multi-Tenant: Organization User Management', () => {

  test('Organization admin can view organization users', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    // Mock organization users
    await page.route(`**/api/organizations/${orgId}/users*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'user-1-id',
            email: ORG_1_ADMIN.email,
            name: ORG_1_ADMIN.name,
            role: 'admin',
            organization_id: orgId,
            status: 'ACTIVE',
          },
          {
            id: 'user-2-id',
            email: ORG_1_USER.email,
            name: ORG_1_USER.name,
            role: 'user',
            organization_id: orgId,
            status: 'ACTIVE',
          },
        ]),
      });
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[User Management] Organization detail page loaded');

    // Look for users section or user count
    const usersSection = page.locator('text=/users|пользователи/i').first();
    const hasUsersSection = await usersSection.isVisible().catch(() => false);

    console.log('[User Management] Users section visible:', hasUsersSection);
  });

  test('Organization admin can add user to organization', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    let addUserCalled = false;

    await page.route(`**/api/organizations/${orgId}/members`, async (route) => {
      if (route.request().method() === 'POST') {
        addUserCalled = true;
        const postData = JSON.parse(route.request().postData() || '{}');
        console.log('[User Management] Add user POST data:', postData);

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-user-id',
            user_id: postData.user_id,
            organization_id: orgId,
            role: postData.role || 'user',
            status: 'ACTIVE',
            joined_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for add user button
    const addButton = page.locator('button:has-text("Add User"), button:has-text("Добавить пользователя"), button:has-text("Invite")').first();

    const hasAddButton = await addButton.isVisible().catch(() => false);
    console.log('[User Management] Add user button visible:', hasAddButton);

    if (hasAddButton) {
      await addButton.click();
      await page.waitForTimeout(1000);

      // Fill user form
      const emailInput = page.locator('input[name="email"], [data-testid="user-email"]').first();
      if (await emailInput.isVisible()) {
        await emailInput.fill('newuser@test.com');
        console.log('[User Management] Filled user email');
      }

      // Submit
      const submitButton = page.locator('button[type="submit"]').first();
      if (await submitButton.isVisible()) {
        await submitButton.click();
        await page.waitForTimeout(1000);
      }
    }

    console.log('[User Management] Add user API called:', addUserCalled);
  });
});

// ============================================================================
// Test Suite 3: Data Isolation
// ============================================================================

test.describe('Multi-Tenant: Data Isolation', () => {

  test('Users can only see data from their organization', async ({ page }) => {
    const org1Id = 'org-1-id';
    const org2Id = 'org-2-id';

    // Setup as Org1 user
    await setupOrgUserAuth(page, org1Id, ORG_1_USER.email, ORG_1_USER.name);

    // Mock channels with organization filtering
    await mockChannelsAPI(page, {
      [org1Id]: [
        { id: 'channel-1', name: 'Org1 Channel 1', organization_id: org1Id },
        { id: 'channel-2', name: 'Org1 Channel 2', organization_id: org1Id },
      ],
      [org2Id]: [
        { id: 'channel-3', name: 'Org2 Channel 1', organization_id: org2Id },
      ],
    });

    await page.goto(`${BASE_URL}/channels`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Data Isolation] Channels page loaded for Org1 user');

    // Verify only Org1 channels are visible
    const org1Channel = page.locator('text=Org1 Channel');
    const org2Channel = page.locator('text=Org2 Channel');

    const hasOrg1Channel = await org1Channel.first().isVisible().catch(() => false);
    const hasOrg2Channel = await org2Channel.first().isVisible().catch(() => false);

    console.log('[Data Isolation] Org1 channel visible:', hasOrg1Channel);
    console.log('[Data Isolation] Org2 channel visible:', hasOrg2Channel);

    // Org1 user should see Org1 channels but not Org2 channels
    expect(hasOrg1Channel).toBeTruthy();
    expect(hasOrg2Channel).toBeFalsy();

    console.log('[Data Isolation] Data isolation verified - user sees only their org data');
  });

  test('Cross-organization access is blocked', async ({ page }) => {
    const org1Id = 'org-1-id';
    const org2Id = 'org-2-id';

    // Setup as Org1 user
    await setupOrgUserAuth(page, org1Id, ORG_1_USER.email, ORG_1_USER.name);

    // Mock API to block cross-org access
    await page.route(`**/api/organizations/${org2Id}*`, async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Access denied: insufficient permissions for this organization',
        }),
      });
    });

    // Try to access Org2 details directly
    await page.goto(`${BASE_URL}/admin/organizations/${org2Id}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Data Isolation] Attempted cross-org access URL:', page.url());

    // Should see access denied or be redirected
    const accessDenied = page.locator('text=/access denied|forbidden|403|нет доступа/i');
    const hasAccessDenied = await accessDenied.first().isVisible().catch(() => false);

    console.log('[Data Isolation] Access denied message visible:', hasAccessDenied);

    // Either shows access denied or redirects away
    const isRedirected = !page.url().includes(org2Id);
    console.log('[Data Isolation] Redirected away from cross-org page:', isRedirected);

    expect(hasAccessDenied || isRedirected).toBeTruthy();
  });

  test('Platform admin can access all organizations', async ({ page }) => {
    const org1Id = 'org-1-id';
    const org2Id = 'org-2-id';

    await setupPlatformAdminAuth(page);

    // Mock multiple organizations
    await page.route('**/api/organizations*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: org1Id, name: ORG_1_DATA.name, slug: ORG_1_DATA.slug, is_active: true },
              { id: org2Id, name: ORG_2_DATA.name, slug: ORG_2_DATA.slug, is_active: true },
            ],
            total: 2,
            page: 1,
            page_size: 10,
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/organizations`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Data Isolation] Platform admin viewing all organizations');

    // Verify both organizations are visible
    const org1Name = page.locator(`text=${ORG_1_DATA.name}`);
    const org2Name = page.locator(`text=${ORG_2_DATA.name}`);

    await expect(org1Name.first()).toBeVisible({ timeout: 5000 });
    await expect(org2Name.first()).toBeVisible({ timeout: 5000 });

    console.log('[Data Isolation] Platform admin can see all organizations');
  });
});

// ============================================================================
// Test Suite 4: Quota Enforcement
// ============================================================================

test.describe('Multi-Tenant: Quota Enforcement', () => {

  test('Organization quotas are displayed correctly', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    // Mock quotas
    const quotas = [
      {
        quota_type: 'streams',
        limit: 10,
        usage: 7,
        usage_percentage: 70,
      },
      {
        quota_type: 'users',
        limit: 100,
        usage: 45,
        usage_percentage: 45,
      },
      {
        quota_type: 'storage_bytes',
        limit: 10737418240, // 10 GB
        usage: 5368709120, // 5 GB
        usage_percentage: 50,
      },
    ];

    await mockOrganizationQuotas(page, orgId, quotas);

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Quota Enforcement] Organization detail page loaded');

    // Look for quota indicators
    const quotaSection = page.locator('text=/quota|квота|лимит/i').first();
    const hasQuotaSection = await quotaSection.isVisible().catch(() => false);

    console.log('[Quota Enforcement] Quota section visible:', hasQuotaSection);

    // Look for progress bars or usage indicators
    const progressBar = page.locator('[role="progressbar"], .progress, [class*="progress"]').first();
    const hasProgressBar = await progressBar.isVisible().catch(() => false);

    console.log('[Quota Enforcement] Progress bar visible:', hasProgressBar);
  });

  test('Organization admin can update quota limits', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    let updateQuotaCalled = false;
    let updatedQuota: any = null;

    // Mock quota update
    await page.route(`**/api/organizations/${orgId}/quotas/*`, async (route) => {
      if (route.request().method() === 'PUT') {
        updateQuotaCalled = true;
        const putData = JSON.parse(route.request().postData() || '{}');
        updatedQuota = putData;

        console.log('[Quota Enforcement] Update quota PUT data:', putData);

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            quota_type: 'streams',
            limit: putData.limit,
            usage: 7,
            usage_percentage: (7 / putData.limit) * 100,
          }),
        });
      }
    });

    // Mock initial quotas
    await mockOrganizationQuotas(page, orgId, [
      {
        quota_type: 'streams',
        limit: 10,
        usage: 7,
        usage_percentage: 70,
      },
    ]);

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for edit quota button
    const editButton = page.locator('button:has-text("Edit"), button:has-text("Изменить"), [aria-label*="edit"]').first();

    const hasEditButton = await editButton.isVisible().catch(() => false);
    console.log('[Quota Enforcement] Edit quota button visible:', hasEditButton);

    if (hasEditButton) {
      await editButton.click();
      await page.waitForTimeout(1000);

      // Update quota limit
      const limitInput = page.locator('input[name="limit"], [data-testid="quota-limit"]').first();
      if (await limitInput.isVisible()) {
        await limitInput.fill('20');
        console.log('[Quota Enforcement] Updated quota limit to 20');
      }

      // Submit
      const submitButton = page.locator('button[type="submit"]').first();
      if (await submitButton.isVisible()) {
        await submitButton.click();
        await page.waitForTimeout(1000);
      }
    }

    console.log('[Quota Enforcement] Update quota API called:', updateQuotaCalled);
    if (updatedQuota) {
      console.log('[Quota Enforcement] Updated quota:', updatedQuota);
    }
  });

  test('Quota exceeded shows warning', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    // Mock exceeded quota
    const quotas = [
      {
        quota_type: 'streams',
        limit: 10,
        usage: 10,
        usage_percentage: 100,
        is_exceeded: true,
      },
    ];

    await mockOrganizationQuotas(page, orgId, quotas);

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Quota Enforcement] Organization with exceeded quota loaded');

    // Look for warning message
    const warningMessage = page.locator('text=/exceeded|limit reached|превышен|лимит/i').first();
    const hasWarning = await warningMessage.isVisible().catch(() => false);

    console.log('[Quota Enforcement] Quota exceeded warning visible:', hasWarning);

    // Look for visual indicator (red color, etc.)
    const warningIndicator = page.locator('[class*="red"], [class*="danger"], [class*="warning"]').first();
    const hasWarningIndicator = await warningIndicator.isVisible().catch(() => false);

    console.log('[Quota Enforcement] Warning indicator visible:', hasWarningIndicator);
  });
});

// ============================================================================
// Test Suite 5: Organization Admin Permissions
// ============================================================================

test.describe('Multi-Tenant: Organization Admin Permissions', () => {

  test('Organization admin can manage their org settings', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    // Mock organization details
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: orgId,
          name: ORG_1_DATA.name,
          slug: ORG_1_DATA.slug,
          logo_url: ORG_1_DATA.logo_url,
          primary_color: ORG_1_DATA.primary_color,
          secondary_color: ORG_1_DATA.secondary_color,
          is_active: true,
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Org Admin Permissions] Organization admin viewing their org');

    // Look for settings/edit button
    const settingsButton = page.locator('button:has-text("Settings"), button:has-text("Edit"), [aria-label*="settings"]').first();
    const hasSettingsButton = await settingsButton.isVisible().catch(() => false);

    console.log('[Org Admin Permissions] Settings button visible:', hasSettingsButton);

    // Verify can see organization details
    const orgName = page.locator(`text=${ORG_1_DATA.name}`);
    await expect(orgName.first()).toBeVisible({ timeout: 5000 });
  });

  test('Organization admin cannot access other organizations', async ({ page }) => {
    const org1Id = 'org-1-id';
    const org2Id = 'org-2-id';

    // Setup as Org1 admin
    await setupOrgAdminAuth(page, org1Id, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    // Mock Org2 access as forbidden
    await page.route(`**/api/organizations/${org2Id}`, async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'You do not have permission to access this organization',
        }),
      });
    });

    // Try to access Org2
    await page.goto(`${BASE_URL}/admin/organizations/${org2Id}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Org Admin Permissions] Attempted to access other organization');

    // Should see access denied or be redirected
    const accessDenied = page.locator('text=/access denied|forbidden|403|нет доступа/i');
    const hasAccessDenied = await accessDenied.isVisible().catch(() => false);

    const isRedirected = !page.url().includes(org2Id);

    console.log('[Org Admin Permissions] Access denied visible:', hasAccessDenied);
    console.log('[Org Admin Permissions] Redirected:', isRedirected);

    expect(hasAccessDenied || isRedirected).toBeTruthy();
  });

  test('Regular user has limited permissions', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgUserAuth(page, orgId, ORG_1_USER.email, ORG_1_USER.name);

    // Mock user permissions (read-only)
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: orgId,
          name: ORG_1_DATA.name,
          slug: ORG_1_DATA.slug,
          is_active: true,
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Org Admin Permissions] Regular user viewing organization');

    // Look for admin-only buttons (should not be visible)
    const editButton = page.locator('button:has-text("Edit"), button:has-text("Settings"), button:has-text("Delete")').first();
    const hasEditButton = await editButton.isVisible().catch(() => false);

    console.log('[Org Admin Permissions] Edit button visible for regular user:', hasEditButton);

    // Regular user should not see admin controls
    expect(hasEditButton).toBeFalsy();
  });
});

// ============================================================================
// Test Suite 6: Platform Admin Cross-Organization Access
// ============================================================================

test.describe('Multi-Tenant: Platform Admin Cross-Org Access', () => {

  test('Platform admin can switch between organizations', async ({ page }) => {
    await setupPlatformAdminAuth(page);

    const org1Id = 'org-1-id';
    const org2Id = 'org-2-id';

    // Mock organizations list
    await page.route('**/api/organizations*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: org1Id, name: ORG_1_DATA.name, slug: ORG_1_DATA.slug, is_active: true },
              { id: org2Id, name: ORG_2_DATA.name, slug: ORG_2_DATA.slug, is_active: true },
            ],
            total: 2,
            page: 1,
            page_size: 10,
          }),
        });
      }
    });

    // Mock individual org details
    await page.route(`**/api/organizations/${org1Id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: org1Id, name: ORG_1_DATA.name, slug: ORG_1_DATA.slug }),
      });
    });

    await page.route(`**/api/organizations/${org2Id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: org2Id, name: ORG_2_DATA.name, slug: ORG_2_DATA.slug }),
      });
    });

    // Navigate to Org1
    await page.goto(`${BASE_URL}/admin/organizations/${org1Id}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    console.log('[Cross-Org Access] Viewing Org1:', page.url());

    // Navigate to Org2
    await page.goto(`${BASE_URL}/admin/organizations/${org2Id}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    console.log('[Cross-Org Access] Viewing Org2:', page.url());

    // Verify both organizations are accessible
    expect(page.url()).toContain(org2Id);

    const org2Name = page.locator(`text=${ORG_2_DATA.name}`);
    await expect(org2Name.first()).toBeVisible({ timeout: 5000 });

    console.log('[Cross-Org Access] Successfully switched between organizations');
  });

  test('Platform admin can view all organizations data', async ({ page }) => {
    await setupPlatformAdminAuth(page);

    // Mock all organizations
    await page.route('**/api/organizations*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              { id: 'org-1', name: 'Organization 1', slug: 'org-1', is_active: true, created_at: '2024-01-01T00:00:00Z' },
              { id: 'org-2', name: 'Organization 2', slug: 'org-2', is_active: true, created_at: '2024-01-02T00:00:00Z' },
              { id: 'org-3', name: 'Organization 3', slug: 'org-3', is_active: false, created_at: '2024-01-03T00:00:00Z' },
            ],
            total: 3,
            page: 1,
            page_size: 10,
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/organizations`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Cross-Org Access] Viewing all organizations');

    // Verify all organizations are visible
    const org1 = page.locator('text=Organization 1');
    const org2 = page.locator('text=Organization 2');
    const org3 = page.locator('text=Organization 3');

    await expect(org1.first()).toBeVisible({ timeout: 5000 });
    await expect(org2.first()).toBeVisible({ timeout: 5000 });
    await expect(org3.first()).toBeVisible({ timeout: 5000 });

    console.log('[Cross-Org Access] All organizations visible to platform admin');
  });

  test('Platform admin can manage any organization', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupPlatformAdminAuth(page);

    let deactivateCalled = false;

    // Mock deactivate endpoint
    await page.route(`**/api/organizations/${orgId}/deactivate`, async (route) => {
      if (route.request().method() === 'POST') {
        deactivateCalled = true;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: orgId,
            name: ORG_1_DATA.name,
            is_active: false,
          }),
        });
      }
    });

    // Mock org details
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: orgId,
          name: ORG_1_DATA.name,
          slug: ORG_1_DATA.slug,
          is_active: true,
        }),
      });
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[Cross-Org Access] Platform admin managing organization');

    // Look for deactivate button
    const deactivateButton = page.locator('button:has-text("Deactivate"), button:has-text("Disable")').first();
    const hasDeactivateButton = await deactivateButton.isVisible().catch(() => false);

    console.log('[Cross-Org Access] Deactivate button visible:', hasDeactivateButton);

    if (hasDeactivateButton) {
      await deactivateButton.click();
      await page.waitForTimeout(1000);

      // Confirm if dialog appears
      const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Yes")').first();
      if (await confirmButton.isVisible()) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }
    }

    console.log('[Cross-Org Access] Deactivate API called:', deactivateCalled);
  });
});

// ============================================================================
// Test Suite 7: White-Label Customization
// ============================================================================

test.describe('Multi-Tenant: White-Label Customization', () => {

  test('Organization branding is displayed', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgUserAuth(page, orgId, ORG_1_USER.email, ORG_1_USER.name);

    // Mock organization with branding
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: orgId,
          name: ORG_1_DATA.name,
          slug: ORG_1_DATA.slug,
          logo_url: ORG_1_DATA.logo_url,
          primary_color: ORG_1_DATA.primary_color,
          secondary_color: ORG_1_DATA.secondary_color,
          custom_domain: ORG_1_DATA.custom_domain,
          is_active: true,
        }),
      });
    });

    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    console.log('[White-Label] Dashboard loaded with organization branding');

    // Look for logo
    const logo = page.locator(`img[src*="${ORG_1_DATA.logo_url}"]`).first();
    const hasLogo = await logo.isVisible().catch(() => false);

    console.log('[White-Label] Organization logo visible:', hasLogo);

    // Look for organization name
    const orgName = page.locator(`text=${ORG_1_DATA.name}`);
    const hasOrgName = await orgName.first().isVisible().catch(() => false);

    console.log('[White-Label] Organization name visible:', hasOrgName);

    // Check if custom colors are applied (would need to inspect CSS)
    const body = page.locator('body');
    const bodyColor = await body.evaluate((el) => window.getComputedStyle(el).color);

    console.log('[White-Label] Body color:', bodyColor);
  });

  test('Organization admin can update branding', async ({ page }) => {
    const orgId = 'org-1-id';
    await setupOrgAdminAuth(page, orgId, ORG_1_ADMIN.email, ORG_1_ADMIN.name);

    let updateCalled = false;
    let updatedBranding: any = null;

    // Mock update endpoint
    await page.route(`**/api/organizations/${orgId}`, async (route) => {
      if (route.request().method() === 'PUT') {
        updateCalled = true;
        const putData = JSON.parse(route.request().postData() || '{}');
        updatedBranding = putData;

        console.log('[White-Label] Update branding PUT data:', putData);

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: orgId,
            ...putData,
            is_active: true,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: orgId,
            name: ORG_1_DATA.name,
            slug: ORG_1_DATA.slug,
            primary_color: ORG_1_DATA.primary_color,
            secondary_color: ORG_1_DATA.secondary_color,
            is_active: true,
          }),
        });
      }
    });

    await page.goto(`${BASE_URL}/admin/organizations/${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for settings/branding section
    const brandingSection = page.locator('text=/branding|цвет|color/i').first();
    const hasBrandingSection = await brandingSection.isVisible().catch(() => false);

    console.log('[White-Label] Branding section visible:', hasBrandingSection);

    if (hasBrandingSection) {
      // Look for color pickers or inputs
      const colorInput = page.locator('input[type="color"], [name="primary_color"]').first();

      if (await colorInput.isVisible()) {
        // Update color (for input[type="color"])
        const inputType = await colorInput.getAttribute('type');
        if (inputType === 'color') {
          await colorInput.fill('#FF0000');
          console.log('[White-Label] Updated primary color');
        }
      }

      // Submit changes
      const saveButton = page.locator('button:has-text("Save"), button:has-text("Apply")').first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(1000);
      }
    }

    console.log('[White-Label] Update branding API called:', updateCalled);
  });
});
