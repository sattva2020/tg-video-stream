"""
Integration test for live stream recording and playback verification.

This test verifies the complete recording workflow:
1. Start live stream with recording enabled
2. Stream for specified duration (5 minutes in production, shorter for tests)
3. Stop stream and wait for recording processing
4. Download recording via API
5. Verify recording plays back correctly
6. Verify recording metadata (duration, format, file size)

Prerequisites:
- MediaMTX service running (rtmp-ingest) with recording enabled
- Backend API running
- RecordingService running with FFmpeg/FFprobe for post-processing
- Test Telegram chat configured
- FFmpeg available for stream injection

Environment Variables:
- BACKEND_URL: Backend API URL (default: http://localhost:8000)
- TEST_TELEGRAM_CHAT_ID: Telegram chat ID for testing
- TEST_USER_TOKEN: Auth token for test user
- RTMP_URL: RTMP server URL (default: rtmp://localhost:1935)
- RECORDINGS_PATH: Local path for recordings (default: ./data/recordings)
- TEST_STREAM_DURATION: Stream duration in seconds (default: 10 for tests, 300 for production)
"""

import os
import asyncio
import pytest
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess
import time
import json

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_TELEGRAM_CHAT_ID = int(os.getenv("TEST_TELEGRAM_CHAT_ID", "-1001234567890"))
TEST_USER_TOKEN = os.getenv("TEST_USER_TOKEN", "")
RTMP_URL = os.getenv("RTMP_URL", "rtmp://localhost:1935/live")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
FFPROBE_PATH = os.getenv("FFPROBE_PATH", "ffprobe")
RECORDINGS_PATH = os.getenv("RECORDINGS_PATH", "./data/recordings")

# Test configuration
TEST_STREAM_DURATION = int(os.getenv("TEST_STREAM_DURATION", "10"))  # 10s for tests, 300s for production
STREAM_TITLE = "Recording Test Live Stream"
TEST_VIDEO_SOURCE = os.getenv("TEST_VIDEO_SOURCE", "test_assets/test_video.mp4")


class LiveStreamRecordingTest:
    """Integration test helper for live stream recording verification."""

    def __init__(self):
        self.backend_url = BACKEND_URL
        self.headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        self.stream_id: Optional[str] = None
        self.recording_id: Optional[str] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.ingestion_url: Optional[str] = None
        self.stream_key: Optional[str] = None

    def create_live_stream(self, title: str = STREAM_TITLE) -> Dict[str, Any]:
        """
        Create a new live stream with recording enabled.

        Returns:
            Created live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams"
        payload = {
            "title": title,
            "chat_id": TEST_TELEGRAM_CHAT_ID,
            "ingestion_type": "rtmp",
            "quality_preset": "720p",
            "max_guests": 0,  # No guests for recording test
            "recording_enabled": True,  # Ensure recording is enabled
            "is_chat_enabled": False
        }

        response = requests.post(url, json=payload, headers=self.headers)
        assert response.status_code == 201, f"Failed to create live stream: {response.text}"

        data = response.json()
        self.stream_id = data["id"]
        self.ingestion_url = data.get("ingestion_url")
        self.stream_key = data.get("stream_key")

        return data

    def get_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Get live stream details by ID.

        Args:
            stream_id: Live stream ID

        Returns:
            Live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to get live stream: {response.text}"
        return response.json()

    def start_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Start a live stream.

        Args:
            stream_id: Live stream ID

        Returns:
            Updated live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/start"
        response = requests.post(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to start live stream: {response.text}"
        return response.json()

    def stop_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Stop a live stream.

        Args:
            stream_id: Live stream ID

        Returns:
            Updated live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/stop"
        response = requests.post(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to stop live stream: {response.text}"
        return response.json()

    def delete_live_stream(self, stream_id: str) -> None:
        """
        Delete a live stream.

        Args:
            stream_id: Live stream ID
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
        response = requests.delete(url, headers=self.headers)
        assert response.status_code in [204, 404], f"Failed to delete live stream: {response.text}"

    def start_rtmp_stream(self, stream_key: str, video_source: str = TEST_VIDEO_SOURCE, duration: int = TEST_STREAM_DURATION) -> subprocess.Popen:
        """
        Start FFmpeg to push RTMP stream to MediaMTX.

        Args:
            stream_key: Stream key for RTMP ingestion
            video_source: Path to video file or test pattern
            duration: Duration in seconds

        Returns:
            FFmpeg subprocess handle
        """
        rtmp_target = f"{RTMP_URL}/{stream_key}"

        # Use test video if available, otherwise generate test pattern
        if os.path.exists(video_source):
            cmd = [
                FFMPEG_PATH,
                "-re",  # Read input at native frame rate
                "-i", video_source,
                "-t", str(duration),  # Limit duration
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2000k",
                "-maxrate", "2000k",
                "-bufsize", "4000k",
                "-pix_fmt", "yuv420p",
                "-g", "50",  # Keyframe every 2 seconds at 25fps
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_target
            ]
        else:
            # Generate test pattern (color bars with tone)
            cmd = [
                FFMPEG_PATH,
                "-f", "lavfi",
                "-i", f"color=c=blue:s=1280x720:d={duration}:r=25",
                "-f", "lavfi",
                "-i", f"sine=frequency=1000:sample_rate=44100:duration={duration}",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2000k",
                "-pix_fmt", "yuv420p",
                "-g", "50",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_target
            ]

        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return self.ffmpeg_process

    def stop_rtmp_stream(self) -> None:
        """Stop FFmpeg RTMP stream."""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
            self.ffmpeg_process = None

    def wait_for_stream_status(
        self,
        stream_id: str,
        expected_status: str,
        timeout_seconds: int = 30,
        poll_interval: float = 0.5
    ) -> Dict[str, Any]:
        """
        Wait for stream to reach expected status.

        Args:
            stream_id: Live stream ID
            expected_status: Expected status value
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Live stream data when status matches

        Raises:
            TimeoutError: If status not reached within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            stream_data = self.get_live_stream(stream_id)
            current_status = stream_data.get("status")

            if current_status == expected_status:
                return stream_data

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Stream {stream_id} did not reach status '{expected_status}' "
            f"within {timeout_seconds}s. Last status: {current_status}"
        )

    def get_recordings_for_stream(self, stream_id: str) -> list:
        """
        Get all recordings for a specific live stream.

        Args:
            stream_id: Live stream ID

        Returns:
            List of recordings
        """
        url = f"{self.backend_url}/api/v1/recordings/stream/{stream_id}"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to get recordings: {response.text}"

        data = response.json()
        return data.get("recordings", [])

    def get_recording(self, recording_id: str) -> Dict[str, Any]:
        """
        Get recording details by ID.

        Args:
            recording_id: Recording ID

        Returns:
            Recording data
        """
        url = f"{self.backend_url}/api/v1/recordings/{recording_id}"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to get recording: {response.text}"
        return response.json()

    def wait_for_recording_ready(
        self,
        stream_id: str,
        timeout_seconds: int = 120,
        poll_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        Wait for recording to be ready after stream stops.

        Args:
            stream_id: Live stream ID
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between checks

        Returns:
            Ready recording data

        Raises:
            TimeoutError: If recording not ready within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            recordings = self.get_recordings_for_stream(stream_id)

            # Find the most recent recording
            if recordings:
                # Sort by created_at descending
                recordings.sort(key=lambda r: r.get("created_at", ""), reverse=True)
                latest_recording = recordings[0]

                if latest_recording.get("status") == "ready":
                    self.recording_id = latest_recording["id"]
                    return latest_recording
                elif latest_recording.get("status") == "error":
                    raise RuntimeError(
                        f"Recording failed with error: {latest_recording.get('error_message', 'Unknown error')}"
                    )

            time.sleep(poll_interval)

        raise TimeoutError(
            f"No ready recording found for stream {stream_id} within {timeout_seconds}s"
        )

    def download_recording(self, recording_id: str, output_path: str) -> str:
        """
        Download recording file to local path.

        Args:
            recording_id: Recording ID
            output_path: Local file path to save recording

        Returns:
            Path to downloaded file
        """
        # First get recording details to get file_url
        recording = self.get_recording(recording_id)

        # Try to download via file_url if available
        file_url = recording.get("file_url")
        if file_url:
            response = requests.get(file_url, stream=True)
            assert response.status_code == 200, f"Failed to download recording: {response.text}"

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return output_path

        # If no file_url, try to construct from file_path
        file_path = recording.get("file_path")
        if file_path and os.path.exists(file_path):
            # Copy file to output path
            import shutil
            shutil.copy(file_path, output_path)
            return output_path

        raise FileNotFoundError(f"Could not find recording file for {recording_id}")

    def verify_recording_metadata(
        self,
        recording: Dict[str, Any],
        expected_duration_min: int,
        expected_duration_max: int
    ) -> bool:
        """
        Verify recording metadata meets expectations.

        Args:
            recording: Recording data
            expected_duration_min: Minimum expected duration in seconds
            expected_duration_max: Maximum expected duration in seconds

        Returns:
            True if metadata is valid

        Raises:
            AssertionError: If metadata does not meet expectations
        """
        # Check required fields
        assert "id" in recording, "Recording missing ID"
        assert "status" in recording, "Recording missing status"
        assert recording["status"] == "ready", f"Recording status is {recording['status']}, expected 'ready'"

        # Check duration
        duration = recording.get("duration")
        assert duration is not None, "Recording missing duration"
        assert expected_duration_min <= duration <= expected_duration_max, \
            f"Recording duration {duration}s not in expected range [{expected_duration_min}, {expected_duration_max}]"

        # Check file size
        file_size = recording.get("file_size")
        assert file_size is not None, "Recording missing file_size"
        assert file_size > 0, f"Recording file_size is {file_size}, expected > 0"

        # Check format
        format_type = recording.get("format")
        assert format_type is not None, "Recording missing format"
        assert format_type in ["mp4", "webm", "mkv", "hls"], \
            f"Recording format {format_type} not in supported formats"

        # Check file path or URL
        assert recording.get("file_path") or recording.get("file_url"), \
            "Recording missing both file_path and file_url"

        # Check timestamps
        assert recording.get("started_at"), "Recording missing started_at"
        assert recording.get("ended_at"), "Recording missing ended_at"
        assert recording.get("created_at"), "Recording missing created_at"

        return True

    def verify_recording_playback(self, recording_file_path: str) -> Dict[str, Any]:
        """
        Verify recording file can be played back using FFprobe.

        Args:
            recording_file_path: Path to recording file

        Returns:
            FFprobe metadata

        Raises:
            AssertionError: If file cannot be played or is invalid
            subprocess.CalledProcessError: If FFprobe fails
        """
        # Run FFprobe to get metadata
        cmd = [
            FFPROBE_PATH,
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            recording_file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        # Verify video stream exists
        streams = metadata.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        assert len(video_streams) > 0, "Recording has no video stream"
        assert len(audio_streams) > 0, "Recording has no audio stream"

        # Verify format
        format_info = metadata.get("format", {})
        assert format_info.get("duration"), "Recording missing duration"
        assert format_info.get("size"), "Recording missing size"

        return {
            "video_streams": len(video_streams),
            "audio_streams": len(audio_streams),
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format_name": format_info.get("format_name", "unknown")
        }

    def delete_recording(self, recording_id: str) -> None:
        """
        Delete a recording.

        Args:
            recording_id: Recording ID
        """
        url = f"{self.backend_url}/api/v1/recordings/{recording_id}"
        response = requests.delete(url, headers=self.headers)
        assert response.status_code in [204, 404], f"Failed to delete recording: {response.text}"

    def cleanup(self) -> None:
        """Clean up test resources."""
        # Stop RTMP stream
        self.stop_rtmp_stream()

        # Delete live stream if it exists
        if self.stream_id:
            try:
                self.delete_live_stream(self.stream_id)
            except Exception:
                pass  # Best effort cleanup

        # Optionally delete recording
        if self.recording_id:
            try:
                self.delete_recording(self.recording_id)
            except Exception:
                pass  # Best effort cleanup


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_stream_recording_and_playback():
    """
    Integration test: Live stream recording and playback verification.

    Test Steps:
    1. Create live stream with recording enabled
    2. Start RTMP stream injection (short duration for tests)
    3. Start live stream via API
    4. Verify stream reaches active status
    5. Wait for streaming duration
    6. Stop live stream
    7. Wait for recording to finish processing
    8. Download recording via API
    9. Verify recording metadata (duration, format, file size)
    10. Verify recording plays back correctly with FFprobe

    Prerequisites:
    - MediaMTX service with recording enabled
    - Backend API running
    - RecordingService with FFmpeg/FFprobe
    - FFmpeg/FFprobe available in PATH
    """
    # Skip if auth token not configured
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    # Skip if ffmpeg not available
    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"FFmpeg not available at {FFMPEG_PATH}")

    # Skip if ffprobe not available
    try:
        subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"FFprobe not available at {FFPROBE_PATH}")

    test = LiveStreamRecordingTest()

    try:
        # Step 1: Create live stream with recording enabled
        stream_data = test.create_live_stream(title="Recording Test Stream")
        assert stream_data["status"] == "idle"
        assert stream_data["recording_enabled"] is True
        assert test.stream_key is not None

        # Step 2: Start RTMP stream injection
        ffmpeg_process = test.start_rtmp_stream(
            test.stream_key,
            duration=TEST_STREAM_DURATION
        )
        assert ffmpeg_process.poll() is None, "FFmpeg process should be running"

        # Give FFmpeg time to start pushing stream
        await asyncio.sleep(2)

        # Step 3: Start live stream via API
        started_stream = test.start_live_stream(test.stream_id)
        assert started_stream["status"] in ["active", "idle"]

        # Step 4: Verify stream reaches active status
        active_stream = test.wait_for_stream_status(
            test.stream_id,
            "active",
            timeout_seconds=30
        )
        assert active_stream["status"] == "active"

        # Step 5: Wait for streaming duration
        await asyncio.sleep(TEST_STREAM_DURATION)

        # Step 6: Stop live stream
        stopped_stream = test.stop_live_stream(test.stream_id)
        assert stopped_stream["status"] == "stopped"

        # Step 7: Wait for recording to finish processing
        recording = test.wait_for_recording_ready(
            test.stream_id,
            timeout_seconds=120
        )
        assert recording["status"] == "ready"
        test.recording_id = recording["id"]

        # Step 8: Download recording via API
        download_path = f"/tmp/test_recording_{test.recording_id}.{recording.get('format', 'mp4')}"
        downloaded_file = test.download_recording(test.recording_id, download_path)
        assert os.path.exists(downloaded_file), "Downloaded recording file does not exist"

        # Step 9: Verify recording metadata
        # Allow 20% tolerance for duration (processing overhead)
        expected_min = int(TEST_STREAM_DURATION * 0.8)
        expected_max = int(TEST_STREAM_DURATION * 1.2)
        test.verify_recording_metadata(recording, expected_min, expected_max)

        # Step 10: Verify recording plays back correctly
        playback_info = test.verify_recording_playback(downloaded_file)
        assert playback_info["video_streams"] > 0, "Recording has no video stream"
        assert playback_info["audio_streams"] > 0, "Recording has no audio stream"
        assert playback_info["duration"] > 0, "Recording has invalid duration"

        # Cleanup downloaded file
        try:
            os.remove(downloaded_file)
        except Exception:
            pass

    finally:
        # Clean up
        test.cleanup()


@pytest.mark.integration
def test_live_stream_recording_metadata():
    """
    Integration test: Recording metadata verification.

    Verifies recording contains all required metadata fields.
    """
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    test = LiveStreamRecordingTest()

    try:
        # Create and start stream
        stream_data = test.create_live_stream(title="Metadata Test")
        test.start_rtmp_stream(test.stream_key, duration=5)
        time.sleep(2)

        test.start_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "active", timeout_seconds=30)
        time.sleep(5)

        test.stop_live_stream(test.stream_id)

        # Wait for recording
        recording = test.wait_for_recording_ready(test.stream_id, timeout_seconds=120)

        # Verify metadata fields
        required_fields = [
            "id", "live_stream_id", "file_path", "status",
            "started_at", "ended_at", "created_at", "format"
        ]

        for field in required_fields:
            assert field in recording, f"Recording missing required field: {field}"

        # Verify field types
        assert isinstance(recording["id"], str)
        assert isinstance(recording["live_stream_id"], str)
        assert isinstance(recording["status"], str)
        assert recording["status"] == "ready"

    finally:
        test.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_stream_recording_format():
    """
    Integration test: Recording format verification.

    Verifies recording is saved in correct format (MP4/WebM/MKV).
    """
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"FFmpeg not available at {FFMPEG_PATH}")

    test = LiveStreamRecordingTest()

    try:
        # Create and start stream
        stream_data = test.create_live_stream(title="Format Test")
        test.start_rtmp_stream(test.stream_key, duration=5)
        await asyncio.sleep(2)

        test.start_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "active", timeout_seconds=30)
        await asyncio.sleep(5)

        test.stop_live_stream(test.stream_id)

        # Wait for recording
        recording = test.wait_for_recording_ready(test.stream_id, timeout_seconds=120)

        # Verify format is supported
        supported_formats = ["mp4", "webm", "mkv", "hls"]
        assert recording["format"] in supported_formats, \
            f"Recording format {recording['format']} not supported"

    finally:
        test.cleanup()


@pytest.mark.integration
def test_live_stream_recording_list():
    """
    Integration test: Recording list API.

    Verifies recordings can be listed via API.
    """
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    test = LiveStreamRecordingTest()

    try:
        # Create stream
        stream_data = test.create_live_stream(title="List Test")

        # List recordings for stream (should be empty initially)
        recordings = test.get_recordings_for_stream(test.stream_id)
        assert isinstance(recordings, list)

        # After streaming, recordings should exist
        test.start_rtmp_stream(test.stream_key, duration=5)
        time.sleep(2)

        test.start_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "active", timeout_seconds=30)
        time.sleep(5)

        test.stop_live_stream(test.stream_id)

        # Wait for recording and verify it appears in list
        recording = test.wait_for_recording_ready(test.stream_id, timeout_seconds=120)
        recordings = test.get_recordings_for_stream(test.stream_id)

        assert len(recordings) > 0, "No recordings found for stream"
        assert any(r["id"] == recording["id"] for r in recordings), \
            "Recording not found in list"

    finally:
        test.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "integration"])
