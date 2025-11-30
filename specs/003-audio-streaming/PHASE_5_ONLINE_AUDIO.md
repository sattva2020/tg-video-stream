# Phase 5: Online Audio Sources

**Status**: In Progress
**Owner**: GitHub Copilot
**Date**: 2025-11-27

## 1. Overview

This phase focuses on enabling the streamer to handle direct online audio sources and playlists. This includes:
1.  Streaming audio directly from HTTP(S) URLs (MP3, AAC, etc.).
2.  Improved integration with `yt-dlp` for audio-only extraction (to save bandwidth/processing if video is not needed, though the project is "24/7 TV", so video might be preferred. However, for "Audio" phase, we might want to support audio-only streams visualized or just audio).
3.  Support for M3U playlists fetched from URLs.

## 2. Requirements

### Functional Requirements
-   **FR-001**: The system MUST accept direct HTTP(S) URLs pointing to audio files (mp3, ogg, wav, etc.).
-   **FR-002**: The system MUST accept URLs pointing to M3U/M3U8 playlists and expand them into individual track URLs.
-   **FR-003**: The system SHOULD attempt to detect the content type of the URL (MIME type) to decide how to handle it (direct stream vs playlist).
-   **FR-004**: `yt-dlp` integration should be robust enough to handle YouTube playlists and individual videos, extracting the best available stream.

### Non-Functional Requirements
-   **NFR-001**: Playlist parsing should handle network timeouts and errors gracefully.
-   **NFR-002**: The streamer should fallback or skip invalid entries in a playlist without crashing.

## 3. Implementation Plan

### 3.1. Audio/Playlist Utilities (`streamer/audio_utils.py`)

Create a new module `streamer/audio_utils.py` (or extend `utils.py`) to handle:
-   `is_supported_audio_url(url)`: Check extension or HEAD request MIME type.
-   `parse_remote_playlist(url)`: Fetch and parse M3U/PLS files.
-   `get_stream_info(url)`: Unified function to get the direct stream URL (using `yt-dlp` or direct link).

### 3.2. Integration with `main.py`

Update `play_sequence` in `streamer/main.py` to use the new utilities.
-   When iterating URLs, check if it's a playlist (M3U) and expand it dynamically or pre-expand.
-   Use the appropriate ffmpeg arguments for audio files (maybe generate a placeholder video if it's an audio-only source, since `PyTgCalls` with `AudioVideoPiped` expects video if we are doing a video stream).

**Note**: Since this is a "TV" channel, audio-only sources need a visual component.
-   **Option A**: Use a static image / loop video as background for audio files.
-   **Option B**: Use `ffmpeg` to generate video from audio (e.g., waveform or static image).

For Phase 5, we will implement **Option A** (Static Image/Black Screen) or just let `ffmpeg` handle it (it might fail if no video stream is present in `AudioVideoPiped`).
Actually, `streamer/utils.py` `build_ffmpeg_av_args` sets up video scaling. If the input has no video, ffmpeg might complain or output nothing.
We should ensure `anullsrc` or a static image is used if the source is audio-only.

### 3.3. Tasks

-   [ ] **T049**: Implement `stream_audio_from_url` / `get_direct_url` handling direct HTTP links.
-   [ ] **T050**: Implement MIME-type detection for URLs.
-   [ ] **T053**: Implement `parse_m3u_url` for online playlists.
-   [ ] **T056**: Add error handling and retries for network requests.
-   [ ] **T060**: Update `streamer/main.py` to integrate new logic.

## 4. Testing

-   Unit tests for playlist parsing.
-   Integration tests with dummy HTTP server serving M3U and MP3 files.
