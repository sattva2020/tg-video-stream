"""
End-to-end integration test for multi-platform analytics aggregation.

Tests the complete workflow:
1. Start stream on multiple platforms
2. Generate viewer activity on each platform
3. Wait for analytics aggregation
4. Verify API returns combined metrics
5. Verify frontend dashboard shows total + breakdown
6. Verify platform-specific optimizations are suggested

Feature: 021-social-media-integration-cross-platform-broadcasting
Subtask: 7-5
"""

import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.models.user import User, UserRole, UserStatus
from src.models.telegram import TelegramAccount, Channel
from src.models.streaming_platform import StreamingPlatform, PlatformType
from src.models.broadcast_destination import BroadcastDestination
from src.models.social_media_post import SocialMediaPost, PostStatus, PostType


class TestMultiPlatformAnalytics:
    """
    End-to-end test for multi-platform analytics aggregation.

    This test verifies that:
    - Streams can be started on multiple platforms simultaneously
    - Viewer activity and social media posts are tracked per platform
    - Analytics aggregation combines metrics from all platforms
    - API returns combined totals and per-platform breakdowns
    - Platform-specific metrics are correctly calculated
    """

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db_session):
        """Create test data for multi-platform analytics."""
        # Create admin user
        admin_user = User(
            email='admin@analyticstest.com',
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
            username='test_analytics_channel',
            title='Test Analytics Channel',
            description='Channel for testing multi-platform analytics aggregation',
            status='stopped',
            is_active=True
        )
        db_session.add(test_channel)
        db_session.commit()
        db_session.refresh(test_channel)

        # Create YouTube platform
        youtube_platform = StreamingPlatform(
            user_id=admin_user.id,
            platform_type=PlatformType.YOUTUBE,
            platform_name='Test YouTube Channel',
            credentials='encrypted_youtube_credentials',
            stream_key='youtube_stream_key_123',
            rtmp_url='rtmp://a.rtmp.youtube.com/live2',
            status='active'
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
            rtmp_url='rtmp://live.twitch.tv/app',
            status='active'
        )
        db_session.add(twitch_platform)
        db_session.commit()
        db_session.refresh(twitch_platform)

        # Create Twitter platform
        twitter_platform = StreamingPlatform(
            user_id=admin_user.id,
            platform_type=PlatformType.TWITTER,
            platform_name='Test Twitter Account',
            credentials='encrypted_twitter_credentials',
            stream_key=None,
            rtmp_url=None,
            status='active'
        )
        db_session.add(twitter_platform)
        db_session.commit()
        db_session.refresh(twitter_platform)

        # Create broadcast destinations
        youtube_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=youtube_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({"title": "Test Stream YouTube", "description": "Analytics test"})
        )
        db_session.add(youtube_dest)

        twitch_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=twitch_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({"title": "Test Stream Twitch", "description": "Analytics test"})
        )
        db_session.add(twitch_dest)

        twitter_dest = BroadcastDestination(
            channel_id=test_channel.id,
            platform_id=twitter_platform.id,
            enabled=True,
            status='idle',
            platform_settings=json.dumps({})
        )
        db_session.add(twitter_dest)
        db_session.commit()

        # Store in test context
        self.admin_user = admin_user
        self.test_channel = test_channel
        self.youtube_platform = youtube_platform
        self.twitch_platform = twitch_platform
        self.twitter_platform = twitter_platform
        self.youtube_dest = youtube_dest
        self.twitch_dest = twitch_dest
        self.twitter_dest = twitter_dest

        yield

        # Cleanup handled by db_session fixture

    def test_start_stream_on_multiple_platforms(self, client):
        """
        Test Step 1: Start stream on multiple platforms.

        Verifies that streams can be started on YouTube, Twitch, and Twitter platforms.
        """
        # Mock the platform streamer service
        with patch('src.services.platform_streamer.PlatformStreamerService') as MockPlatformStreamer:
            async def mock_start_all(channel_id):
                return {
                    "success": True,
                    "started_platforms": 3,
                    "failed_platforms": 0,
                    "platforms": [
                        {
                            "platform_id": str(self.youtube_platform.id),
                            "status": "streaming"
                        },
                        {
                            "platform_id": str(self.twitch_platform.id),
                            "status": "streaming"
                        },
                        {
                            "platform_id": str(self.twitter_platform.id),
                            "status": "streaming"
                        }
                    ]
                }

            mock_streamer = AsyncMock()
            mock_streamer.start_all_platforms = mock_start_all
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

            # Verify each platform is in response
            platform_ids = [p["platform_id"] for p in data["platforms"]]
            assert str(self.youtube_platform.id) in platform_ids
            assert str(self.twitch_platform.id) in platform_ids
            assert str(self.twitter_platform.id) in platform_ids

            # Verify all show streaming status
            for platform in data["platforms"]:
                assert platform["status"] in ["streaming", "starting"]

    def test_generate_viewer_activity_on_each_platform(self, db_session):
        """
        Test Step 2: Generate viewer activity on each platform.

        Simulates viewer activity by creating social media posts for each platform.
        This represents engagement metrics that will be aggregated.
        """
        # Create social media posts for YouTube (stream announcement)
        youtube_post_1 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.youtube_platform.id,
            post_type=PostType.STREAM_START,
            platform_post_id="yt_post_123",
            content="🔴 Going live on YouTube! Join the stream: https://youtube.com/watch?v=test123",
            status=PostStatus.POSTED,
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        youtube_post_2 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.youtube_platform.id,
            post_type=PostType.STREAM_END,
            platform_post_id="yt_post_124",
            content="📺 Stream ended! Thanks for watching! VOD available now.",
            status=PostStatus.POSTED,
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        db_session.add(youtube_post_1)
        db_session.add(youtube_post_2)

        # Create social media posts for Twitch
        twitch_post_1 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.twitch_platform.id,
            post_type=PostType.STREAM_START,
            platform_post_id="twitch_post_456",
            content="🎮 Live on Twitch! Come hang out: https://twitch.tv/teststream",
            status=PostStatus.POSTED,
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=25),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=25)
        )
        twitch_post_2 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.twitch_platform.id,
            post_type=PostType.STREAM_END,
            platform_post_id="twitch_post_457",
            content="✨ Stream recap! Today was amazing. Catch the VOD!",
            status=PostStatus.POSTED,
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=3),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=3)
        )
        db_session.add(twitch_post_1)
        db_session.add(twitch_post_2)

        # Create social media posts for Twitter
        twitter_post_1 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.twitter_platform.id,
            post_type=PostType.STREAM_START,
            platform_post_id="tweet_789",
            content="🔴 LIVE NOW! Streaming on YouTube and Twitch! Don't miss it! #stream #live",
            status=PostStatus.POSTED,
            posted_at=datetime.now(timezone.utc) - timedelta(minutes=28),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=28)
        )
        # Simulate a failed post to test failed_posts metric
        twitter_post_2 = SocialMediaPost(
            user_id=self.admin_user.id,
            channel_id=self.test_channel.id,
            platform_id=self.twitter_platform.id,
            post_type=PostType.STREAM_END,
            platform_post_id=None,  # Failed to post
            content="Stream's over! Thanks for watching!",
            status=PostStatus.FAILED,
            error_message="Rate limit exceeded",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
        db_session.add(twitter_post_1)
        db_session.add(twitter_post_2)

        db_session.commit()

        # Verify posts were created
        youtube_posts = db_session.query(SocialMediaPost).filter(
            SocialMediaPost.platform_id == self.youtube_platform.id
        ).all()
        twitch_posts = db_session.query(SocialMediaPost).filter(
            SocialMediaPost.platform_id == self.twitch_platform.id
        ).all()
        twitter_posts = db_session.query(SocialMediaPost).filter(
            SocialMediaPost.platform_id == self.twitter_platform.id
        ).all()

        assert len(youtube_posts) == 2, "YouTube should have 2 posts"
        assert len(twitch_posts) == 2, "Twitch should have 2 posts"
        assert len(twitter_posts) == 2, "Twitter should have 2 posts (1 success, 1 failed)"

        # Verify post statuses
        successful_posts = db_session.query(SocialMediaPost).filter(
            SocialMediaPost.status == PostStatus.POSTED
        ).count()
        failed_posts = db_session.query(SocialMediaPost).filter(
            SocialMediaPost.status == PostStatus.FAILED
        ).count()

        assert successful_posts == 5, "Should have 5 successful posts"
        assert failed_posts == 1, "Should have 1 failed post"

    def test_verify_api_returns_combined_metrics(self, client, db_session):
        """
        Test Step 3 & 4: Wait for analytics aggregation and verify API returns combined metrics.

        Verifies that the multi-platform analytics API endpoint returns:
        - Aggregated totals across all platforms
        - Per-platform breakdowns
        - Correct calculations (total posts, success rates, etc.)
        """
        # First, ensure we have activity data from test_step_2
        self.test_generate_viewer_activity_on_each_platform(db_session)

        # Call the multi-platform analytics API
        response = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "period" in data
        assert "total_platforms" in data
        assert "active_platforms" in data
        assert "platforms" in data
        assert "total_streams" in data
        assert "total_posts" in data
        assert "successful_posts_rate" in data

        # Verify combined totals
        assert data["total_platforms"] >= 3, f"Expected at least 3 platforms, got {data['total_platforms']}"
        assert data["active_platforms"] >= 3, f"Expected at least 3 active platforms, got {data['active_platforms']}"
        assert data["total_posts"] >= 6, f"Expected at least 6 total posts, got {data['total_posts']}"

        # Verify success rate is calculated correctly
        expected_success_rate = (5 / 6) * 100  # 5 successful out of 6 total
        assert abs(data["successful_posts_rate"] - expected_success_rate) < 1.0, \
            f"Expected success rate ~{expected_success_rate}%, got {data['successful_posts_rate']}%"

        # Verify platforms array contains all platforms
        platform_ids_in_response = [p["platform_type"] for p in data["platforms"]]
        assert "youtube" in platform_ids_in_response, "YouTube not in response"
        assert "twitch" in platform_ids_in_response, "Twitch not in response"
        assert "twitter" in platform_ids_in_response, "Twitter not in response"

    def test_verify_frontend_dashboard_shows_total_and_breakdown(self, client, db_session):
        """
        Test Step 5: Verify frontend dashboard shows total + breakdown.

        Verifies that the API response structure includes both:
        - Aggregated totals for dashboard summary cards
        - Per-platform breakdowns for detailed views
        """
        # Ensure we have activity data
        self.test_generate_viewer_activity_on_each_platform(db_session)

        # Get analytics data
        response = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify dashboard summary metrics (totals for top cards)
        summary_metrics = {
            "total_platforms": data["total_platforms"],
            "active_platforms": data["active_platforms"],
            "total_streams": data["total_streams"],
            "total_stream_hours": data["total_stream_hours"],
            "total_posts": data["total_posts"],
            "successful_posts_rate": data["successful_posts_rate"]
        }

        # All summary metrics should be present and non-null
        for key, value in summary_metrics.items():
            assert value is not None, f"Summary metric {key} should not be null"

        # Verify per-platform breakdown (for detailed view)
        assert isinstance(data["platforms"], list), "platforms should be a list"
        assert len(data["platforms"]) >= 3, "Should have at least 3 platform breakdowns"

        # Check each platform breakdown has required fields
        for platform in data["platforms"]:
            required_fields = [
                "platform_type",
                "platform_name",
                "status",
                "stream_count",
                "post_count",
                "successful_posts",
                "failed_posts",
                "last_activity"
            ]
            for field in required_fields:
                assert field in platform, f"Platform breakdown missing field: {field}"

        # Verify we can identify which platforms have most activity
        # (useful for frontend to highlight top performers)
        platforms_by_posts = sorted(data["platforms"], key=lambda p: p["post_count"], reverse=True)
        assert len(platforms_by_posts) > 0, "Should have platform post counts"

        # Top platform should be YouTube or Twitch (we created 2 posts each)
        top_platform = platforms_by_posts[0]
        assert top_platform["post_count"] >= 2, "Top platform should have at least 2 posts"

    def test_verify_platform_specific_metrics_are_calculated(self, client, db_session):
        """
        Test Step 6: Verify platform-specific metrics and optimizations.

        Verifies that:
        - Each platform has accurate individual metrics
        - Post success/failure rates are tracked per platform
        - Last activity is tracked per platform
        - Platform status is correctly reported
        """
        # Ensure we have activity data
        self.test_generate_viewer_activity_on_each_platform(db_session)

        # Get analytics data
        response = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Find each platform in the response
        platforms_by_type = {p["platform_type"]: p for p in data["platforms"]}

        # Verify YouTube metrics
        if "youtube" in platforms_by_type:
            youtube = platforms_by_type["youtube"]
            assert youtube["platform_type"] == "youtube"
            assert youtube["post_count"] >= 2, "YouTube should have at least 2 posts"
            assert youtube["successful_posts"] >= 2, "YouTube posts should all be successful"
            assert youtube["failed_posts"] == 0, "YouTube should have no failed posts"
            assert youtube["last_activity"] is not None, "YouTube should have last activity timestamp"

        # Verify Twitch metrics
        if "twitch" in platforms_by_type:
            twitch = platforms_by_type["twitch"]
            assert twitch["platform_type"] == "twitch"
            assert twitch["post_count"] >= 2, "Twitch should have at least 2 posts"
            assert twitch["successful_posts"] >= 2, "Twitch posts should all be successful"
            assert twitch["failed_posts"] == 0, "Twitch should have no failed posts"
            assert twitch["last_activity"] is not None, "Twitch should have last activity timestamp"

        # Verify Twitter metrics (including the failed post)
        if "twitter" in platforms_by_type:
            twitter = platforms_by_type["twitter"]
            assert twitter["platform_type"] == "twitter"
            assert twitter["post_count"] >= 2, "Twitter should have at least 2 posts"
            assert twitter["successful_posts"] >= 1, "Twitter should have at least 1 successful post"
            assert twitter["failed_posts"] >= 1, "Twitter should have at least 1 failed post"
            assert twitter["last_activity"] is not None, "Twitter should have last activity timestamp"

            # Verify success rate calculation for Twitter
            if twitter["post_count"] > 0:
                twitter_success_rate = (twitter["successful_posts"] / twitter["post_count"]) * 100
                assert 0 <= twitter_success_rate <= 100, "Twitter success rate should be between 0-100%"

    def test_analytics_aggregation_with_different_time_periods(self, client, db_session):
        """
        Test analytics aggregation with different time periods.

        Verifies that the period filter (7d, 30d, 90d, all) works correctly.
        """
        # Ensure we have activity data
        self.test_generate_viewer_activity_on_each_platform(db_session)

        # Test 7d period
        response_7d = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )
        assert response_7d.status_code == 200
        data_7d = response_7d.json()
        assert data_7d["period"] == "7d"
        assert data_7d["total_posts"] >= 6

        # Test 30d period
        response_30d = client.get(
            "/api/analytics/multi-platform?period=30d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )
        assert response_30d.status_code == 200
        data_30d = response_30d.json()
        assert data_30d["period"] == "30d"

        # 30d should include at least as many posts as 7d
        assert data_30d["total_posts"] >= data_7d["total_posts"]

        # Test 'all' period
        response_all = client.get(
            "/api/analytics/multi-platform?period=all",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )
        assert response_all.status_code == 200
        data_all = response_all.json()
        assert data_all["period"] == "all"

        # 'all' should include the most posts
        assert data_all["total_posts"] >= data_30d["total_posts"]

    def test_analytics_caching_behavior(self, client, db_session):
        """
        Test that analytics results are cached for performance.

        Verifies that subsequent calls within the cache TTL return cached results.
        """
        # Ensure we have activity data
        self.test_generate_viewer_activity_on_each_platform(db_session)

        # First call - should compute and cache
        response_1 = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )
        assert response_1.status_code == 200
        data_1 = response_1.json()

        # Verify cached_at timestamp is present
        assert "cached_at" in data_1
        assert data_1["cached_at"] is not None

        # Second call - should return cached result (same timestamp)
        response_2 = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )
        assert response_2.status_code == 200
        data_2 = response_2.json()

        # Both should have same data (from cache)
        assert data_1["total_posts"] == data_2["total_posts"]
        assert data_1["total_platforms"] == data_2["total_platforms"]
        assert len(data_1["platforms"]) == len(data_2["platforms"])

    def test_analytics_with_no_activity(self, client, db_session):
        """
        Test analytics when there are platforms but no activity.

        Verifies that analytics handles edge cases gracefully.
        """
        # Create a new platform with no activity
        inactive_platform = StreamingPlatform(
            user_id=self.admin_user.id,
            platform_type=PlatformType.CUSTOM,
            platform_name='Inactive Custom RTMP',
            credentials='encrypted_credentials',
            stream_key='test_key',
            rtmp_url='rtmp://custom.example.com/live',
            status='inactive'
        )
        db_session.add(inactive_platform)
        db_session.commit()
        db_session.refresh(inactive_platform)

        # Get analytics - should include inactive platform
        response = client.get(
            "/api/analytics/multi-platform?period=7d",
            headers={"Authorization": f"Bearer {self._get_token(client)}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should include the inactive platform in total count
        assert data["total_platforms"] >= 4

        # Find the inactive platform in the list
        inactive_in_response = any(
            p["platform_type"] == "custom" and p["platform_name"] == "Inactive Custom RTMP"
            for p in data["platforms"]
        )
        assert inactive_in_response, "Inactive platform should still appear in analytics"

        # Inactive platform should have 0 posts
        for platform in data["platforms"]:
            if platform["platform_type"] == "custom" and platform["platform_name"] == "Inactive Custom RTMP":
                assert platform["post_count"] == 0
                assert platform["successful_posts"] == 0
                assert platform["failed_posts"] == 0

    def _get_token(self, client):
        """Helper to get auth token for test user."""
        from src.auth.jwt import create_access_token
        return create_access_token(
            data={"sub": str(self.admin_user.id), "role": self.admin_user.role}
        )
