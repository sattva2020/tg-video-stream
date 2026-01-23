# Integration Tests

End-to-end integration tests for the live streaming feature.

## Prerequisites

Before running integration tests, ensure the following services are running:

### Required Services
- **MediaMTX (rtmp-ingest)**: RTMP ingestion server on `rtmp://localhost:1935`
- **Backend API**: FastAPI server on `http://localhost:8000`
- **Streamer**: PyTgCalls streamer service
- **PostgreSQL**: Database server
- **Redis**: State management

### Required Tools
- **FFmpeg**: For RTMP stream injection
  ```bash
  # Check if FFmpeg is available
  ffmpeg -version
  ```
- **FFprobe**: For recording verification (included with FFmpeg)
  ```bash
  # Check if FFprobe is available
  ffprobe -version
  ```

### Required Environment Variables

Create a `.env.test` file or set these environment variables:

```bash
# Backend API
BACKEND_URL=http://localhost:8000

# Authentication (get from admin panel or API)
TEST_USER_TOKEN=your_test_token_here

# Telegram
TEST_TELEGRAM_CHAT_ID=-1001234567890

# RTMP Configuration
RTMP_URL=rtmp://localhost:1935/live

# FFmpeg path (if not in PATH)
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe

# Recordings path
RECORDINGS_PATH=./data/recordings

# Stream duration for recording tests (in seconds, default 10 for tests, 300 for production)
TEST_STREAM_DURATION=10

# Optional: Test video source
TEST_VIDEO_SOURCE=test_assets/test_video.mp4
```

### Getting Test User Token

1. Start the backend services
2. Create a test user via the API or admin panel
3. Use the token from login response or admin panel

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v -m e2e
```

### Run Specific Test

```bash
# Main E2E test
pytest tests/integration/test_live_streaming_e2e.py::test_rtmp_to_telegram_broadcast -v

# Lifecycle test
pytest tests/integration/test_live_streaming_e2e.py::test_live_stream_lifecycle -v

# API endpoints test (no streaming required)
pytest tests/integration/test_live_streaming_e2e.py::test_live_stream_api_endpoints -v

# Recording and playback test
pytest tests/integration/test_live_stream_recording.py::test_live_stream_recording_and_playback -v

# Recording metadata test
pytest tests/integration/test_live_stream_recording.py::test_live_stream_recording_metadata -v

# Recording format test
pytest tests/integration/test_live_stream_recording.py::test_live_stream_recording_format -v

# Recording list test
pytest tests/integration/test_live_stream_recording.py::test_live_stream_recording_list -v
```

### Run with Detailed Output

```bash
pytest tests/integration/test_live_streaming_e2e.py -v -s
```

### Run and Generate Coverage Report

```bash
pytest tests/integration/ --cov=backend/src --cov-report=html
```

## Test Descriptions

### `test_rtmp_to_telegram_broadcast`

**Purpose**: Verifies complete RTMP to Telegram broadcast workflow

**Steps**:
1. Create live stream via API
2. Inject RTMP stream using FFmpeg
3. Start live stream via API
4. Verify stream reaches active status
5. Monitor stream for 10 seconds
6. Stop live stream
7. Verify recording is saved

**Duration**: ~60-90 seconds

**Dependencies**: All services + FFmpeg + valid auth token

### `test_live_stream_lifecycle`

**Purpose**: Verifies stream can be restarted after stopping

**Steps**:
1. Create and start live stream
2. Stop stream
3. Restart stream
4. Verify it becomes active again
5. Clean up

**Duration**: ~45-60 seconds

**Dependencies**: All services + FFmpeg + valid auth token

### `test_live_stream_api_endpoints`

**Purpose**: Verifies API endpoints without actual streaming

**Steps**:
1. Create live stream via API
2. Fetch stream details
3. List all streams
4. Verify data structures

**Duration**: ~5 seconds

**Dependencies**: Backend API only + valid auth token

### Recording Tests (`test_live_stream_recording.py`)

#### `test_live_stream_recording_and_playback`

**Purpose**: Verifies complete recording and playback workflow

**Steps**:
1. Create live stream with recording enabled
2. Inject RTMP stream for specified duration
3. Start live stream via API
4. Verify stream reaches active status
5. Wait for streaming duration (10s for tests, 300s for production)
6. Stop live stream
7. Wait for recording to finish processing (up to 120s)
8. Download recording via API
9. Verify recording metadata (duration, format, file size)
10. Verify recording plays back correctly with FFprobe

**Duration**: ~150-180 seconds

**Dependencies**: All services + FFmpeg + FFprobe + valid auth token

**Verification**:
- Recording status is "ready"
- Duration within expected range (±20% tolerance)
- File size > 0
- Format is supported (mp4, webm, mkv, hls)
- Video and audio streams present
- FFprobe can parse the file

#### `test_live_stream_recording_metadata`

**Purpose**: Verifies recording contains all required metadata fields

**Steps**:
1. Create and start stream with recording
2. Stop stream and wait for recording
3. Verify all required fields present
4. Verify field types and values

**Duration**: ~60 seconds

**Dependencies**: All services + FFmpeg + valid auth token

#### `test_live_stream_recording_format`

**Purpose**: Verifies recording is saved in correct format

**Steps**:
1. Create and start stream
2. Stop stream and wait for recording
3. Verify format is supported (MP4/WebM/MKV/HLS)

**Duration**: ~60 seconds

**Dependencies**: All services + FFmpeg + valid auth token

#### `test_live_stream_recording_list`

**Purpose**: Verifies recordings can be listed via API

**Steps**:
1. Create stream
2. Verify recordings list is initially empty
3. Start and stop stream
4. Verify recording appears in list

**Duration**: ~60 seconds

**Dependencies**: All services + FFmpeg + valid auth token

## Test Video Assets

For realistic testing, you can provide a test video:

```bash
# Create test video directory
mkdir -p test_assets

# Download or create a test video
# Or let the test generate a test pattern automatically
```

If no test video is provided, FFmpeg will generate a color bar test pattern with audio tone.

## Troubleshooting

### Tests Fail with "Backend not reachable"

**Solution**: Ensure backend is running:
```bash
docker-compose up -d backend
# or
cd backend && uvicorn src.main:app --reload
```

### Tests Fail with "FFmpeg not available"

**Solution**: Install FFmpeg (includes FFprobe):
- **Windows**: `choco install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Tests Fail with "FFprobe not available"

**Solution**: FFprobe is included with FFmpeg. If you have FFmpeg but not FFprobe:
- Reinstall FFmpeg completely
- Or add FFmpeg to your PATH manually

### Tests Fail with "TEST_USER_TOKEN not configured"

**Solution**: Set the environment variable or create `.env.test` file with a valid token.

### RTMP Stream Fails to Connect

**Solution**: Ensure MediaMTX is running:
```bash
docker-compose up -d rtmp-ingest
docker-compose logs -f rtmp-ingest
```

### Stream Does Not Become Active

**Possible causes**:
1. Streamer service not running
2. FFmpeg not pushing stream
3. RTMP URL configuration mismatch

**Debug steps**:
1. Check MediaMTX logs: `docker-compose logs rtmp-ingest`
2. Check streamer logs: `docker-compose logs streamer`
3. Verify FFmpeg output for errors
4. Check RTMP URL in test configuration

### Recording Not Saved

**Possible causes**:
1. Recording service not configured
2. File permissions issue
3. Recording path not writable
4. Recording processing timeout

**Debug steps**:
1. Check recording directory permissions: `ls -la data/recordings`
2. Check backend logs for recording errors
3. Verify `RECORDINGS_PATH` environment variable
4. Check RecordingService Celery tasks are running: `docker-compose logs celery`

### Recording Verification Fails

**Possible causes**:
1. FFprobe not available
2. Recording file corrupted
3. Recording format not supported

**Debug steps**:
1. Verify FFprobe works: `ffprobe -version`
2. Check recording file manually: `ffprobe /path/to/recording.mp4`
3. Review RecordingService logs for processing errors
4. Verify recording format is supported

### Recording Processing Timeout

**Possible causes**:
1. Recording too long
2. FFmpeg post-processing slow
3. Insufficient disk space

**Debug steps**:
1. Check disk space: `df -h`
2. Reduce TEST_STREAM_DURATION for faster tests
3. Check FFmpeg processing logs: `docker-compose logs backend | grep ffmpeg`
4. Verify recording post-processing tasks are running

## CI/CD Integration

For automated CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Start services
  run: docker-compose up -d

- name: Run integration tests
  env:
    TEST_USER_TOKEN: ${{ secrets.TEST_USER_TOKEN }}
    TEST_TELEGRAM_CHAT_ID: ${{ secrets.TEST_TELEGRAM_CHAT_ID }}
  run: |
    pytest tests/integration/ -v -m e2e \
      --timeout=300 \
      --continue-on-errors
```

## Best Practices

1. **Always clean up**: Tests use try/finally to ensure cleanup
2. **Use unique names**: Each test uses unique stream titles
3. **Skip gracefully**: Tests skip with descriptive messages if prerequisites not met
4. **Timeout handling**: Tests have reasonable timeouts for async operations
5. **Idempotent**: Tests can be run multiple times without side effects

## Adding New Tests

When adding new integration tests:

1. Follow the existing pattern with `LiveStreamingE2ETest` helper class
2. Use pytest markers (`@pytest.mark.e2e`)
3. Include proper cleanup in finally blocks
4. Document prerequisites in this README
5. Skip tests if required services/tools not available
6. Use environment variables for configuration

## Support

For issues or questions about integration tests, refer to:
- Main spec: `.auto-claude/specs/019-real-time-live-streaming-capabilities/spec.md`
- Build progress: `.auto-claude/specs/019-real-time-live-streaming-capabilities/build-progress.txt`
- Implementation plan: `.auto-claude/specs/019-real-time-live-streaming-capabilities/implementation_plan.json`
