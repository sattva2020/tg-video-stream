import sys
import os
import pytest

# Add streamer directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../streamer'))

import audio_utils
import utils

def test_transcoding_profiles_have_low_latency_flags():
    """
    Verify that all transcoding profiles include Opus low-latency flags.
    """
    required_flags = ['-application', 'lowdelay', '-frame_duration', '20']
    
    for name, profile in audio_utils.TRANSCODING_PROFILES.items():
        args = profile['ffmpeg_args']
        print(f"Checking profile {name}: {args}")
        
        # Check for presence of flags
        for flag in required_flags:
            assert flag in args, f"Profile {name} missing flag {flag}"
            
        # Check specifically for libopus codec
        assert 'libopus' in args
        assert '-c:a' in args

def test_video_args_have_low_latency_flags():
    """
    Verify that video arguments include ultrafast preset and zerolatency tune.
    """
    v_args, _ = utils.build_ffmpeg_av_args("720p")
    print(f"Video args: {v_args}")
    
    assert "-preset" in v_args
    assert "ultrafast" in v_args
    assert "-tune" in v_args
    assert "zerolatency" in v_args

def test_video_args_quality_scaling():
    """
    Verify that quality scaling is preserved while keeping latency flags.
    """
    v_1080, _ = utils.build_ffmpeg_av_args("1080p")
    assert "3500k" in v_1080
    assert "ultrafast" in v_1080
    
    v_480, _ = utils.build_ffmpeg_av_args("480p")
    assert "900k" in v_480
    assert "ultrafast" in v_480

if __name__ == "__main__":
    pytest.main([__file__])
