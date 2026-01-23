# Verification: Shuffle and Repeat Modes

This document provides comprehensive testing and verification instructions for shuffle and repeat mode functionality in playlists.

## Overview

Shuffle and repeat modes control playlist playback behavior:
- **Shuffle mode** (`is_shuffled`): When enabled, playlist items play in random order
- **Repeat mode** (`repeat_mode`): Controls playlist looping behavior
  - `none`: Stop after last item (default)
  - `one`: Repeat current item indefinitely
  - `all`: Loop through entire playlist continuously

## Test Coverage

### Backend Integration Tests (16 test cases)

**Location:** `backend/tests/integration/test_shuffle_repeat_modes.py`

1. `test_create_playlist_with_shuffle_enabled` - Create playlist with shuffle=True
2. `test_create_playlist_with_shuffle_disabled` - Create playlist with shuffle=False
3. `test_create_playlist_with_repeat_none` - Create playlist with repeat_mode="none"
4. `test_create_playlist_with_repeat_one` - Create playlist with repeat_mode="one"
5. `test_create_playlist_with_repeat_all` - Create playlist with repeat_mode="all"
6. `test_update_playlist_shuffle_mode` - Update shuffle from False to True
7. `test_update_playlist_repeat_mode_to_one` - Update repeat_mode to "one"
8. `test_update_playlist_repeat_mode_to_all` - Update repeat_mode to "all"
9. `test_update_playlist_both_shuffle_and_repeat` - Update both settings together
10. `test_get_playlist_returns_shuffle_and_repeat` - GET returns shuffle/repeat settings
11. `test_list_playlists_includes_shuffle_and_repeat` - List includes shuffle/repeat
12. `test_invalid_repeat_mode_is_rejected` - Invalid repeat_mode rejected with 422
13. `test_default_shuffle_and_repeat_values` - Default values are correct
14. `test_update_shuffle_to_false` - Update shuffle from True to False
15. `test_update_repeat_mode_from_all_to_none` - Update repeat_mode from "all" to "none"
16. `test_update_repeat_mode_from_all_to_none` - Update repeat_mode from "all" to "none"

### Frontend E2E Tests (17 test cases)

**Location:** `frontend/tests/e2e/shuffle-repeat-modes.spec.ts`

1. `should create playlist with shuffle enabled` - Create with is_shuffled=true
2. `should create playlist with shuffle disabled` - Create with is_shuffled=false
3. `should create playlist with repeat mode NONE` - Create with repeat_mode="none"
4. `should create playlist with repeat mode ONE` - Create with repeat_mode="one"
5. `should create playlist with repeat mode ALL` - Create with repeat_mode="all"
6. `should update playlist shuffle mode from false to true` - Enable shuffle
7. `should update playlist shuffle mode from true to false` - Disable shuffle
8. `should update playlist repeat mode to ONE` - Change to repeat one
9. `should update playlist repeat mode to ALL` - Change to repeat all
10. `should update both shuffle and repeat mode together` - Update both
11. `should get playlist with shuffle and repeat settings` - GET returns settings
12. `should list playlists with shuffle and repeat settings` - List includes settings
13. `should reject invalid repeat mode` - Invalid mode returns 422
14. `should use default values for shuffle and repeat` - Defaults work correctly
15. `should require authentication for creating playlists` - Auth required for POST
16. `should require authentication for updating playlists` - Auth required for PUT

## Running Tests

### Backend Tests

```bash
# Run all shuffle/repeat integration tests
cd backend
pytest tests/integration/test_shuffle_repeat_modes.py -v

# Run specific test
pytest tests/integration/test_shuffle_repeat_modes.py::test_create_playlist_with_shuffle_enabled -v

# Run with coverage
pytest tests/integration/test_shuffle_repeat_modes.py --cov=src.models.schedule --cov=src.api.schedule.playlists -v
```

### Frontend Tests

```bash
# Run all shuffle/repeat E2E tests
cd frontend
npm run test:e2e shuffle-repeat-modes

# Run specific test file
npx playwright test shuffle-repeat-modes.spec.ts

# Run with UI mode for debugging
npx playwright test shuffle-repeat-modes.spec.ts --ui
```

## Manual Verification Steps

### API Testing with curl

#### 1. Create playlist with shuffle enabled

```bash
curl -X POST http://localhost:8000/api/schedule/playlists \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Shuffled Playlist",
    "is_shuffled": true,
    "items": [
      {"url": "https://www.youtube.com/watch?v=video1", "title": "Video 1", "duration": 180, "type": "youtube"},
      {"url": "https://www.youtube.com/watch?v=video2", "title": "Video 2", "duration": 240, "type": "youtube"}
    ]
  }'
```

**Expected Response:** 201 Created with `"is_shuffled": true`

#### 2. Create playlist with repeat mode ALL

```bash
curl -X POST http://localhost:8000/api/schedule/playlists \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Looping Playlist",
    "repeat_mode": "all",
    "items": [
      {"url": "https://www.youtube.com/watch?v=video1", "title": "Video 1", "duration": 180, "type": "youtube"}
    ]
  }'
```

**Expected Response:** 201 Created with `"repeat_mode": "all"`

#### 3. Update playlist shuffle mode

```bash
curl -X PUT http://localhost:8000/api/schedule/playlists/PLAYLIST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_shuffled": true
  }'
```

**Expected Response:** 200 OK with `"is_shuffled": true`

#### 4. Update playlist repeat mode

```bash
curl -X PUT http://localhost:8000/api/schedule/playlists/PLAYLIST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repeat_mode": "one"
  }'
```

**Expected Response:** 200 OK with `"repeat_mode": "one"`

#### 5. Get playlist with settings

```bash
curl -X GET http://localhost:8000/api/schedule/playlists/PLAYLIST_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:** 200 OK with both `is_shuffled` and `repeat_mode` fields

#### 6. List all playlists

```bash
curl -X GET http://localhost:8000/api/schedule/playlists \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:** 200 OK with array of playlists, each containing `is_shuffled` and `repeat_mode`

### Database Verification

```sql
-- Check playlist shuffle and repeat settings
SELECT id, name, is_shuffled, repeat_mode, items_count
FROM playlists
WHERE user_id = 'YOUR_USER_ID';

-- Verify repeat_mode enum values
SELECT DISTINCT repeat_mode FROM playlists;

-- Count playlists by shuffle mode
SELECT is_shuffled, COUNT(*) as count
FROM playlists
GROUP BY is_shuffled;

-- Count playlists by repeat mode
SELECT repeat_mode, COUNT(*) as count
FROM playlists
GROUP BY repeat_mode;
```

### Browser Verification

1. **Navigate to playlists page:**
   - Open `http://localhost:3000/user-playlists`
   - Login with test credentials

2. **Create a new playlist:**
   - Click "New Playlist" button
   - Enter name: "Test Shuffle Playlist"
   - Add some items
   - Enable shuffle toggle (if UI has it)
   - Select repeat mode from dropdown (if UI has it)
   - Click "Save"

3. **Verify settings persisted:**
   - Open the playlist
   - Check that shuffle toggle shows correct state
   - Check that repeat mode dropdown shows correct value

4. **Update settings:**
   - Toggle shuffle on/off
   - Change repeat mode
   - Click "Save"
   - Refresh page and verify settings are saved

## Success Criteria

### All Tests Pass
- ✅ All 16 backend integration tests pass
- ✅ All 16 frontend E2E tests pass
- ✅ No console errors in browser during E2E tests
- ✅ All API calls return correct status codes

### API Behavior
- ✅ Playlists can be created with shuffle=True or shuffle=False
- ✅ Playlists can be created with repeat_mode="none", "one", or "all"
- ✅ Shuffle mode can be updated via PUT endpoint
- ✅ Repeat mode can be updated via PUT endpoint
- ✅ Both settings can be updated simultaneously
- ✅ Invalid repeat_mode values are rejected with 422
- ✅ Default values are: is_shuffled=false, repeat_mode="none"

### Database Verification
- ✅ `is_shuffled` column stores boolean correctly
- ✅ `repeat_mode` column stores enum values correctly
- ✅ Values persist across updates
- ✅ Enum constraint rejects invalid values

### Frontend Integration
- ✅ API client can send and receive shuffle/repeat settings
- ✅ UI components display shuffle/repeat settings correctly
- ✅ UI updates settings via API calls
- ✅ Settings persist across page refreshes

## Troubleshooting

### Backend Tests Fail

**Problem:** Test fails with 404 Not Found

**Solution:**
- Verify backend server is running on port 8000
- Check that database migrations are applied
- Ensure test user exists in database

**Problem:** Test fails with 422 Validation Error

**Solution:**
- Verify request payload matches expected schema
- Check that repeat_mode value is one of: "none", "one", "all"
- Verify is_shuffled is a boolean value

**Problem:** Database assertion fails

**Solution:**
- Check that database session is committed before assertions
- Verify correct playlist ID is used
- Ensure database has latest schema with is_shuffled and repeat_mode columns

### Frontend Tests Fail

**Problem:** E2E test fails with network error

**Solution:**
- Verify backend API is accessible from frontend
- Check CORS settings allow requests
- Ensure API_URL environment variable is correct

**Problem:** Authentication fails

**Solution:**
- Verify test user exists in database
- Check JWT secret is configured correctly
- Ensure login endpoint returns access_token

**Problem:** UI elements not found

**Solution:**
- Verify frontend is built and serving on correct port
- Check that UI components for shuffle/repeat exist
- Ensure page has fully loaded before interactions

### Missing Functionality

**Problem:** Shuffle or repeat mode not in API response

**Solution:**
- Verify PlaylistResponse schema includes is_shuffled and repeat_mode
- Check that database model has these fields
- Ensure API endpoint returns model fields correctly

**Problem:** Update endpoint doesn't change shuffle/repeat

**Solution:**
- Verify PlaylistUpdate schema accepts is_shuffled and repeat_mode
- Check that update_playlist service method handles these fields
- Ensure database commit is called after update

## Test Data

### Sample Playlist Items

```json
[
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "duration": 212,
    "type": "youtube"
  },
  {
    "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "title": "Gangnam Style",
    "duration": 252,
    "type": "youtube"
  },
  {
    "url": "https://vimeo.com/148751763",
    "title": "Vimeo Staff Pick",
    "duration": 180,
    "type": "vimeo"
  },
  {
    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "title": "Me at the zoo",
    "duration": 19,
    "type": "youtube"
  }
]
```

### Test Playlists

1. **Shuffled Playlist:** is_shuffled=true, repeat_mode="none"
2. **Ordered Playlist:** is_shuffled=false, repeat_mode="none"
3. **Repeat One Playlist:** is_shuffled=false, repeat_mode="one"
4. **Repeat All Playlist:** is_shuffled=false, repeat_mode="all"
5. **Shuffled Repeat All:** is_shuffled=true, repeat_mode="all"

## Expected Results Summary

| Test Case | Expected Status | Expected Response |
|-----------|----------------|-------------------|
| Create with shuffle=true | 201 | is_shuffled=true |
| Create with shuffle=false | 201 | is_shuffled=false |
| Create with repeat="none" | 201 | repeat_mode="none" |
| Create with repeat="one" | 201 | repeat_mode="one" |
| Create with repeat="all" | 201 | repeat_mode="all" |
| Update shuffle mode | 200 | is_shuffled=updated_value |
| Update repeat mode | 200 | repeat_mode=updated_value |
| Update both settings | 200 | Both fields updated |
| Get playlist | 200 | Includes shuffle and repeat |
| List playlists | 200 | All items include settings |
| Invalid repeat mode | 422 | Validation error |
| Missing auth | 401 | Unauthorized error |

## Additional Notes

- The shuffle flag (`is_shuffled`) indicates whether the playback system should randomize item order
- The repeat mode (`repeat_mode`) controls looping behavior: none (stop), one (repeat item), all (loop playlist)
- These settings are independent and can be combined (e.g., shuffled + repeat all)
- The actual playback logic that implements shuffling and repeating is handled by the streaming/player system
- This verification only tests the storage and retrieval of these settings, not the actual playback behavior
