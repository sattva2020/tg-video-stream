"""Unit tests for validator utilities.

Tests validation functions for email, password, file size, timezone,
and URL validation.
"""

import pytest
from pydantic import ValidationError

from src.lib.validators import (
    EmailValidator,
    PasswordValidator,
    FileValidator,
    TimezoneValidator,
    URLValidator,
    ValidatedUserInput,
    ValidatedPasswordInput,
    ValidatedFileInput,
    validate_schedule_name,
    validate_time_actions,
    validate_repeat_days,
    validate_playlist_name,
    validate_playlist_description,
)


class TestEmailValidator:
    """Test email validation functions."""

    def test_validate_email_format_valid(self):
        """Test validation of valid email formats."""
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "test_user@test-domain.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert EmailValidator.validate_email_format(email) is True

    def test_validate_email_format_invalid(self):
        """Test validation of invalid email formats."""
        invalid_emails = [
            "",
            "notanemail",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "user@com",
            "user name@example.com",
            None,
            123,
        ]

        for email in invalid_emails:
            assert EmailValidator.validate_email_format(email) is False

    def test_validate_email_length_limit(self):
        """Test email length validation (RFC 5321 limit)."""
        # Create email longer than 254 characters
        long_local = "a" * 245
        long_email = f"{long_local}@example.com"
        assert len(long_email) > 254
        assert EmailValidator.validate_email_format(long_email) is False

    def test_normalize_email(self):
        """Test email normalization (lowercase and strip)."""
        assert EmailValidator.normalize_email("  Test@Example.COM  ") == "test@example.com"
        assert EmailValidator.normalize_email("USER@DOMAIN.COM") == "user@domain.com"


class TestPasswordValidator:
    """Test password validation functions."""

    def test_validate_password_strength_valid(self):
        """Test validation of strong passwords."""
        strong_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd",
            "C0mplex!Ty123",
            "Very$tr0ngPass2024",
        ]

        for password in strong_passwords:
            result = PasswordValidator.validate_password_strength(password)
            assert result["valid"] is True
            assert result["issues"] == []
            assert result["strength_score"] > 0

    def test_validate_password_strength_too_short(self):
        """Test password validation rejects short passwords."""
        short_passwords = [
            "Short1!",
            "A1!b",
            "Test12!",
        ]

        for password in short_passwords:
            result = PasswordValidator.validate_password_strength(password)
            assert result["valid"] is False
            assert any("at least 12 characters" in issue for issue in result["issues"])

    def test_validate_password_strength_missing_uppercase(self):
        """Test password validation requires uppercase letters."""
        password = "nouppercase123!"
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is False
        assert any("uppercase" in issue for issue in result["issues"])

    def test_validate_password_strength_missing_lowercase(self):
        """Test password validation requires lowercase letters."""
        password = "NOLOWERCASE123!"
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is False
        assert any("lowercase" in issue for issue in result["issues"])

    def test_validate_password_strength_missing_digit(self):
        """Test password validation requires digits."""
        password = "NoDigitsHere!"
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is False
        assert any("digit" in issue for issue in result["issues"])

    def test_validate_password_strength_missing_special(self):
        """Test password validation requires special characters."""
        password = "NoSpecialChar123"
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is False
        assert any("special" in issue for issue in result["issues"])

    def test_validate_password_strength_repeated_chars(self):
        """Test password validation rejects repeated characters."""
        password = "Passsssword123!"
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is False
        assert any("repeated" in issue for issue in result["issues"])

    def test_validate_password_strength_common_passwords(self):
        """Test password validation rejects common passwords."""
        common_passwords = ["Password123!", "1234567890!", "Qwerty123!", "Admin123!", "User123!"]

        for password in common_passwords:
            result = PasswordValidator.validate_password_strength(password)
            assert result["valid"] is False
            assert any("too common" in issue for issue in result["issues"])

    def test_calculate_strength_score(self):
        """Test password strength scoring."""
        # Strong password
        result = PasswordValidator.validate_password_strength("SecurePass123!")
        assert result["strength_score"] > 70

        # Weak password (but passes minimum requirements)
        result = PasswordValidator.validate_password_strength("Abcdefg123!")
        assert result["strength_score"] < 70

    def test_generate_secure_password(self):
        """Test secure password generation."""
        password = PasswordValidator.generate_secure_password()

        # Check length
        assert len(password) >= 12

        # Check contains at least one of each type
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        # Verify it's valid
        result = PasswordValidator.validate_password_strength(password)
        assert result["valid"] is True

    def test_generate_secure_password_custom_length(self):
        """Test password generation with custom length."""
        password = PasswordValidator.generate_secure_password(length=20)
        assert len(password) == 20

        # Minimum length enforced
        password = PasswordValidator.generate_secure_password(length=8)
        assert len(password) >= 12


class TestFileValidator:
    """Test file validation functions."""

    def test_validate_file_size_valid(self):
        """Test validation of valid file sizes."""
        # 1GB file
        result = FileValidator.validate_file_size(1024 * 1024 * 1024)
        assert result["valid"] is True

        # 1MB file
        result = FileValidator.validate_file_size(1024 * 1024)
        assert result["valid"] is True

    def test_validate_file_size_exceeds_limit(self):
        """Test validation rejects files exceeding 2GB limit."""
        size = 2 * 1024 * 1024 * 1024 + 1  # 2GB + 1 byte
        result = FileValidator.validate_file_size(size)
        assert result["valid"] is False
        assert "exceeds maximum allowed size" in result["error"]

    def test_validate_file_size_exactly_2gb(self):
        """Test validation accepts files exactly at 2GB limit."""
        size = 2 * 1024 * 1024 * 1024  # Exactly 2GB
        result = FileValidator.validate_file_size(size)
        assert result["valid"] is True

    def test_validate_video_format_valid_extensions(self):
        """Test validation of valid video file extensions."""
        valid_files = [
            ("video.mp4", "video/mp4"),
            ("video.mkv", None),
            ("video.avi", "video/x-msvideo"),
            ("video.mov", "video/quicktime"),
            ("video.wmv", "video/x-ms-wmv"),
            ("video.flv", "video/x-flv"),
            ("video.webm", "video/webm"),
        ]

        for filename, content_type in valid_files:
            result = FileValidator.validate_video_format(filename, content_type)
            assert result["valid"] is True

    def test_validate_video_format_invalid_extension(self):
        """Test validation rejects invalid file extensions."""
        result = FileValidator.validate_video_format("document.pdf", "application/pdf")
        assert result["valid"] is False
        assert "not allowed" in result["error"]

    def test_validate_video_format_invalid_mimetype(self):
        """Test validation rejects invalid MIME types."""
        result = FileValidator.validate_video_format("video.mp4", "application/pdf")
        assert result["valid"] is False
        assert "not allowed" in result["error"]

    def test_validate_video_format_case_insensitive(self):
        """Test file extension validation is case-insensitive."""
        result = FileValidator.validate_video_format("video.MP4", "video/mp4")
        assert result["valid"] is True

        result = FileValidator.validate_video_format("video.MKV", None)
        assert result["valid"] is True

    def test_get_file_size_mb(self):
        """Test file size conversion to MB."""
        # 1 MB in bytes
        size_mb = FileValidator.get_file_size_mb(1024 * 1024)
        assert size_mb == 1.0

        # 1.5 MB
        size_mb = FileValidator.get_file_size_mb(int(1.5 * 1024 * 1024))
        assert size_mb == 1.5

        # Round to 2 decimal places
        size_mb = FileValidator.get_file_size_mb(1234567)
        assert size_mb == round(1234567 / (1024 * 1024), 2)


class TestTimezoneValidator:
    """Test timezone validation functions."""

    def test_validate_timezone_valid(self):
        """Test validation of valid IANA timezones."""
        valid_timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

        for tz in valid_timezones:
            result = TimezoneValidator.validate_timezone(tz)
            assert result["valid"] is True

    def test_validate_timezone_invalid(self):
        """Test validation rejects invalid timezones."""
        invalid_timezones = [
            "Invalid/Timezone",
            "FOO/BAR",
            "America/NonExistent",
            "",
        ]

        for tz in invalid_timezones:
            result = TimezoneValidator.validate_timezone(tz)
            assert result["valid"] is False
            assert "Invalid timezone" in result["error"]

    def test_get_common_timezones(self):
        """Test retrieval of common timezone list."""
        timezones = TimezoneValidator.get_common_timezones()

        assert isinstance(timezones, list)
        assert len(timezones) > 0
        assert "UTC" in timezones
        assert "America/New_York" in timezones


class TestURLValidator:
    """Test URL validation functions."""

    def test_validate_url_valid(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path",
            "https://example.com/path?query=value",
            "http://localhost:8000",
            "https://192.168.1.1",
        ]

        for url in valid_urls:
            result = URLValidator.validate_url(url)
            assert result["valid"] is True

    def test_validate_url_invalid(self):
        """Test validation rejects invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",
            "//example.com",
            None,
            123,
        ]

        for url in invalid_urls:
            result = URLValidator.validate_url(url)
            assert result["valid"] is False

    def test_validate_youtube_url_valid(self):
        """Test validation of valid YouTube URLs."""
        valid_urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://www.youtube.com/watch?v=abc123XYZ_-", "abc123XYZ_-"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_youtube_url(url)
            assert result["valid"] is True
            assert result["video_id"] == expected_id

    def test_validate_youtube_url_invalid(self):
        """Test validation rejects invalid YouTube URLs."""
        invalid_urls = [
            "https://example.com",
            "https://youtube.com/",
            "https://youtu.be/",
        ]

        for url in invalid_urls:
            result = URLValidator.validate_youtube_url(url)
            assert result["valid"] is False
            assert result["video_id"] is None

    def test_validate_vimeo_url_valid(self):
        """Test validation of valid Vimeo URLs."""
        valid_urls = [
            ("https://vimeo.com/123456789", "123456789"),
            ("https://www.vimeo.com/123456789", "123456789"),
            ("https://vimeo.com/channels/staffpicks/123456789", "123456789"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_vimeo_url(url)
            assert result["valid"] is True
            assert result["video_id"] == expected_id

    def test_validate_vimeo_url_invalid(self):
        """Test validation rejects invalid Vimeo URLs."""
        result = URLValidator.validate_vimeo_url("https://example.com")
        assert result["valid"] is False
        assert result["video_id"] is None

    def test_validate_twitch_url_valid(self):
        """Test validation of valid Twitch URLs."""
        valid_urls = [
            ("https://www.twitch.tv/testchannel", "testchannel"),
            ("https://twitch.tv/testchannel", "testchannel"),
            ("https://www.twitch.tv/videos/123456", "123456"),
            ("https://twitch.tv/videos/123456", "123456"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_twitch_url(url)
            assert result["valid"] is True
            assert result["channel_id"] == expected_id

    def test_validate_twitch_url_invalid(self):
        """Test validation rejects invalid Twitch URLs."""
        result = URLValidator.validate_twitch_url("https://example.com")
        assert result["valid"] is False
        assert result["channel_id"] is None

    def test_validate_dailymotion_url_valid(self):
        """Test validation of valid Dailymotion URLs."""
        valid_urls = [
            ("https://www.dailymotion.com/video/x123abc", "x123abc"),
            ("https://dailymotion.com/video/x123abc", "x123abc"),
            ("https://www.dailymotion.com/embed/x123abc", "x123abc"),
            ("https://dai.ly/x123abc", "x123abc"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_dailymotion_url(url)
            assert result["valid"] is True
            assert result["video_id"] == expected_id

    def test_validate_dailymotion_url_invalid(self):
        """Test validation rejects invalid Dailymotion URLs."""
        result = URLValidator.validate_dailymotion_url("https://example.com")
        assert result["valid"] is False
        assert result["video_id"] is None

    def test_validate_hls_url_valid(self):
        """Test validation of valid HLS URLs."""
        valid_urls = [
            "https://example.com/stream.m3u8",
            "https://cdn.example.com/live/stream.m3u8",
            "https://example.com/stream.m3u8?token=abc123",
        ]

        for url in valid_urls:
            result = URLValidator.validate_hls_url(url)
            assert result["valid"] is True
            assert result["url"] == url

    def test_validate_hls_url_invalid(self):
        """Test validation rejects invalid HLS URLs."""
        invalid_urls = [
            "https://example.com/stream.mp4",
            "https://example.com/",
            "",
            None,
        ]

        for url in invalid_urls:
            result = URLValidator.validate_hls_url(url)
            assert result["valid"] is False

    def test_validate_google_drive_url_valid(self):
        """Test validation of valid Google Drive URLs."""
        valid_urls = [
            ("https://drive.google.com/file/d/abc123XYZ/view", "abc123XYZ"),
            ("https://drive.google.com/open?id=abc123XYZ", "abc123XYZ"),
            ("https://www.drive.google.com/file/d/abc123XYZ", "abc123XYZ"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_google_drive_url(url)
            assert result["valid"] is True
            assert result["file_id"] == expected_id

    def test_validate_google_drive_url_invalid(self):
        """Test validation rejects invalid Google Drive URLs."""
        result = URLValidator.validate_google_drive_url("https://example.com")
        assert result["valid"] is False
        assert result["file_id"] is None

    def test_validate_dropbox_url_valid(self):
        """Test validation of valid Dropbox URLs."""
        valid_urls = [
            ("https://www.dropbox.com/s/abc123/file.mp4", "abc123"),
            ("https://dropbox.com/s/abc123/file.mp4", "abc123"),
            ("https://db.tt/abc123", "abc123"),
        ]

        for url, expected_id in valid_urls:
            result = URLValidator.validate_dropbox_url(url)
            assert result["valid"] is True
            assert result["file_id"] == expected_id

    def test_validate_dropbox_url_invalid(self):
        """Test validation rejects invalid Dropbox URLs."""
        result = URLValidator.validate_dropbox_url("https://example.com")
        assert result["valid"] is False
        assert result["file_id"] is None

    def test_validate_onedrive_url_valid(self):
        """Test validation of valid OneDrive URLs."""
        valid_urls = [
            "https://onedrive.live.com/?id=abc123",
            "https://1drv.ms/u/abc123",
            "https://onedrive.live.com/authkey=abc123",
        ]

        for url in valid_urls:
            result = URLValidator.validate_onedrive_url(url)
            assert result["valid"] is True
            assert result["url"] == url

    def test_validate_onedrive_url_invalid(self):
        """Test validation rejects invalid OneDrive URLs."""
        result = URLValidator.validate_onedrive_url("https://example.com")
        assert result["valid"] is False

    def test_validate_rss_feed_url_valid(self):
        """Test validation of valid RSS feed URLs."""
        valid_urls = [
            "https://example.com/feed.xml",
            "https://example.com/feed.rss",
            "https://example.com/feed.atom",
            "https://example.com/feed",
            "https://example.com/rss",
            "https://example.com/atom",
        ]

        for url in valid_urls:
            result = URLValidator.validate_rss_feed_url(url)
            assert result["valid"] is True
            assert result["url"] == url

    def test_validate_rss_feed_url_invalid(self):
        """Test validation rejects invalid RSS URLs."""
        invalid_urls = [
            "https://example.com/video.mp4",
            "https://example.com/",
            "",
            None,
        ]

        for url in invalid_urls:
            result = URLValidator.validate_rss_feed_url(url)
            assert result["valid"] is False


class TestPydanticModels:
    """Test Pydantic models with validation."""

    def test_validated_user_input_valid(self):
        """Test ValidatedUserInput with valid email."""
        model = ValidatedUserInput(email="test@example.com")
        assert model.email == "test@example.com"

    def test_validated_user_input_normalizes_email(self):
        """Test ValidatedUserInput normalizes email."""
        model = ValidatedUserInput(email="  TEST@EXAMPLE.COM  ")
        assert model.email == "test@example.com"

    def test_validated_user_input_invalid_email(self):
        """Test ValidatedUserInput rejects invalid email."""
        with pytest.raises(ValidationError):
            ValidatedUserInput(email="invalid-email")

    def test_validated_password_input_valid(self):
        """Test ValidatedPasswordInput with strong password."""
        model = ValidatedPasswordInput(password="SecurePass123!")
        assert model.password == "SecurePass123!"

    def test_validated_password_input_weak(self):
        """Test ValidatedPasswordInput rejects weak password."""
        with pytest.raises(ValidationError):
            ValidatedPasswordInput(password="weak")

    def test_validated_file_input_valid(self):
        """Test ValidatedFileInput with valid file."""
        model = ValidatedFileInput(
            filename="video.mp4",
            size_bytes=1024 * 1024,
            content_type="video/mp4"
        )
        assert model.filename == "video.mp4"
        assert model.size_bytes == 1024 * 1024

    def test_validated_file_input_too_large(self):
        """Test ValidatedFileInput rejects oversized file."""
        with pytest.raises(ValidationError):
            ValidatedFileInput(
                filename="video.mp4",
                size_bytes=3 * 1024 * 1024 * 1024,  # 3GB
                content_type="video/mp4"
            )

    def test_validated_file_input_invalid_format(self):
        """Test ValidatedFileInput rejects invalid format."""
        with pytest.raises(ValidationError):
            ValidatedFileInput(
                filename="document.pdf",
                size_bytes=1024,
                content_type="application/pdf"
            )


class TestScheduleValidation:
    """Test schedule validation functions."""

    def test_validate_schedule_name_valid(self):
        """Test validation of valid schedule names."""
        valid_names = [
            "My Schedule",
            "Test-123",
            "schedule_name",
            "Schedule 1",
        ]

        for name in valid_names:
            # Should not raise
            validate_schedule_name(name)

    def test_validate_schedule_name_empty(self):
        """Test validation rejects empty schedule name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_schedule_name("")

    def test_validate_schedule_name_too_long(self):
        """Test validation rejects schedule name exceeding 100 characters."""
        long_name = "a" * 101
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            validate_schedule_name(long_name)

    def test_validate_schedule_name_invalid_chars(self):
        """Test validation rejects invalid characters."""
        invalid_names = ["Test@Schedule", "Schedule#", "Test/Schedule"]

        for name in invalid_names:
            with pytest.raises(ValueError, match="can only contain"):
                validate_schedule_name(name)

    def test_validate_time_actions_valid(self):
        """Test validation of valid time actions."""
        valid_actions = [
            [{"type": "start", "time": "09:00"}],
            [
                {"type": "start", "time": "09:00"},
                {"type": "pause", "time": "12:00"},
                {"type": "resume", "time": "14:00"},
                {"type": "stop", "time": "18:00"}
            ],
        ]

        for actions in valid_actions:
            # Should not raise
            validate_time_actions(actions)

    def test_validate_time_actions_empty(self):
        """Test validation rejects empty time actions."""
        with pytest.raises(ValueError, match="At least one time action"):
            validate_time_actions([])

    def test_validate_time_actions_too_many(self):
        """Test validation rejects more than 10 time actions."""
        actions = [{"type": "start", "time": f"{i:02d}:00"} for i in range(11)]
        with pytest.raises(ValueError, match="Cannot have more than 10"):
            validate_time_actions(actions)

    def test_validate_time_actions_missing_type(self):
        """Test validation rejects action without type."""
        with pytest.raises(ValueError, match="must have 'type' field"):
            validate_time_actions([{"time": "09:00"}])

    def test_validate_time_actions_missing_time(self):
        """Test validation rejects action without time."""
        with pytest.raises(ValueError, match="must have 'time' field"):
            validate_time_actions([{"type": "start"}])

    def test_validate_time_actions_invalid_type(self):
        """Test validation rejects invalid action type."""
        with pytest.raises(ValueError, match="Invalid action type"):
            validate_time_actions([{"type": "invalid", "time": "09:00"}])

    def test_validate_time_actions_invalid_time_format(self):
        """Test validation rejects invalid time format."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_time_actions([{"type": "start", "time": "9:00"}])

        with pytest.raises(ValueError, match="Invalid time format"):
            validate_time_actions([{"type": "start", "time": "25:00"}])

    def test_validate_time_actions_duplicate_times(self):
        """Test validation rejects duplicate times."""
        actions = [
            {"type": "start", "time": "09:00"},
            {"type": "stop", "time": "09:00"},
        ]
        with pytest.raises(ValueError, match="Duplicate time action"):
            validate_time_actions(actions)

    def test_validate_repeat_days_valid(self):
        """Test validation of valid repeat days."""
        valid_days = [
            None,
            [],
            [0, 1, 2],  # Mon, Tue, Wed
            [6],  # Sunday
            list(range(7)),  # All days
        ]

        for days in valid_days:
            # Should not raise
            validate_repeat_days(days)

    def test_validate_repeat_days_invalid_type(self):
        """Test validation rejects non-list repeat days."""
        with pytest.raises(ValueError, match="must be a list"):
            validate_repeat_days("0,1,2")

    def test_validate_repeat_days_too_many(self):
        """Test validation rejects more than 7 days."""
        with pytest.raises(ValueError, match="Cannot repeat on more than 7 days"):
            validate_repeat_days(list(range(8)))

    def test_validate_repeat_days_invalid_day(self):
        """Test validation rejects invalid day numbers."""
        with pytest.raises(ValueError, match="must be between 0 and 6"):
            validate_repeat_days([7])

        with pytest.raises(ValueError, match="must be between 0 and 6"):
            validate_repeat_days([-1])

    def test_validate_repeat_days_duplicate(self):
        """Test validation rejects duplicate days."""
        with pytest.raises(ValueError, match="Duplicate repeat day"):
            validate_repeat_days([0, 0])


class TestPlaylistValidation:
    """Test playlist validation functions."""

    def test_validate_playlist_name_valid(self):
        """Test validation of valid playlist names."""
        valid_names = [
            "My Playlist",
            "Test-123",
            "playlist_name",
            "Playlist 1",
        ]

        for name in valid_names:
            # Should not raise
            validate_playlist_name(name)

    def test_validate_playlist_name_empty(self):
        """Test validation rejects empty playlist name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_playlist_name("")

    def test_validate_playlist_name_too_long(self):
        """Test validation rejects playlist name exceeding 100 characters."""
        long_name = "a" * 101
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            validate_playlist_name(long_name)

    def test_validate_playlist_name_invalid_chars(self):
        """Test validation rejects invalid characters."""
        with pytest.raises(ValueError, match="can only contain"):
            validate_playlist_name("Test@Playlist")

    def test_validate_playlist_description_valid(self):
        """Test validation of valid playlist descriptions."""
        valid_descriptions = [
            "A short description",
            "This is a longer description with more details",
            None,
            "",
        ]

        for desc in valid_descriptions:
            # Should not raise
            validate_playlist_description(desc)

    def test_validate_playlist_description_too_long(self):
        """Test validation rejects description exceeding 500 characters."""
        long_desc = "a" * 501
        with pytest.raises(ValueError, match="cannot exceed 500 characters"):
            validate_playlist_description(long_desc)

    def test_validate_playlist_description_invalid_type(self):
        """Test validation rejects non-string description."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_playlist_description(123)
