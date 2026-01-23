# -*- coding: utf-8 -*-
"""
Custom exceptions for video streaming and transcoding services.
Provides consistent error handling with actionable messages.

Example usage:
    from streamer.exceptions import TranscodingError, EncodingProfileError

    if codec not in supported_codecs:
        raise TranscodingError('unsupported_codec', f'codec={codec}')
"""

from typing import Optional, Dict, Any


class StreamerError(Exception):
    """
    Base exception for streaming and transcoding services.

    All specific streamer exceptions inherit from this class,
    allowing catch-all streamer error handling.
    """

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "STREAMER_ERROR"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.code,
            "message": self.message,
        }


class TranscodingError(StreamerError):
    """
    Video transcoding error with actionable error messages.

    Provides specific guidance on how to fix transcoding issues
    (unsupported codecs, invalid parameters, FFmpeg errors, etc.).

    Attributes:
        error_type: Type of transcoding error (unsupported_codec, invalid_bitrate, etc.)
        context: Additional context about the error (e.g., codec=hevc, bitrate=10000)
        actionable_message: Human-readable message with suggested fix

    Example:
        >>> e = TranscodingError('unsupported_codec', 'codec=hevc')
        >>> print(e.actionable_message)
        'Use supported codec: h264, h265, or vp9'
    """

    # Error type to actionable message mapping
    ACTIONABLE_MESSAGES = {
        'unsupported_codec': 'Use supported video codec: h264, h265, or vp9; audio codec: aac, mp3, or opus',
        'invalid_bitrate': 'Set video bitrate between 500-10000 kbps and audio bitrate between 32-320 kbps',
        'invalid_resolution': 'Use resolution format WIDTHxHEIGHT (e.g., 1920x1080, 1280x720)',
        'codec_not_supported': 'Transcode source file to supported codec or install FFmpeg codec support',
        'file_too_large': 'Reduce file size to under 2GB or use streaming transcoding',
        'file_not_found': 'Verify source file URL is accessible and file exists',
        'network_error': 'Check network connection and source URL availability',
        'permission_denied': 'Verify file permissions and ensure FFmpeg has read access',
        'invalid_container': 'Remux to supported container format (mp4, mkv, webm)',
        'orientation_error': 'Re-encode video with proper orientation metadata',
        'filter_error': 'Simplify FFmpeg filter chain or check filter syntax',
        'encoder_error': 'Try different codec preset (ultrafast, superfast, veryfast) or lower bitrate',
        'memory_error': 'Reduce resolution, bitrate, or use lower quality preset',
        'timeout_error': 'Increase timeout, reduce file size, or check network connectivity',
        'corrupted_file': 'Source file is corrupted - re-encode from original source',
        'audio_sync_error': 'Extract and re-encode audio track separately, then remux',
        'pixel_format_error': 'Add -pix_fmt yuv420p to FFmpeg parameters for compatibility',
        'framerate_error': 'Specify valid framerate (e.g., -r 30 for 30fps) in FFmpeg parameters',
    }

    def __init__(
        self,
        error_type: str,
        context: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.error_type = error_type
        self.context = context

        # Generate base error message
        if message:
            msg = message
        elif context:
            msg = f"Transcoding error ({error_type}): {context}"
        else:
            msg = f"Transcoding error: {error_type}"

        # Generate actionable message
        self.actionable_message = self._get_actionable_message()

        super().__init__(msg, code="TRANSCODING_ERROR")

    def _get_actionable_message(self) -> str:
        """
        Get actionable message based on error type.

        Returns a human-readable message with specific guidance
        on how to resolve the transcoding error.
        """
        return self.ACTIONABLE_MESSAGES.get(
            self.error_type,
            'Review FFmpeg logs and verify encoding parameters are compatible'
        )

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["error_type"] = self.error_type
        result["actionable_message"] = self.actionable_message
        if self.context:
            result["context"] = self.context
        return result


class EncodingProfileError(StreamerError):
    """
    Encoding profile configuration error.

    Raised when encoding profile parameters are invalid or incompatible.

    Attributes:
        parameter: The parameter that failed validation
        reason: Human-readable reason for the error
        suggested_value: Optional suggested value for the parameter
    """

    # Parameter-specific actionable messages
    PARAMETER_HINTS = {
        'video_codec': 'Supported: h264 (default), h265, vp9',
        'audio_codec': 'Supported: aac (default), mp3, opus',
        'video_bitrate': 'Recommended: 500-10000 kbps (depends on resolution)',
        'audio_bitrate': 'Recommended: 64-192 kbps (128 kbps is standard)',
        'resolution': 'Format: WIDTHxHEIGHT (e.g., 1920x1080, 1280x720)',
        'video_quality': 'Supported: 480p, 720p, 1080p, 2k, 4k',
    }

    def __init__(
        self,
        parameter: str,
        reason: str,
        suggested_value: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.parameter = parameter
        self.reason = reason
        self.suggested_value = suggested_value

        if message:
            msg = message
        else:
            msg = f"Encoding profile error ({parameter}): {reason}"
            if suggested_value:
                msg += f" | Suggested: {suggested_value}"

        super().__init__(msg, code="ENCODING_PROFILE_ERROR")

    def get_actionable_hint(self) -> Optional[str]:
        """Get actionable hint based on parameter."""
        return self.PARAMETER_HINTS.get(self.parameter)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["parameter"] = self.parameter
        result["reason"] = self.reason
        if self.suggested_value:
            result["suggested_value"] = self.suggested_value
        hint = self.get_actionable_hint()
        if hint:
            result["hint"] = hint
        return result


class FFmpegError(StreamerError):
    """
    FFmpeg execution error with detailed diagnostics.

    Raised when FFmpeg process fails or returns non-zero exit code.

    Attributes:
        exit_code: FFmpeg process exit code
        stderr_output: FFmpeg stderr output
        command: FFmpeg command that failed
        diagnosed_issue: Diagnosed issue type
    """

    # Common FFmpeg error patterns and their meanings
    ERROR_PATTERNS = {
        'Unsupported codec': 'codec_not_supported',
        'Permission denied': 'permission_denied',
        'No such file or directory': 'file_not_found',
        'Invalid data': 'corrupted_file',
        'Connection refused': 'network_error',
        'Connection timed out': 'network_error',
        'Operation not permitted': 'permission_denied',
        'Cannot allocate memory': 'memory_error',
        'Conversion failed': 'encoder_error',
        'Bitrate not specified': 'invalid_bitrate',
        'Error initializing': 'filter_error',
        'Unknown encoder': 'codec_not_supported',
    }

    def __init__(
        self,
        exit_code: int,
        stderr_output: str,
        command: str,
        message: Optional[str] = None,
    ):
        self.exit_code = exit_code
        self.stderr_output = stderr_output
        self.command = command
        self.diagnosed_issue = self._diagnose_issue()

        if message:
            msg = message
        else:
            msg = f"FFmpeg failed (exit code: {exit_code}): {self.diagnosed_issue}"

        super().__init__(msg, code="FFMPEG_ERROR")

    def _diagnose_issue(self) -> str:
        """
        Diagnose FFmpeg error from stderr output.

        Parses FFmpeg stderr to identify the likely cause of failure.
        """
        stderr_lower = self.stderr_output.lower()

        for pattern, issue in self.ERROR_PATTERNS.items():
            if pattern.lower() in stderr_lower:
                return issue

        # Check for common codec issues
        if 'codec' in stderr_lower and ('not found' in stderr_lower or 'unknown' in stderr_lower):
            return 'codec_not_supported'

        # Check for bitrate issues
        if 'bitrate' in stderr_lower:
            return 'invalid_bitrate'

        # Check for resolution/filter issues
        if 'scale' in stderr_lower or 'filter' in stderr_lower:
            return 'filter_error'

        # Default: generic error
        return 'unknown_error'

    def get_actionable_message(self) -> str:
        """Get actionable message based on diagnosed issue."""
        transcoding_error = TranscodingError(self.diagnosed_issue)
        return transcoding_error.actionable_message

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["exit_code"] = self.exit_code
        result["diagnosed_issue"] = self.diagnosed_issue
        result["actionable_message"] = self.get_actionable_message()
        # Only include first 500 chars of stderr to avoid massive responses
        if self.stderr_output:
            result["stderr_preview"] = self.stderr_output[:500]
        return result
