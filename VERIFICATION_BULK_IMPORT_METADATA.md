# Subtask 5-4: End-to-End Test - Bulk Import YouTube/Vimeo with Metadata

## Overview
This document describes the end-to-end tests for bulk importing YouTube and Vimeo playlists with automatic metadata fetching (titles, durations, thumbnails), verifying that all metadata is correctly retrieved and stored.

## Test Files Created

### 1. Frontend E2E Test
**File:** `frontend/tests/e2e/bulk-import-metadata.spec.ts`

**Framework:** Playwright (TypeScript)

**What it tests:**
- Bulk import of YouTube playlist URLs
- Bulk import of Vimeo video URLs
- Mixed imports (YouTube + Vimeo in single request)
- Metadata fetching (title, duration, thumbnails)
- Thumbnail storage and retrieval
- Error handling for invalid URLs
- Authentication requirements

**Test Cases:**
1. **Step 1: Import YouTube playlist URL** - Verifies bulk import endpoint accepts YouTube playlist URLs
2. **Step 2: Verify YouTube playlist items have thumbnails** - Checks metadata is fetched and thumbnails are stored
3. **Step 3: Import multiple YouTube playlists in bulk** - Tests multiple URLs in single request
4. **Step 4: Import Vimeo video URL** - Verifies Vimeo URL import
5. **Step 5: Verify Vimeo video has metadata and thumbnail** - Checks Vimeo metadata extraction
6. **Step 6: Import mixed YouTube and Vimeo URLs** - Tests mixed URL types
7. **Step 7: Verify both YouTube and Vimeo items in playlist** - Confirms both types work together
8. **Step 8: Verify invalid URL is handled gracefully** - Tests error handling
9. **Step 9: Verify mixed valid and invalid URLs** - Tests partial success scenarios
10. **Step 10: Verify empty URL array returns error** - Tests validation
11. **API: Bulk import endpoint accepts correct payload** - Tests API contract
12. **API: Bulk import requires authentication** - Tests security

### 2. Backend Integration Test
**File:** `backend/tests/integration/test_bulk_import_metadata.py`

**Framework:** Pytest (Python)

**What it tests:**
- Bulk import of YouTube playlists and videos
- Bulk import of Vimeo videos
- Mixed URL imports
- Error handling for invalid URLs
- Authentication requirements
- Channel ID parameter handling
- Metadata storage (title, duration, type, thumbnail)
- Type detection (youtube, vimeo, stream)
- Thumbnail URL validation
- Response structure validation

**Test Cases:**
1. `test_bulk_import_youtube_playlist` - YouTube playlist URL import
2. `test_bulk_import_youtube_video` - YouTube video URL import
3. `test_bulk_import_youtube_short_url` - YouTube short URL (youtu.be) import
4. `test_bulk_import_vimeo_video` - Vimeo video URL import
5. `test_bulk_import_vimeo_with_player_url` - Vimeo player URL import
6. `test_bulk_import_mixed_youtube_vimeo` - Mixed YouTube and Vimeo URLs
7. `test_bulk_import_invalid_url` - Invalid URL error handling
8. `test_bulk_import_empty_url_array` - Empty array validation
9. `test_bulk_import_mixed_valid_invalid_urls` - Partial success handling
10. `test_bulk_import_requires_authentication` - Authentication requirement
11. `test_bulk_import_with_channel_id` - Optional channel_id parameter
12. `test_playlist_items_have_metadata` - Metadata storage verification
13. `test_playlist_items_type_detection` - Correct type detection
14. `test_thumbnail_urls_are_valid` - Thumbnail URL validation
15. `test_bulk_import_response_structure` - API response structure
16. `test_bulk_import_multiple_urls` - Multiple URL handling

## Verification Steps

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:3000` (or port 5173)
3. Database migrations applied
4. Test user credentials available
5. `yt-dlp` installed for metadata fetching

### Running Frontend E2E Tests

```bash
# From the project root
cd frontend

# Install dependencies (if not already installed)
npm install

# Install Playwright browsers (if not already installed)
npx playwright install

# Run the specific bulk import test
npx playwright test bulk-import-metadata.spec.ts

# Run with UI mode for visual debugging
npx playwright test bulk-import-metadata.spec.ts --ui

# Run with headed mode to see browser
npx playwright test bulk-import-metadata.spec.ts --headed

# Run with debug mode
npx playwright test bulk-import-metadata.spec.ts --debug
```

### Running Backend Integration Tests

```bash
# From the project root
cd backend

# Install test dependencies (if not already installed)
pip install -r tests/requirements-test.txt

# Run the specific bulk import test
pytest tests/integration/test_bulk_import_metadata.py -v

# Run with coverage
pytest tests/integration/test_bulk_import_metadata.py --cov=src.api.routes.playlists --cov-report=html

# Run with detailed output
pytest tests/integration/test_bulk_import_metadata.py -vv -s

# Run specific test case
pytest tests/integration/test_bulk_import_metadata.py::test_bulk_import_youtube_playlist -v
```

### Running All Related Tests

```bash
# Frontend: Run all playlist-related e2e tests
cd frontend
npx playwright test playlist-templates.spec.ts nested-playlist-folders.spec.ts smart-playlists.spec.ts bulk-import-metadata.spec.ts

# Backend: Run all playlist integration tests
cd backend
pytest tests/integration/test_playlist_templates.py tests/integration/test_nested_playlist_groups.py tests/integration/test_smart_playlists.py tests/integration/test_bulk_import_metadata.py -v
```

## Expected Results

### Frontend E2E Tests

All 12 test cases should pass:

1. ✅ YouTube playlist import succeeds
2. ✅ Playlist items have titles, durations, and thumbnails
3. ✅ Multiple YouTube playlists imported successfully
4. ✅ Vimeo video import succeeds
5. ✅ Vimeo video has metadata and thumbnail
6. ✅ Mixed YouTube and Vimeo URLs processed correctly
7. ✅ Both YouTube and Vimeo items appear in playlist with correct types
8. ✅ Invalid URLs are handled gracefully with error messages
9. ✅ Mixed valid/invalid URLs processed with partial success
10. ✅ Empty URL arrays are rejected with 400 error
11. ✅ API response has correct structure (success_count, failed_count, results, message)
12. ✅ Authentication is required (401 without auth token)

### Backend Integration Tests

All 16 test cases should pass:

1. ✅ `test_bulk_import_youtube_playlist` - Returns 200 with valid response structure
2. ✅ `test_bulk_import_youtube_video` - Imports individual YouTube video
3. ✅ `test_bulk_import_youtube_short_url` - Handles youtu.be short URLs
4. ✅ `test_bulk_import_vimeo_video` - Imports Vimeo videos
5. ✅ `test_bulk_import_vimeo_with_player_url` - Handles player.vimeo.com URLs
6. ✅ `test_bulk_import_mixed_youtube_vimeo` - Processes mixed URL types
7. ✅ `test_bulk_import_invalid_url` - Handles errors gracefully
8. ✅ `test_bulk_import_empty_url_array` - Returns 400 for empty array
9. ✅ `test_bulk_import_mixed_valid_invalid_urls` - Reports success/failure correctly
10. ✅ `test_bulk_import_requires_authentication` - Returns 401 without auth
11. ✅ `test_bulk_import_with_channel_id` - Accepts optional channel_id parameter
12. ✅ `test_playlist_items_have_metadata` - Items have title, duration, type, thumbnail
13. ✅ `test_playlist_items_type_detection` - Correct types detected (youtube, vimeo, stream)
14. ✅ `test_thumbnail_urls_are_valid` - Thumbnail URLs are valid HTTP(S) URLs
15. ✅ `test_bulk_import_response_structure` - Response matches expected schema
16. ✅ `test_bulk_import_multiple_urls` - Handles multiple URLs in single request

## Manual Verification Steps

### 1. Test YouTube Playlist Import via API

```bash
# Login to get auth token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "password": "your-password"}' \
  | jq -r '.access_token')

# Import YouTube playlist
curl -X POST http://localhost:8000/api/playlists/import/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"]
  }' | jq

# Expected response:
# {
#   "success_count": 1,
#   "failed_count": 0,
#   "results": [
#     {
#       "url": "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
#       "success": true,
#       "message": "Import started"
#     }
#   ],
#   "message": "Processed 1 URLs. 1 succeeded, 0 failed."
# }
```

### 2. Verify Playlist with Metadata

```bash
# Wait a few seconds for async import to complete
sleep 10

# Fetch all playlists
curl -X GET http://localhost:8000/api/playlists/ \
  -H "Authorization: Bearer $TOKEN" | jq

# Look for the imported playlist
# Verify items have:
# - title: "Never Gonna Give You Up" or similar
# - duration: > 0
# - type: "youtube"
# - thumbnail: URL to ytimg.com
```

### 3. Test Vimeo Import

```bash
# Import Vimeo video
curl -X POST http://localhost:8000/api/playlists/import/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://vimeo.com/148751763"]
  }' | jq

# Wait and verify
sleep 10

# Fetch playlists again
curl -X GET http://localhost:8000/api/playlists/ \
  -H "Authorization: Bearer $TOKEN" | jq

# Verify Vimeo item has:
# - title: Video title
# - duration: > 0
# - type: "vimeo"
# - thumbnail: URL to vimeocdn.com
```

### 4. Test Mixed Import

```bash
# Import both YouTube and Vimeo in single request
curl -X POST http://localhost:8000/api/playlists/import/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://vimeo.com/148751763"
    ]
  }' | jq

# Expected: success_count + failed_count = 2
```

### 5. Browser Verification

1. Navigate to `http://localhost:3000` or `http://localhost:5173`
2. Login with test credentials
3. Go to User Playlists page
4. Click "Import" button
5. Paste YouTube playlist URL: `https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf`
6. Submit import
7. Wait for import to complete
8. Click on imported playlist
9. Verify:
   - Playlist items display with thumbnails
   - Each item shows title and duration
   - Type indicator shows "YouTube" or "Vimeo"
   - Thumbnails load and display correctly

## Success Criteria

✅ All frontend E2E tests pass (12/12)
✅ All backend integration tests pass (16/16)
✅ YouTube playlists import with all metadata
✅ YouTube videos import with thumbnails
✅ Vimeo videos import with metadata
✅ Mixed imports work correctly
✅ Thumbnails are stored and retrieved correctly
✅ Type detection works (youtube, vimeo, stream)
✅ Invalid URLs are handled gracefully
✅ Authentication is enforced
✅ Response structure matches API contract

## Troubleshooting

### Issue: Tests fail with network errors

**Solution:** Tests mock the `import_playlist_async` function to avoid network calls. If you're running manual tests, ensure:
- Backend server has internet access
- `yt-dlp` is installed: `pip install yt-dlp`
- No firewall blocking YouTube/Vimeo

### Issue: Thumbnails not appearing

**Solution:**
1. Check if metadata fetching completed: `curl http://localhost:8000/api/playlists/ -H "Authorization: Bearer $TOKEN" | jq '.[].items[0].thumbnail'`
2. Verify yt-dlp can extract thumbnails: `yt-dlp --get-thumbnail https://www.youtube.com/watch?v=dQw4w9WgXcQ`
3. Check backend logs for metadata fetching errors

### Issue: Import seems to hang

**Solution:**
- Bulk import runs asynchronously in background
- Check backend logs for progress: `tail -f backend/logs/app.log`
- Wait 10-30 seconds for large playlists
- Verify Celery worker is running (if using Celery)

### Issue: Type detection is wrong

**Solution:**
- Check URL patterns in `backend/src/tasks/media.py`
- Verify `_detect_video_type()` function
- Test URL patterns: `youtube.com`, `youtu.be`, `vimeo.com`

### Issue: Authentication fails

**Solution:**
1. Verify user exists: `curl http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"`
2. Check token is valid: `echo $TOKEN | cut -d'.' -f2 | base64 -d | jq`
3. Ensure user status is "approved"

## Test Data

### YouTube URLs
- Playlist: `https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf` (lofi hip hop radio)
- Video: `https://www.youtube.com/watch?v=dQw4w9WgXcQ` (Rick Roll - classic test video)
- Short URL: `https://youtu.be/dQw4w9WgXcQ`

### Vimeo URLs
- Video: `https://vimeo.com/148751763` (Public test video)
- Player URL: `https://player.vimeo.com/video/148751763`

### Invalid URL
- `https://invalid-url-that-does-not-exist.com/video`

## Notes

- Tests use mocking to avoid actual network calls during automated testing
- Manual verification tests will make real network calls
- Async import may take 5-30 seconds depending on playlist size
- Thumbnails are stored as URLs in the items JSONB field
- Type detection is based on URL pattern and yt-dlp extractor
- The bulk import endpoint is fire-and-forget (returns immediately, processes in background)
- Check the actual playlists endpoint to verify import completion

## Related Documentation

- [Playlist Templates Verification](./VERIFICATION_PLAYLIST_TEMPLATES.md)
- [Nested Folders Verification](./VERIFICATION_NESTED_FOLDERS.md)
- [Smart Playlists Verification](./VERIFICATION_SMART_PLAYLISTS.md)
- [Bulk Import API Spec](./.auto-claude/specs/008-advanced-playlist-management-with-smart-features/spec.md)
