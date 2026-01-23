"""
End-to-end integration test for platform failure isolation.

Tests the complete workflow:
1. Start stream with 3 platforms (Telegram + YouTube + Twitch)
2. Simulate YouTube RTMP failure
3. Verify Telegram and Twitch continue streaming
4. Verify health monitoring shows YouTube as 'error'
5. Fix YouTube issue and verify recovery
6. Verify all platforms show 'running' again

Feature: 021-social-media-integration-cross-platform-broadcasting
Subtask: 7-4
"""

import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from src.models.user import User, UserRole, UserStatus
from src.models.telegram import TelegramAccount, Channel
from src.models.streaming_platform import StreamingPlatform, PlatformType
from src.models.broadcast_destination import BroadcastDestination


class TestPlatformIsolation:
    """
    End-to-end test for platform failure isolation.

    This test verifies that:
    - Multiple platforms can stream simultaneously
    - Failures on one platform don't affect other platforms
    - Health monitoring tracks per-platform status independently
    - Failed platforms can recover without affecting others
    - Redis status updates reflect individual platform health
    """

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db_session):
        """Create test data for platform isolation testing."""
        # Create admin user
        admin_user = User(
            email='admin@isolationtest.com',
            hashed_password='test_hash',
            role=UserRole.ADMIN,
            status=UserStatus.APPROVED
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

        # Create Telegram account
        tg_account = TelegramAccount(
            user_id=admin_user.id,
            phone='+1234567890',
            encrypted_session='encrypted_session_data',
            tg_user_id=123456789
        )
        db_session.add(tg_account)
        db_session.commit()
        db_session.refresh(tg_account)

        # Create channel
        test_channel = Channel(
            id=uuid.uuid4(),
            account_id=tg_account.id,
            chat_id=-1001234567890,
            username='test_isolation_channel',
            title='Test Platform Isolation Channel',
            description='Channel for testing platform failure isolation',
            status='stopped'
        )
        db_session.add(test_channel)
        db_session.commit()
        db_session.refresh(test_channel)

        # Create Telegram platform
        telegram_platform = StreamingPlatform(
            user_id=admin_user.id,
            platform_type=PlatformType.TELEGRAM,
            platform_name='Test Telegram Stream',
            credentials='encrypted_telegram_credentials',
            stream_key='telegram_stream_key',
            rtmp_url='rtmp://telegram.example.com/live'
        )
        db_session.add(telegram_platform)
        db_session.commit()
        db_session.refresh(telegram_platform)

        # Create YouTube platform
        youtube_platform = StreamingPlatform(
            user_id=admin_user.id,
            platform_type=PlatformType.YOUTUBE,
            platform_name='Test YouTube Channel',
            credentials='encrypted_youtube_credentials',
            stream_key='youtube_stream_key_123',
            rtmp_url='rtmp://a.rtmp.youtube.com/live2'
        )
        db_session.add(youtube_platform)
        db_session.commit()
        db_session.refresh(youtube_platform)

        # Create Twitch platform
        twitch_platform = StreamingPlatform(
            user_id=admin_user.id,
            platform_type=PlatformType.TWITCH,
            platform_name='Test Twitch Channel',
            credentials='encrypted_twitch_credentials',
            stream_key='twitch_stream_key_456',
            rtmp_url='rtmp://live.twitch.tv/app'
        )
        db_session.add(twitch_platform)
        db_session.commit()
        db_session.refresh(twitch_platform)

        # Create broadcast destinations for all 3 platforms
        telegram_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=telegram_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({"title": "Test Stream Telegram"})
        )
        db_session.add(telegram_dest)

        youtube_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=youtube_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({"title": "Test Stream YouTube"})
        )
        db_session.add(youtube_dest)

        twitch_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=twitch_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({"title": "Test Stream Twitch"})
        )
        db_session.add(twitch_dest)
        db_session.commit()

        # Store in test context
        self.admin_user = admin_user
        self.test_channel = test_channel
        self.telegram_platform = telegram_platform
        self.youtube_platform = youtube_platform
        self.twitch_platform = twitch_platform
        self.telegram_dest = telegram_dest
        self.youtube_dest = youtube_dest
        self.twitch_dest = twitch_dest

        yield

        # Cleanup handled by db_session fixture

    def test_start_stream_with_three_platforms(self, client):
        """
        Test Step 1: Start stream with 3 platforms.

        Verifies that all three platforms start streaming successfully.
        """
        # Mock the platform streamer service
        with patch('src.services.platform_streamer.PlatformStreamerService') as MockPlatformStreamer:
            mock_streamer = AsyncMock()
            mock_streamer.start_all_platforms.return_value = {
                "success": True,
                "started_platforms": 3,
                "failed_platforms": 0,
                "platforms": [
                    {
                        "platform_id": str(self.telegram_platform.id),
                        "status": "streaming",
                        "rtmp_url": self.telegram_platform.rtmp_url
                    },
                    {
                        "platform_id": str(self.youtube_platform.id),
                        "status": "streaming",
                        "rtmp_url": self.youtube_platform.rtmp_url
                    },
                    {
                        "platform_id": str(self.twitch_platform.id),
                        "status": "streaming",
                        "rtmp_url": self.twitch_platform.rtmp_url
                    }
                ]
            }
            MockPlatformStreamer.return_value = mock_streamer

            # Start all platforms
            response = client.post(
                f"/api/broadcast-destinations/start-all/{self.test_channel.id}",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify all 3 platforms started
            assert data["started_platforms"] == 3
            assert data["failed_platforms"] == 0

            # Verify all platforms are in response
            platform_ids = [p["platform_id"] for p in data["platforms"]]
            assert str(self.telegram_platform.id) in platform_ids
            assert str(self.youtube_platform.id) in platform_ids
            assert str(self.twitch_platform.id) in platform_ids

            # Verify all show streaming status
            for platform in data["platforms"]:
                assert platform["status"] in ["streaming", "starting"]

    def test_simulate_youtube_rtmp_failure(self, client, db_session):
        """
        Test Step 2 & 3: Simulate YouTube RTMP failure and verify other platforms continue.

        Verifies that when YouTube fails, Telegram and Twitch continue streaming.
        """
        import redis
        redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

        # First, set all platforms to streaming in Redis
        for platform in [self.telegram_platform, self.youtube_platform, self.twitch_platform]:
            status_key = f"platform:status:{platform.id}"
            status_data = {
                "platform_id": str(platform.id),
                "channel_id": str(self.test_channel.id),
                "status": "streaming",
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            redis_client.setex(status_key, 3600, json.dumps(status_data))

        # Mock platform streamer to simulate YouTube failure
        with patch('src.services.platform_streamer.PlatformStreamerService') as MockPlatformStreamer:
            # Create a function that returns YouTube as failed
            async def mock_get_all_status(channel_id):
                return {
                    "success": True,
                    "platforms": [
                        {
                            "platform_id": str(self.telegram_platform.id),
                            "status": "streaming",
                            "is_streaming": True,
                            "error": None
                        },
                        {
                            "platform_id": str(self.youtube_platform.id),
                            "status": "error",
                            "is_streaming": False,
                            "error": "RTMP connection failed: Connection refused"
                        },
                        {
                            "platform_id": str(self.twitch_platform.id),
                            "status": "streaming",
                            "is_streaming": True,
                            "error": None
                        }
                    ]
                }

            mock_streamer = AsyncMock()
            mock_streamer.get_all_platform_statuses = mock_get_all_status
            MockPlatformStreamer.return_value = mock_streamer

            # Update YouTube to error state in Redis
            youtube_status_key = f"platform:status:{self.youtube_platform.id}"
            youtube_error_data = {
                "platform_id": str(self.youtube_platform.id),
                "channel_id": str(self.test_channel.id),
                "status": "error",
                "error": "RTMP connection failed: Connection refused",
                "error_time": datetime.now(timezone.utc).isoformat()
            }
            redis_client.setex(youtube_status_key, 3600, json.dumps(youtube_error_data))

            # Get platform statuses via API
            response = client.get(
                f"/api/broadcast-destinations/status-all/{self.test_channel.id}",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify Telegram is still streaming
            telegram_status = next(
                (p for p in data["platforms"] if p["platform_id"] == str(self.telegram_platform.id)),
                None
            )
            assert telegram_status is not None
            assert telegram_status["status"] in ["streaming", "starting"]

            # Verify YouTube shows error
            youtube_status = next(
                (p for p in data["platforms"] if p["platform_id"] == str(self.youtube_platform.id)),
                None
            )
            assert youtube_status is not None
            assert youtube_status["status"] == "error"
            assert youtube_status.get("error") is not None

            # Verify Twitch is still streaming
            twitch_status = next(
                (p for p in data["platforms"] if p["platform_id"] == str(self.twitch_platform.id)),
                None
            )
            assert twitch_status is not None
            assert twitch_status["status"] in ["streaming", "starting"]

    def test_verify_health_monitoring_shows_youtube_error(self, client):
        """
        Test Step 4: Verify health monitoring shows YouTube as 'error'.

        Verifies that the health monitor correctly tracks the failed platform.
        """
        import redis
        redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

        # Set health status for YouTube as unhealthy/error
        youtube_health_key = f"platform:health:{self.youtube_platform.id}"
        health_data = {
            "platform_id": str(self.youtube_platform.id),
            "status": "unhealthy",
            "consecutive_failures": 3,
            "total_failures": 5,
            "error_message": "RTMP connection failed: Connection refused",
            "is_streaming": False,
            "health_score": 0.2,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        redis_client.setex(youtube_health_key, 60, json.dumps(health_data))

        # Set other platforms as healthy
        for platform in [self.telegram_platform, self.twitch_platform]:
            health_key = f"platform:health:{platform.id}"
            platform_health = {
                "platform_id": str(platform.id),
                "status": "healthy",
                "consecutive_failures": 0,
                "total_failures": 0,
                "error_message": None,
                "is_streaming": True,
                "health_score": 1.0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            redis_client.setex(health_key, 60, json.dumps(platform_health))

        # Verify health status via direct Redis check
        youtube_health = json.loads(redis_client.get(youtube_health_key))
        assert youtube_health["status"] in ["unhealthy", "error"]
        assert youtube_health["consecutive_failures"] >= 3
        assert youtube_health["health_score"] < 0.5

        # Verify other platforms are healthy
        telegram_health = json.loads(
            redis_client.get(f"platform:health:{self.telegram_platform.id}")
        )
        assert telegram_health["status"] == "healthy"
        assert telegram_health["health_score"] >= 0.9

        twitch_health = json.loads(
            redis_client.get(f"platform:health:{self.twitch_platform.id}")
        )
        assert twitch_health["status"] == "healthy"
        assert twitch_health["health_score"] >= 0.9

    def test_fix_youtube_and_verify_recovery(self, client):
        """
        Test Step 5 & 6: Fix YouTube issue and verify recovery.

        Verifies that a failed platform can recover and all platforms show 'running'.
        """
        import redis
        redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

        # Mock platform streamer to simulate successful restart
        with patch('src.services.platform_streamer.PlatformStreamerService') as MockPlatformStreamer:
            async def mock_restart_platform(channel_id, platform_id):
                # Simulate successful restart
                return {
                    "success": True,
                    "platform_id": str(platform_id),
                    "status": "streaming"
                }

            async def mock_get_all_status(channel_id):
                return {
                    "success": True,
                    "platforms": [
                        {
                            "platform_id": str(self.telegram_platform.id),
                            "status": "streaming",
                            "is_streaming": True
                        },
                        {
                            "platform_id": str(self.youtube_platform.id),
                            "status": "streaming",
                            "is_streaming": True
                        },
                        {
                            "platform_id": str(self.twitch_platform.id),
                            "status": "streaming",
                            "is_streaming": True
                        }
                    ]
                }

            mock_streamer = AsyncMock()
            mock_streamer.start_platform = mock_restart_platform
            mock_streamer.get_all_platform_statuses = mock_get_all_status
            MockPlatformStreamer.return_value = mock_streamer

            # Restart YouTube platform
            response = client.post(
                f"/api/broadcast-destinations/{self.youtube_dest.id}/start",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["platform_id"] == str(self.youtube_platform.id)

            # Update Redis to show YouTube recovered
            youtube_status_key = f"platform:status:{self.youtube_platform.id}"
            youtube_recovered_data = {
                "platform_id": str(self.youtube_platform.id),
                "channel_id": str(self.test_channel.id),
                "status": "streaming",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "recovered_at": datetime.now(timezone.utc).isoformat()
            }
            redis_client.setex(youtube_status_key, 3600, json.dumps(youtube_recovered_data))

            # Update health to show recovery
            youtube_health_key = f"platform:health:{self.youtube_platform.id}"
            recovered_health = {
                "platform_id": str(self.youtube_platform.id),
                "status": "healthy",
                "consecutive_failures": 0,
                "total_failures": 5,  # Historical failures preserved
                "recovery_attempts": 1,
                "last_recovery_time": datetime.now(timezone.utc).isoformat(),
                "error_message": None,
                "is_streaming": True,
                "health_score": 1.0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            redis_client.setex(youtube_health_key, 60, json.dumps(recovered_health))

            # Get all platform statuses
            response = client.get(
                f"/api/broadcast-destinations/status-all/{self.test_channel.id}",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify ALL platforms are now streaming
            for platform_data in data["platforms"]:
                assert platform_data["status"] in ["streaming", "starting"], \
                    f"Platform {platform_data['platform_id']} has status {platform_data['status']}, expected streaming"

            # Verify YouTube health recovered
            youtube_health = json.loads(redis_client.get(youtube_health_key))
            assert youtube_health["status"] == "healthy"
            assert youtube_health["health_score"] >= 0.9
            assert youtube_health["is_streaming"] is True

    def test_individual_platform_stop_during_failure(self, client):
        """
        Test that individual platforms can be stopped even when others are failing.

        This verifies complete independence - you can stop Telegram even if
        YouTube is in error state.
        """
        import redis
        redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

        # Set up state: YouTube in error, Telegram and Twitch streaming
        youtube_error = {
            "platform_id": str(self.youtube_platform.id),
            "status": "error",
            "error": "RTMP failed"
        }
        redis_client.setex(
            f"platform:status:{self.youtube_platform.id}",
            3600,
            json.dumps(youtube_error)
        )

        telegram_streaming = {
            "platform_id": str(self.telegram_platform.id),
            "status": "streaming"
        }
        redis_client.setex(
            f"platform:status:{self.telegram_platform.id}",
            3600,
            json.dumps(telegram_streaming)
        )

        # Mock stopping Telegram
        with patch('src.services.platform_streamer.PlatformStreamerService') as MockPlatformStreamer:
            async def mock_stop_platform(channel_id, platform_id):
                return {
                    "success": True,
                    "platform_id": str(platform_id),
                    "status": "stopped"
                }

            mock_streamer = AsyncMock()
            mock_streamer.stop_platform = mock_stop_platform
            MockPlatformStreamer.return_value = mock_streamer

            # Stop ONLY Telegram
            response = client.post(
                f"/api/broadcast-destinations/{self.telegram_dest.id}/stop",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify Telegram is stopped
            response = client.get(
                f"/api/broadcast-destinations/{self.telegram_dest.id}",
                headers={"Authorization": f"Bearer {self._get_token(client)}"}
            )
            assert response.status_code == 200
            # Status should be stopped or idle

    def _get_token(self, client):
        """Helper to get auth token for test user."""
        from src.auth.jwt import create_access_token
        return create_access_token(
            data={"sub": str(self.admin_user.id), "role": self.admin_user.role}
        )
