# Subtask 5-1: End-to-End Test - Nested Folder Structure with Playlists

## Overview
This document describes the end-to-end tests for creating nested folder structures with playlists, verifying that the playlist folder tree correctly displays hierarchical relationships.

## Test Files Created

### 1. Frontend E2E Test
**File:** `frontend/tests/e2e/nested-playlist-folders.spec.ts`

**Framework:** Playwright (TypeScript)

**What it tests:**
- Creating a parent playlist group at root level
- Creating a child group inside the parent group
- Creating a playlist in the nested child group
- Verifying the folder tree displays correct nesting hierarchy
- Preventing circular references in group hierarchy

**Test Cases:**
1. **Step 1: Create parent playlist group** - Verifies parent group creation with no parent_id
2. **Step 2: Create child group inside parent** - Verifies child has parent_id set to parent
3. **Step 3: Create playlist in child group** - Verifies playlist belongs to child group
4. **Step 4: Verify folder tree shows correct nesting** - Fetches groups and playlists to verify hierarchy
5. **UI: Folder tree displays nested structure correctly** - Browser test verifying visual nesting
6. **API: Verify circular reference prevention** - Ensures invalid moves are rejected

### 2. Backend Integration Test
**File:** `backend/tests/integration/test_nested_playlist_groups.py`

**Framework:** Pytest (Python)

**What it tests:**
- Creating parent groups at root level
- Creating child groups with parent_id
- Deeply nested group hierarchies (3+ levels)
- Fetching groups with nested structure
- Creating playlists in nested groups
- Moving groups between parents
- Circular reference prevention
- Delete parent and move children to root

**Test Cases:**
1. `test_create_parent_group` - Root level group creation
2. `test_create_child_group` - Child group with parent_id
3. `test_create_deeply_nested_groups` - Multiple hierarchy levels
4. `test_get_groups_returns_nested_structure` - Fetch all groups with relationships
5. `test_create_playlist_in_nested_group` - Playlist in child group
6. `test_move_group_to_parent` - Moving groups in hierarchy
7. `test_prevent_circular_reference` - Invalid move prevention
8. `test_delete_parent_group_moves_children_to_root` - Cascade behavior
9. `test_get_group_with_parent_details` - Single group fetch with parent info

## Verification Steps

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:3000` (or port 5173)
3. Database migrations applied
4. Test user credentials available

### Running Frontend E2E Tests

```bash
# From the project root
cd frontend

# Install dependencies (if not already installed)
npm install

# Run the specific nested folders test
npx playwright test nested-playlist-folders.spec.ts

# Run with UI mode for visual debugging
npx playwright test nested-playlist-folders.spec.ts --ui

# Run with headed mode to see browser
npx playwright test nested-playlist-folders.spec.ts --headed
```

### Running Backend Integration Tests

```bash
# From the project root
cd backend

# Install test dependencies (if not already installed)
pip install -r tests/requirements-test.txt

# Run the specific nested folders test
pytest tests/integration/test_nested_playlist_groups.py -v

# Run with coverage
pytest tests/integration/test_nested_playlist_groups.py --cov=src.services.playlist_group_service --cov-report=html

# Run with detailed output
pytest tests/integration/test_nested_playlist_groups.py -vv -s
```

### Running All Related Tests

```bash
# Backend - All integration tests
cd backend
pytest tests/integration/ -v

# Frontend - All e2e tests
cd frontend
npx playwright test

# Both (from project root)
cd backend && pytest tests/integration/test_nested_playlist_groups.py -v
cd ../frontend && npx playwright test nested-playlist-folders.spec.ts
```

## Expected Results

### Successful Test Run Should Show:

1. **Parent Group Created**
   - `parent_id` is `null`
   - Group has valid `id`, `user_id`, `created_at`
   - Position and other fields set correctly

2. **Child Group Created**
   - `parent_id` matches parent group's `id`
   - All other fields valid
   - Relationship established in database

3. **Playlist in Child Group**
   - `group_id` matches child group's `id`
   - Playlist accessible via child group
   - Hierarchy: Parent → Child → Playlist

4. **Folder Tree Displays Correctly**
   - Parent group visible at root level
   - Child group nested under parent (visually indented)
   - Playlist visible inside child group
   - Expand/collapse functionality works

5. **Circular Reference Prevented**
   - Attempting to set parent's parent to its child fails
   - Returns 400 or 422 status code
   - Error message indicates circular reference

## Manual Verification Steps

### Via API (using curl or Postman)

1. **Create Parent Group:**
```bash
curl -X POST http://localhost:8000/api/playlists/groups \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Music Collection",
    "description": "My music folders",
    "position": 0
  }'
```
Expected: Group created with `parent_id: null`

2. **Create Child Group:**
```bash
curl -X POST http://localhost:8000/api/playlists/groups \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rock Classics",
    "parent_id": "PARENT_GROUP_ID",
    "position": 0
  }'
```
Expected: Group created with `parent_id: "PARENT_GROUP_ID"`

3. **Create Playlist in Child:**
```bash
curl -X POST http://localhost:8000/api/playlists/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Best Rock Songs",
    "group_id": "CHILD_GROUP_ID",
    "items": []
  }'
```
Expected: Playlist created with `group_id: "CHILD_GROUP_ID"`

4. **Verify Hierarchy:**
```bash
curl http://localhost:8000/api/playlists/groups \
  -H "Authorization: Bearer YOUR_TOKEN"
```
Expected: Both groups returned with correct parent relationships

### Via Browser UI

1. Navigate to `http://localhost:3000/user-playlists`
2. Click "New Folder" button
3. Create "Music Collection" folder
4. Click the folder to select it
5. Create "Rock Classics" folder (should have option to select parent)
6. Select "Rock Classics" folder
7. Create "Best Rock Songs" playlist
8. Verify folder tree shows:
   ```
   📁 Music Collection
     📁 Rock Classics
       🎵 Best Rock Songs
   ```

## Success Criteria

✅ **All tests pass:**
- Frontend e2e tests: 6/6 pass
- Backend integration tests: 9/9 pass

✅ **No circular references possible:**
- API rejects invalid parent assignments
- Database constraints enforced

✅ **Visual hierarchy correct:**
- Folder tree displays nesting with indentation
- Expand/collapse works for nested folders
- Playlists appear in correct folder

✅ **Database relationships maintained:**
- Parent-child foreign keys valid
- Orphan handling works (delete parent → children to root)
- Moving groups updates relationships correctly

## Troubleshooting

### Common Issues

1. **Auth Errors (401)**
   - Ensure test user exists and is approved
   - Check token is valid and not expired
   - Verify Authorization header format

2. **Database Errors**
   - Run migrations: `alembic upgrade head`
   - Check database connection string
   - Verify PlaylistGroup model has parent_id column

3. **Frontend Test Failures**
   - Check mock API responses match actual API format
   - Ensure frontend server is running
   - Verify DOM selectors match component structure

4. **Backend Test Failures**
   - Check fixtures are creating test data correctly
   - Verify db_session is committed/refreshed as needed
   - Check circular reference logic in PlaylistGroupService

### Debug Commands

```bash
# Check database for groups
psql -U postgres -d sattva -c "SELECT id, name, parent_id, position FROM playlist_groups;"

# Count groups by parent
psql -U postgres -d sattva -c "SELECT parent_id, COUNT(*) FROM playlist_groups GROUP BY parent_id;"

# Check playlists in groups
psql -U postgres -d sattva -c "SELECT p.name, g.name as group_name, pg.name as parent_group FROM playlists p JOIN playlist_groups g ON p.group_id = g.id LEFT JOIN playlist_groups pg ON g.parent_id = pg.id;"

# Test API directly
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/playlists/groups | jq
```

## Notes

- Tests use test user authentication
- Database changes in tests are rolled back or cleaned up
- Frontend tests mock API responses for speed and reliability
- Backend tests use actual database transactions
- Screenshot artifacts saved to `frontend/tests/e2e/artifacts/`
