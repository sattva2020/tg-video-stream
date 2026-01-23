#!/usr/bin/env python3
"""Verification script for VP9 codec support."""

import sys
sys.path.insert(0, 'streamer')

from video_transcoder import VideoTranscoder

# Check if vp9 is in supported codecs
if 'vp9' in VideoTranscoder.SUPPORTED_VIDEO_CODECS:
    print("✓ vp9 found in SUPPORTED_VIDEO_CODECS")
    print(f"  Supported codecs: {VideoTranscoder.SUPPORTED_VIDEO_CODECS}")
    sys.exit(0)
else:
    print("✗ vp9 NOT found in SUPPORTED_VIDEO_CODECS")
    print(f"  Supported codecs: {VideoTranscoder.SUPPORTED_VIDEO_CODECS}")
    sys.exit(1)
