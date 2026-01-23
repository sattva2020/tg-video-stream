# -*- coding: utf-8 -*-
"""
Custom exceptions for video validation and transcoding services.
Provides consistent error handling with actionable messages.

Example usage:
    from src.exceptions.video import VideoValidationError, VideoTranscodingError

    if codec not in supported_codecs:
        raise VideoValidationError('unsupported_codec', f'codec={codec}')
"""

from typing import Optional


class VideoServiceError(Exception):
    """
    Base exception for video validation and transcoding services.

    All specific video exceptions inherit from this class,
    allowing catch-all video error handling.
    """

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "VIDEO_ERROR"
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.code,
            "message": self.message,
        }


class VideoValidationError(VideoServiceError):
    """
    Video validation error with actionable error messages.

    Provides specific guidance on how to fix validation issues
    (unsupported codecs, formats, container issues, etc.).

    Attributes:
        error_type: Type of validation error (unsupported_codec, invalid_format, etc.)
        context: Additional context about the error (e.g., codec=hevc, format=avi)
        actionable_message: Human-readable message with suggested fix

    Example:
        >>> e = VideoValidationError('unsupported_codec', 'codec=hevc')
        >>> print(e.actionable_message)
        'Transcode to h264 or h265'
    """

    # Error type to actionable message mapping
    ACTIONABLE_MESSAGES = {
        'unsupported_codec': 'Transcode to supported codec (h264, h265 for video; aac, mp3, opus for audio)',
        'invalid_format': 'Convert to supported container format (mp4, mkv, webm)',
        'orientation_missing': 'Video may display incorrectly - consider adding orientation metadata',
        'resolution_exceeded': 'Reduce resolution to 1080p or lower for optimal compatibility',
        'bitrate_too_high': 'Lower bitrate to 4000 Kbps or lower for reliable streaming',
        'file_corrupted': 'Source file is corrupted or incomplete - re-encode from original',
        'duration_too_short': 'Video must be at least 1 second long',
        'duration_too_long': 'Video exceeds maximum duration - split into shorter segments',
        'no_video_stream': 'File contains no video stream - verify source file',
        'no_audio_stream': 'File contains no audio stream - add audio track',
        'unsupported_pixel_format': 'Transcode with pixel format yuv420p for compatibility',
        'container_mismatch': 'Remux to proper container (e.g., MP4 for h264/aac)',
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
            msg = f"Validation error ({error_type}): {context}"
        else:
            msg = f"Validation error: {error_type}"

        # Generate actionable message
        self.actionable_message = self._get_actionable_message()

        super().__init__(msg, code="VIDEO_VALIDATION_ERROR")

    def _get_actionable_message(self) -> str:
        """
        Get actionable message based on error type.

        Returns a human-readable message with specific guidance
        on how to resolve the validation error.
        """
        return self.ACTIONABLE_MESSAGES.get(
            self.error_type,
            'Review video specifications and transcode to Telegram-compatible format'
        )

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["error_type"] = self.error_type
        result["actionable_message"] = self.actionable_message
        if self.context:
            result["context"] = self.context
        return result


class VideoTranscodingError(VideoServiceError):
    """
    Video transcoding error.

    Raised when FFmpeg transcoding fails or encounters issues.

    Attributes:
        operation: The operation that failed (e.g., transcode, remux, orientation_correction)
        reason: Human-readable reason for the failure
        exit_code: FFmpeg exit code (if applicable)
    """

    def __init__(
        self,
        operation: str,
        reason: str,
        exit_code: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.operation = operation
        self.reason = reason
        self.exit_code = exit_code

        if message:
            msg = message
        elif exit_code is not None:
            msg = f"Transcoding error ({operation}): {reason} (exit code: {exit_code})"
        else:
            msg = f"Transcoding error ({operation}): {reason}"

        super().__init__(msg, code="VIDEO_TRANSCODING_ERROR")

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["operation"] = self.operation
        result["reason"] = self.reason
        if self.exit_code is not None:
            result["exit_code"] = self.exit_code
        return result


class VideoFormatError(VideoServiceError):
    """
    Video format or container error.

    Raised when video file format is unsupported or malformed.

    Attributes:
        format: The detected or expected format
        reason: Human-readable reason for the error
    """

    def __init__(
        self,
        format: str,
        reason: str,
        message: Optional[str] = None,
    ):
        self.format = format
        self.reason = reason

        msg = message or f"Format error ({format}): {reason}"
        super().__init__(msg, code="VIDEO_FORMAT_ERROR")

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        result["format"] = self.format
        result["reason"] = self.reason
        return result


class VideoOrientationError(VideoServiceError):
    """
    Video orientation metadata error.

    Raised when video orientation cannot be detected or corrected.

    Attributes:
        orientation: The detected or expected orientation (0, 90, 180, 270)
        reason: Human-readable reason for the error
    """

    def __init__(
        self,
        orientation: Optional[int],
        reason: str,
        message: Optional[str] = None,
    ):
        self.orientation = orientation
        self.reason = reason

        if message:
            msg = message
        elif orientation is not None:
            msg = f"Orientation error ({orientation}°): {reason}"
        else:
            msg = f"Orientation error: {reason}"

        super().__init__(msg, code="VIDEO_ORIENTATION_ERROR")

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        result = super().to_dict()
        if self.orientation is not None:
            result["orientation"] = self.orientation
        result["reason"] = self.reason
        return result


# =============================================================================
# FastAPI Exception Handler
# =============================================================================

def video_exception_handler(request, exc: VideoServiceError):
    """
    FastAPI exception handler for video exceptions.

    Usage:
        from fastapi import FastAPI
        from src.exceptions.video import VideoServiceError, video_exception_handler

        app = FastAPI()
        app.add_exception_handler(VideoServiceError, video_exception_handler)
    """
    from fastapi.responses import JSONResponse

    status_code = 400

    # Determine HTTP status code based on error type
    if isinstance(exc, VideoValidationError):
        status_code = 422  # Unprocessable Entity
    elif isinstance(exc, VideoFormatError):
        status_code = 415  # Unsupported Media Type
    elif isinstance(exc, VideoTranscodingError):
        status_code = 500  # Internal Server Error (transcoding service error)

    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )
