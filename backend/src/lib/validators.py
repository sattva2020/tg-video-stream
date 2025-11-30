"""
Request validation utilities for the Telegram broadcast platform.

This module provides validation functions for common input types
such as email, password strength, file size, and timezone validation.
"""

import re
import secrets
import string
from typing import Optional

import pytz
from pydantic import BaseModel, EmailStr, validator


class EmailValidator:
    """Email validation utilities."""

    # RFC 5322 compliant email regex (simplified but comprehensive)
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        Validate email format using RFC 5322 compliant regex.

        Args:
            email: Email address to validate

        Returns:
            bool: True if email format is valid
        """
        if not email or not isinstance(email, str):
            return False

        # Check length constraints
        if len(email) > 254:  # RFC 5321 limit
            return False

        # Check basic format
        return bool(EmailValidator.EMAIL_REGEX.match(email))

    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize email address (lowercase, strip whitespace).

        Args:
            email: Email address to normalize

        Returns:
            str: Normalized email address
        """
        return email.strip().lower()


class PasswordValidator:
    """Password strength validation utilities."""

    @staticmethod
    def validate_password_strength(password: str) -> dict:
        """
        Validate password strength and return detailed feedback.

        Args:
            password: Password to validate

        Returns:
            dict: Validation result with 'valid' bool and 'issues' list
        """
        issues = []

        # Minimum length check
        if len(password) < 12:
            issues.append("Password must be at least 12 characters long")

        # Character variety checks
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password))

        if not has_upper:
            issues.append("Password must contain at least one uppercase letter")
        if not has_lower:
            issues.append("Password must contain at least one lowercase letter")
        if not has_digit:
            issues.append("Password must contain at least one digit")
        if not has_special:
            issues.append("Password must contain at least one special character")

        # Check for common weak patterns
        if re.search(r'(.)\1{2,}', password):  # Repeated characters
            issues.append("Password should not contain repeated characters")
        if password.lower() in ['password', '123456', 'qwerty', 'admin', 'user']:
            issues.append("Password is too common")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength_score": PasswordValidator._calculate_strength_score(password)
        }

    @staticmethod
    def _calculate_strength_score(password: str) -> int:
        """
        Calculate a password strength score (0-100).

        Args:
            password: Password to score

        Returns:
            int: Strength score from 0 (weak) to 100 (strong)
        """
        score = 0

        # Length bonus
        length = len(password)
        if length >= 12:
            score += min(25, (length - 8) * 2)

        # Character variety bonuses
        if re.search(r'[A-Z]', password):
            score += 15
        if re.search(r'[a-z]', password):
            score += 15
        if re.search(r'\d', password):
            score += 15
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            score += 15

        # Complexity bonuses
        if re.search(r'.{3,}', password):  # Has sequences of 3+ chars
            score += 5
        if not re.search(r'(.)\1{2,}', password):  # No repeated chars
            score += 5
        if not password.lower() in ['password', '123456', 'qwerty', 'admin', 'user']:
            score += 5

        return min(100, score)

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """
        Generate a secure random password.

        Args:
            length: Desired password length (minimum 12)

        Returns:
            str: Secure random password
        """
        length = max(12, length)

        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Ensure at least one of each type
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)


class FileValidator:
    """File validation utilities."""

    # Maximum file size: 2GB
    MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB

    # Allowed video formats
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    ALLOWED_VIDEO_MIMETYPES = {
        'video/mp4',
        'video/x-msvideo',  # .avi
        'video/quicktime',  # .mov
        'video/x-ms-wmv',   # .wmv
        'video/x-flv',      # .flv
        'video/webm'
    }

    @staticmethod
    def validate_file_size(size_bytes: int) -> dict:
        """
        Validate file size against platform limits.

        Args:
            size_bytes: File size in bytes

        Returns:
            dict: Validation result with 'valid' bool and error message
        """
        if size_bytes > FileValidator.MAX_FILE_SIZE_BYTES:
            return {
                "valid": False,
                "error": f"File size {size_bytes} bytes exceeds maximum allowed size of {FileValidator.MAX_FILE_SIZE_BYTES} bytes (2GB)"
            }

        return {"valid": True}

    @staticmethod
    def validate_video_format(filename: str, content_type: Optional[str] = None) -> dict:
        """
        Validate video file format.

        Args:
            filename: Original filename
            content_type: MIME content type (optional)

        Returns:
            dict: Validation result with 'valid' bool and error message
        """
        import os

        # Check file extension
        _, ext = os.path.splitext(filename.lower())

        if ext not in FileValidator.ALLOWED_VIDEO_EXTENSIONS:
            return {
                "valid": False,
                "error": f"File extension '{ext}' not allowed. Allowed extensions: {', '.join(FileValidator.ALLOWED_VIDEO_EXTENSIONS)}"
            }

        # Check MIME type if provided
        if content_type and content_type not in FileValidator.ALLOWED_VIDEO_MIMETYPES:
            return {
                "valid": False,
                "error": f"Content type '{content_type}' not allowed. Allowed types: {', '.join(FileValidator.ALLOWED_VIDEO_MIMETYPES)}"
            }

        return {"valid": True}

    @staticmethod
    def get_file_size_mb(size_bytes: int) -> float:
        """
        Convert file size from bytes to megabytes.

        Args:
            size_bytes: File size in bytes

        Returns:
            float: File size in MB, rounded to 2 decimal places
        """
        return round(size_bytes / (1024 * 1024), 2)


class TimezoneValidator:
    """Timezone validation utilities."""

    @staticmethod
    def validate_timezone(timezone_str: str) -> dict:
        """
        Validate timezone string against IANA timezone database.

        Args:
            timezone_str: Timezone string to validate

        Returns:
            dict: Validation result with 'valid' bool and error message
        """
        try:
            pytz.timezone(timezone_str)
            return {"valid": True}
        except pytz.exceptions.UnknownTimeZoneError:
            return {
                "valid": False,
                "error": f"Invalid timezone '{timezone_str}'. Must be a valid IANA timezone identifier."
            }

    @staticmethod
    def get_common_timezones() -> list[str]:
        """
        Get a list of commonly used timezone identifiers.

        Returns:
            list[str]: List of common IANA timezone identifiers
        """
        return [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Europe/Moscow",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
            "Pacific/Auckland"
        ]


class URLValidator:
    """URL validation utilities."""

    URL_REGEX = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE  # path
    )

    YOUTUBE_URL_REGEX = re.compile(
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        re.IGNORECASE
    )

    @staticmethod
    def validate_url(url: str) -> dict:
        """
        Validate URL format.

        Args:
            url: URL string to validate

        Returns:
            dict: Validation result with 'valid' bool and error message
        """
        if not url or not isinstance(url, str):
            return {"valid": False, "error": "URL cannot be empty"}

        if not URLValidator.URL_REGEX.match(url):
            return {"valid": False, "error": "Invalid URL format"}

        return {"valid": True}

    @staticmethod
    def validate_youtube_url(url: str) -> dict:
        """
        Validate YouTube URL and extract video ID.

        Args:
            url: YouTube URL to validate

        Returns:
            dict: Validation result with 'valid' bool, 'video_id', and error message
        """
        match = URLValidator.YOUTUBE_URL_REGEX.search(url)
        if not match:
            return {
                "valid": False,
                "error": "Invalid YouTube URL format",
                "video_id": None
            }

        video_id = match.group(1)
        return {
            "valid": True,
            "video_id": video_id
        }


# Pydantic models with built-in validation
class ValidatedUserInput(BaseModel):
    """Base model for validated user input."""
    email: EmailStr

    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        result = EmailValidator.validate_email_format(v)
        if not result:
            raise ValueError('Invalid email format')
        return EmailValidator.normalize_email(v)


class ValidatedPasswordInput(BaseModel):
    """Model for password input with validation."""
    password: str

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        result = PasswordValidator.validate_password_strength(v)
        if not result['valid']:
            raise ValueError(f"Password validation failed: {', '.join(result['issues'])}")
        return v


class ValidatedFileInput(BaseModel):
    """Model for file input validation."""
    filename: str
    size_bytes: int
    content_type: Optional[str] = None

    @validator('size_bytes')
    def validate_file_size(cls, v):
        """Validate file size."""
        result = FileValidator.validate_file_size(v)
        if not result['valid']:
            raise ValueError(result['error'])
        return v

    @validator('filename')
    def validate_filename(cls, v, values):
        """Validate filename and format."""
        content_type = values.get('content_type')
        result = FileValidator.validate_video_format(v, content_type)
        if not result['valid']:
            raise ValueError(result['error'])
        return v


# Schedule validation functions
def validate_schedule_name(name: str) -> None:
    """
    Validate schedule name.

    Args:
        name: Schedule name to validate

    Raises:
        ValueError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Schedule name is required")

    name = name.strip()
    if len(name) < 1:
        raise ValueError("Schedule name cannot be empty")
    if len(name) > 100:
        raise ValueError("Schedule name cannot exceed 100 characters")

    # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValueError("Schedule name can only contain letters, numbers, spaces, hyphens, and underscores")


def validate_time_actions(time_actions: list) -> None:
    """
    Validate time actions list.

    Args:
        time_actions: List of time action dictionaries

    Raises:
        ValueError: If time actions are invalid
    """
    if not time_actions or not isinstance(time_actions, list):
        raise ValueError("At least one time action is required")

    if len(time_actions) < 1:
        raise ValueError("At least one time action is required")

    if len(time_actions) > 10:  # Reasonable limit
        raise ValueError("Cannot have more than 10 time actions")

    seen_times = set()
    for action in time_actions:
        if not isinstance(action, dict):
            raise ValueError("Each time action must be a dictionary")

        # Validate required fields
        if 'type' not in action:
            raise ValueError("Time action must have 'type' field")
        if 'time' not in action:
            raise ValueError("Time action must have 'time' field")

        action_type = action['type']
        action_time = action['time']

        # Validate action type
        if action_type not in ['start', 'pause', 'resume', 'stop']:
            raise ValueError(f"Invalid action type: {action_type}. Must be one of: start, pause, resume, stop")

        # Validate time format (HH:MM)
        if not isinstance(action_time, str):
            raise ValueError("Time must be a string in HH:MM format")

        time_match = re.match(r'^([01][0-9]|2[0-3]):[0-5][0-9]$', action_time)
        if not time_match:
            raise ValueError(f"Invalid time format: {action_time}. Must be HH:MM (24-hour format)")

        # Check for duplicate times
        if action_time in seen_times:
            raise ValueError(f"Duplicate time action: {action_time}")
        seen_times.add(action_time)


def validate_repeat_days(repeat_days: list) -> None:
    """
    Validate repeat days list.

    Args:
        repeat_days: List of day numbers (0=Monday, 6=Sunday)

    Raises:
        ValueError: If repeat days are invalid
    """
    if repeat_days is None:
        return  # None is allowed (no repeat)

    if not isinstance(repeat_days, list):
        raise ValueError("Repeat days must be a list")

    if len(repeat_days) == 0:
        return  # Empty list is allowed (no repeat)

    if len(repeat_days) > 7:
        raise ValueError("Cannot repeat on more than 7 days")

    seen_days = set()
    for day in repeat_days:
        if not isinstance(day, int):
            raise ValueError("Each repeat day must be an integer")

        if day < 0 or day > 6:
            raise ValueError("Repeat day must be between 0 (Monday) and 6 (Sunday)")

        if day in seen_days:
            raise ValueError(f"Duplicate repeat day: {day}")
        seen_days.add(day)


# Playlist validation functions
def validate_playlist_name(name: str) -> None:
    """
    Validate playlist name.

    Args:
        name: Playlist name to validate

    Raises:
        ValueError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Playlist name is required")

    name = name.strip()
    if len(name) < 1:
        raise ValueError("Playlist name cannot be empty")
    if len(name) > 100:
        raise ValueError("Playlist name cannot exceed 100 characters")

    # Allow letters, numbers, spaces, hyphens and underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValueError("Playlist name can only contain letters, numbers, spaces, hyphens, and underscores")


def validate_playlist_description(description: Optional[str]) -> None:
    """
    Validate playlist description length and type.

    Args:
        description: Playlist description

    Raises:
        ValueError: If description is invalid
    """
    if description is None:
        return

    if not isinstance(description, str):
        raise ValueError("Playlist description must be a string")

    if len(description) > 500:
        raise ValueError("Playlist description cannot exceed 500 characters")