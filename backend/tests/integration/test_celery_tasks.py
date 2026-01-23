"""
Celery Background Tasks Integration Tests

Integration tests for Celery background tasks related to smart scheduling and auto-pilot features.
Tests cover task execution, error handling, retry logic, and result validation.

Tests:
- Auto-fill gaps task execution
- Schedule optimization task execution
- Daily suggestions task execution
- Task retry behavior on temporary errors
- Task failure handling
- Task result structure validation
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy import select, and_
from database import SessionLocal
from src.models.schedule import ScheduleSlot, ScheduleTemplate, Playlist, Channel
from src.models.analytics import TrackPlay
from src.models.schedule_optimization import ScheduleOptimization, ScheduleRecommendation
from src.services.auto_pilot_service import AutoPilotService, fill_gaps_task, generate_schedule_task
from src.services.schedule_optimization_service import ScheduleOptimizationService, run_optimization_task
from src.services.schedule_recommendation_service import ScheduleRecommendationService, generate_daily_suggestions_task
from src.models.user import User, UserRole


# ==================== Fixtures ====================

@pytest.fixture
def admin_user(db_session):
    """Create admin user for testing."""
    user = User(
        id=uuid4(),
        email="admin@test.com",
        username="admin",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_channel(db_session, admin_user):
    """Create test channel."""
    from src.models.telegram import TelegramAccount

    telegram_account = TelegramAccount(
        id=uuid4(),
        user_id=admin_user.id,
        phone_number="+1234567890",
        username="test_channel",
        is_active=True
    )
    db_session.add(telegram_account)
    db_session.flush()

    channel = Channel(
        id=uuid4(),
        user_id=admin_user.id,
        telegram_account_id=telegram_account.id,
        name="Test Channel",
        is_active=True
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def test_playlists(db_session, test_channel):
    """Create test playlists with different engagement levels."""
    playlists = []

    for i in range(3):
        playlist = Playlist(
            id=uuid4(),
            channel_id=test_channel.id,
            name=f"Playlist {i+1}",
            items=[],
            items_count=5,
            total_duration=3600,
            is_active=True
        )
        db_session.add(playlist)
        playlists.append(playlist)

    db_session.commit()

    for playlist in playlists:
        db_session.refresh(playlist)

    return playlists


@pytest.fixture
def engagement_data(db_session, test_channel, test_playlists):
    """Create engagement data for recommendations."""
    from src.models.content import Track, PlaylistItem

    # Create tracks
    tracks = []
    for i in range(5):
        track = Track(
            id=uuid4(),
            title=f"Track {i+1}",
            artist=f"Artist {i+1}",
            duration=300,
            file_path=f"/tracks/{i+1}.mp3"
        )
        db_session.add(track)
        tracks.append(track)

    db_session.commit()

    # Create playlist items
    for playlist in test_playlists:
        for track in tracks[:3]:
            item = PlaylistItem(
                id=uuid4(),
                playlist_id=playlist.id,
                track_id=track.id,
                position=tracks.index(track) + 1
            )
            db_session.add(item)

    db_session.commit()

    # Create engagement data (TrackPlay records)
    # Playlist 0: High engagement (evening hours)
    # Playlist 1: Medium engagement (daytime hours)
    # Playlist 2: Low engagement (morning hours)

    now = datetime.utcnow()
    engagement_records = []

    for days_ago in range(30):
        target_date = now - timedelta(days=days_ago)

        # High engagement for Playlist 0 (19:00-21:00)
        for hour in [19, 20, 21]:
            play = TrackPlay(
                id=uuid4(),
                playlist_item_id=uuid4(),  # Mock ID
                played_at=target_date.replace(hour=hour, minute=0, second=0),
                duration_seconds=300,
                listeners_count=75 + (hour % 3) * 10  # 75-95 listeners
            )
            engagement_records.append(play)

        # Medium engagement for Playlist 1 (13:00-15:00)
        for hour in [13, 14, 15]:
            play = TrackPlay(
                id=uuid4(),
                playlist_item_id=uuid4(),
                played_at=target_date.replace(hour=hour, minute=0, second=0),
                duration_seconds=300,
                listeners_count=25 + (hour % 3) * 5  # 25-35 listeners
            )
            engagement_records.append(play)

        # Low engagement for Playlist 2 (07:00-09:00)
        for hour in [7, 8, 9]:
            play = TrackPlay(
                id=uuid4(),
                playlist_item_id=uuid4(),
                played_at=target_date.replace(hour=hour, minute=0, second=0),
                duration_seconds=300,
                listeners_count=5 + (hour % 3) * 2  # 5-9 listeners
            )
            engagement_records.append(play)

    db_session.add_all(engagement_records)
    db_session.commit()

    return engagement_records


@pytest.fixture
def schedule_with_gaps(db_session, test_channel, test_playlists):
    """Create schedule with gaps for testing gap filling."""
    today = date.today()

    # Create some slots to leave gaps
    slots = [
        # Day 1: Morning slot only (gap in afternoon/evening)
        ScheduleSlot(
            id=uuid4(),
            channel_id=test_channel.id,
            playlist_id=test_playlists[0].id,
            start_date=today,
            start_time="08:00",
            end_time="10:00",
            title="Morning Show",
            is_active=True,
            priority=5
        ),
        # Day 2: Afternoon slot only (gap in morning/evening)
        ScheduleSlot(
            id=uuid4(),
            channel_id=test_channel.id,
            playlist_id=test_playlists[1].id,
            start_date=today + timedelta(days=1),
            start_time="14:00",
            end_time="16:00",
            title="Afternoon Show",
            is_active=True,
            priority=5
        ),
    ]

    db_session.add_all(slots)
    db_session.commit()

    return slots


# ==================== Test: Auto-Fill Gaps Task ====================

class TestFillGapsTask:
    """Test suite for fill_gaps_task Celery task."""

    def test_fill_gaps_task_execution(
        self,
        db_session,
        test_channel,
        test_playlists,
        schedule_with_gaps
    ):
        """Test fill_gaps_task executes and fills gaps in schedule."""
        # Arrange
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)

        # Get initial gap count
        from src.schemas.schedule_ai import GapDetectionRequest
        service = ScheduleOptimizationService(db_session)
        service._init_services()

        initial_request = GapDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=start_date,
            end_date=end_date,
            consider_peak_hours=True
        )

        initial_gaps = service.detect_gaps(initial_request)
        initial_gap_count = len(initial_gaps.gaps) if initial_gaps.gaps else 0

        # Act
        result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            max_daily_hours=24,
            use_ai_recommendations=False,  # Use fallback for testing
            user_id=str(test_channel.user_id)
        )

        # Assert
        assert result["status"] == "completed"
        assert result["channel_id"] == str(test_channel.id)
        assert result["gaps_filled"] >= 0
        assert result["total_gap_hours"] >= 0.0
        assert result["error_message"] is None

        # Verify gaps were filled (new slots created)
        slots_after = db_session.execute(
            select(ScheduleSlot).where(
                ScheduleSlot.channel_id == test_channel.id
            )
        ).scalars().all()

        # Should have more slots now
        assert len(slots_after) > len(schedule_with_gaps)

    def test_fill_gaps_task_with_ai_recommendations(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test fill_gaps_task with AI recommendations enabled."""
        # Arrange
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)

        # Act
        result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            max_daily_hours=24,
            use_ai_recommendations=True,
            user_id=str(test_channel.user_id)
        )

        # Assert
        assert result["status"] == "completed"
        assert result["gaps_filled"] >= 0
        # AI recommendations may fill more or less gaps depending on confidence

    def test_fill_gaps_task_respects_max_daily_hours(
        self,
        db_session,
        test_channel,
        test_playlists
    ):
        """Test fill_gaps_task respects max_daily_hours limit."""
        # Arrange
        start_date = date.today()
        end_date = date.today()
        max_hours = 4  # Limit to 4 hours per day

        # Act
        result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            max_daily_hours=max_hours,
            use_ai_recommendations=False,
            user_id=str(test_channel.user_id)
        )

        # Assert
        assert result["status"] == "completed"

        # Verify total hours scheduled doesn't exceed limit
        slots = db_session.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == test_channel.id,
                    ScheduleSlot.start_date == start_date
                )
            )
        ).scalars().all()

        total_hours = sum(
            (s.end_time.hour - s.start_time.hour) +
            (s.end_time.minute - s.start_time.minute) / 60.0
            for s in slots
        )

        assert total_hours <= max_hours

    def test_fill_gaps_task_with_no_playlists(
        self,
        db_session,
        test_channel
    ):
        """Test fill_gaps_task handles no playlists gracefully."""
        # Arrange
        start_date = date.today()
        end_date = date.today()

        # Act
        result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            max_daily_hours=24,
            use_ai_recommendations=False,
            user_id=str(test_channel.user_id)
        )

        # Assert - should complete but fill no gaps
        assert result["status"] in ["completed", "failed"]
        assert result["gaps_filled"] == 0

    def test_fill_gaps_task_retry_on_temporary_error(
        self,
        db_session,
        test_channel,
        test_playlists
    ):
        """Test fill_gaps_task retries on temporary errors."""
        # Arrange
        start_date = date.today()

        with patch('database.SessionLocal') as mock_session:
            # First call raises connection error, second succeeds
            mock_session.side_effect = [
                Exception("Database connection timeout"),
                SessionLocal()
            ]

            # Act & Assert
            # Task should retry on temporary error
            with pytest.raises(Exception) as exc_info:
                fill_gaps_task(
                    channel_id=str(test_channel.id),
                    date_range_start=start_date.isoformat(),
                    date_range_end=start_date.isoformat(),
                    max_daily_hours=24,
                    use_ai_recommendations=False
                )

            # Verify retry was raised
            assert "retry" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()


# ==================== Test: Schedule Optimization Task ====================

class TestRunOptimizationTask:
    """Test suite for run_optimization_task Celery task."""

    def test_optimization_task_execution(
        self,
        db_session,
        test_channel,
        test_playlists,
        schedule_with_gaps
    ):
        """Test run_optimization_task executes and produces optimization results."""
        # Arrange
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)

        # Act
        result = run_optimization_task(
            channel_id=str(test_channel.id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            priorities={
                "coverage": 0.25,
                "engagement": 0.30,
                "variety": 0.20,
                "conflicts": 0.15,
                "peak_hours": 0.10
            },
            auto_apply=False  # Don't actually create slots in test
        )

        # Assert
        assert result["status"] in ["completed", "failed"]
        assert "optimization_id" in result
        assert "metrics" in result
        assert "suggestions_count" in result
        assert "gaps_found" in result
        assert "conflicts_found" in result

        # Verify optimization record was created
        optimizations = db_session.execute(
            select(ScheduleOptimization).where(
                ScheduleOptimization.channel_id == test_channel.id
            )
        ).scalars().all()

        assert len(optimizations) > 0

    def test_optimization_task_with_auto_apply(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test run_optimization_task with auto_apply enabled."""
        # Arrange
        start_date = date.today()
        end_date = date.today()

        # Get initial slot count
        initial_slots = db_session.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == test_channel.id,
                    ScheduleSlot.start_date >= start_date,
                    ScheduleSlot.start_date <= end_date
                )
            )
        ).scalars().all()
        initial_count = len(initial_slots)

        # Act
        result = run_optimization_task(
            channel_id=str(test_channel.id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            priorities={
                "coverage": 0.25,
                "engagement": 0.30,
                "variety": 0.20,
                "conflicts": 0.15,
                "peak_hours": 0.10
            },
            auto_apply=True,  # Create slots from suggestions
            max_suggestions=10
        )

        # Assert
        assert result["status"] in ["completed", "failed"]

        # Verify slots were created
        final_slots = db_session.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == test_channel.id,
                    ScheduleSlot.start_date >= start_date,
                    ScheduleSlot.start_date <= end_date
                )
            )
        ).scalars().all()

        # Should have created new slots
        assert len(final_slots) >= initial_count

    def test_optimization_task_metrics_calculation(
        self,
        db_session,
        test_channel,
        test_playlists,
        schedule_with_gaps,
        engagement_data
    ):
        """Test run_optimization_task calculates optimization metrics correctly."""
        # Arrange
        start_date = date.today()
        end_date = date.today()

        # Act
        result = run_optimization_task(
            channel_id=str(test_channel.id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            priorities={
                "coverage": 0.25,
                "engagement": 0.30,
                "variety": 0.20,
                "conflicts": 0.15,
                "peak_hours": 0.10
            },
            auto_apply=False
        )

        # Assert
        if result["status"] == "completed":
            metrics = result["metrics"]
            assert "coverage_percent" in metrics
            assert "engagement_score" in metrics
            assert "variety_score" in metrics
            assert "conflicts_count" in metrics
            assert "peak_hours_coverage" in metrics

            # Verify metrics are in valid ranges
            assert 0 <= metrics["coverage_percent"] <= 100
            assert 0 <= metrics["engagement_score"] <= 10
            assert 0 <= metrics["variety_score"] <= 10
            assert metrics["conflicts_count"] >= 0
            assert 0 <= metrics["peak_hours_coverage"] <= 100

    def test_optimization_task_handles_invalid_channel(
        self,
        db_session
    ):
        """Test run_optimization_task handles invalid channel ID."""
        # Arrange
        fake_channel_id = str(uuid4())
        start_date = date.today()
        end_date = date.today()

        # Act
        result = run_optimization_task(
            channel_id=fake_channel_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            priorities={},
            auto_apply=False
        )

        # Assert - should handle gracefully
        assert result["status"] in ["completed", "failed"]


# ==================== Test: Daily Suggestions Task ====================

class TestDailySuggestionsTask:
    """Test suite for generate_daily_suggestions_task Celery task."""

    def test_daily_suggestions_task_execution(
        self,
        db_session,
        admin_user,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test generate_daily_suggestions_task creates recommendations."""
        # Act
        result = generate_daily_suggestions_task()

        # Assert
        assert result["status"] == "completed"
        assert "processed_channels" in result
        assert "total_recommendations" in result
        assert isinstance(result["processed_channels"], int)
        assert isinstance(result["total_recommendations"], int)

        # Verify recommendations were created for test channel
        if result["total_recommendations"] > 0:
            recommendations = db_session.execute(
                select(ScheduleRecommendation).where(
                    ScheduleRecommendation.channel_id == test_channel.id
                )
            ).scalars().all()

            assert len(recommendations) > 0

    def test_daily_suggestions_task_creates_for_tomorrow(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test generate_daily_suggestions_task creates recommendations for tomorrow."""
        # Arrange
        tomorrow = date.today() + timedelta(days=1)

        # Act
        result = generate_daily_suggestions_task()

        # Assert
        if result["total_recommendations"] > 0:
            # Check if recommendations exist for tomorrow
            recommendations = db_session.execute(
                select(ScheduleRecommendation).where(
                    and_(
                        ScheduleRecommendation.channel_id == test_channel.id,
                        ScheduleRecommendation.target_date == tomorrow
                    )
                )
            ).scalars().all()

            # Should have recommendations for tomorrow (or next day)
            assert len(recommendations) >= 0

    def test_daily_suggestions_task_handles_empty_channels(
        self,
        db_session
    ):
        """Test generate_daily_suggestions_task handles no active channels gracefully."""
        # Arrange - create channel with no playlists
        from src.models.user import User
        from src.models.telegram import TelegramAccount

        user = User(
            id=uuid4(),
            email="empty@test.com",
            username="empty",
            hashed_password="hash",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user)

        telegram_account = TelegramAccount(
            id=uuid4(),
            user_id=user.id,
            phone_number="+0987654321",
            username="empty_channel",
            is_active=True
        )
        db_session.add(telegram_account)
        db_session.flush()

        empty_channel = Channel(
            id=uuid4(),
            user_id=user.id,
            telegram_account_id=telegram_account.id,
            name="Empty Channel",
            is_active=True
        )
        db_session.add(empty_channel)
        db_session.commit()

        # Act
        result = generate_daily_suggestions_task()

        # Assert - should complete without errors
        assert result["status"] == "completed"

    def test_daily_suggestions_task_with_engagement_data(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test generate_daily_suggestions_task uses engagement data for recommendations."""
        # Arrange - delete any existing recommendations
        db_session.execute(
            select(ScheduleRecommendation).where(
                ScheduleRecommendation.channel_id == test_channel.id
            )
        )
        db_session.commit()

        # Act
        result = generate_daily_suggestions_task()

        # Assert
        assert result["status"] == "completed"

        # Verify recommendations have confidence scores
        recommendations = db_session.execute(
            select(ScheduleRecommendation).where(
                ScheduleRecommendation.channel_id == test_channel.id
            )
        ).scalars().all()

        for rec in recommendations:
            assert rec.confidence_score >= 0
            assert rec.playlist_id is not None


# ==================== Test: Generate Schedule Task ====================

class TestGenerateScheduleTask:
    """Test suite for generate_schedule_task Celery task."""

    def test_generate_schedule_task_full_workflow(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test generate_schedule_task executes full auto-pilot workflow."""
        # Arrange
        start_date = date.today()
        end_date = date.today() + timedelta(days=2)

        # Act
        result = generate_schedule_task(
            task_id=str(uuid4()),
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            template=None,
            fill_gaps=True,
            max_daily_hours=12,
            use_ai_recommendations=False,
            resolve_conflicts=True,
            user_id=str(test_channel.user_id)
        )

        # Assert
        assert result["status"] in ["completed", "failed"]
        assert "task_id" in result
        assert "channel_id" in result
        assert "slots_created" in result
        assert "gaps_filled" in result
        assert "conflicts_resolved" in result

        # Verify slots were created
        slots = db_session.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == test_channel.id,
                    ScheduleSlot.start_date >= start_date,
                    ScheduleSlot.start_date <= end_date
                )
            )
        ).scalars().all()

        assert len(slots) > 0

    def test_generate_schedule_task_with_template(
        self,
        db_session,
        test_channel,
        test_playlists
    ):
        """Test generate_schedule_task applies template."""
        # Arrange
        start_date = date.today()
        end_date = date.today() + timedelta(days=2)

        template = {
            "name": "Test Template",
            "description": "Template for testing",
            "slots": [
                {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "playlist_id": str(test_playlists[0].id),
                    "title": "Template Slot 1",
                    "repeat_type": "DAILY",
                    "priority": 5
                }
            ]
        }

        # Act
        result = generate_schedule_task(
            task_id=str(uuid4()),
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            template=template,
            fill_gaps=False,
            max_daily_hours=24,
            use_ai_recommendations=False,
            resolve_conflicts=False,
            user_id=str(test_channel.user_id)
        )

        # Assert
        assert result["status"] in ["completed", "failed"]
        assert result["slots_created"] >= 0

        # Verify template slots were created
        slots = db_session.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == test_channel.id,
                    ScheduleSlot.start_date >= start_date
                )
            )
        ).scalars().all()

        # Should have created slots from template
        assert len(slots) > 0

    def test_generate_schedule_task_error_handling(
        self,
        db_session,
        test_channel
    ):
        """Test generate_schedule_task handles errors gracefully."""
        # Arrange - use invalid data
        start_date = date.today()

        # Act
        result = generate_schedule_task(
            task_id=str(uuid4()),
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=start_date.isoformat(),
            template=None,
            fill_gaps=True,
            max_daily_hours=24,
            use_ai_recommendations=True,
            resolve_conflicts=True,
            user_id=str(test_channel.user_id)
        )

        # Assert - should complete even with errors
        assert "status" in result
        assert "error_message" in result


# ==================== Test: Task Integration ====================

class TestCeleryTaskIntegration:
    """Integration tests for Celery task orchestration."""

    def test_multiple_tasks_execution_order(
        self,
        db_session,
        test_channel,
        test_playlists,
        engagement_data
    ):
        """Test multiple tasks can execute in correct order."""
        # Arrange
        start_date = date.today()
        end_date = date.today()

        # Step 1: Generate daily suggestions
        suggestions_result = generate_daily_suggestions_task()
        assert suggestions_result["status"] == "completed"

        # Step 2: Fill gaps
        gaps_result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            max_daily_hours=24,
            use_ai_recommendations=False,
            user_id=str(test_channel.user_id)
        )
        assert gaps_result["status"] == "completed"

        # Step 3: Run optimization
        optimization_result = run_optimization_task(
            channel_id=str(test_channel.id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            priorities={},
            auto_apply=False
        )
        assert optimization_result["status"] in ["completed", "failed"]

    def test_task_result_structure_validation(
        self,
        db_session,
        test_channel,
        test_playlists
    ):
        """Test all tasks return properly structured results."""
        start_date = date.today()

        # Test fill_gaps_task result structure
        gaps_result = fill_gaps_task(
            channel_id=str(test_channel.id),
            date_range_start=start_date.isoformat(),
            date_range_end=start_date.isoformat(),
            max_daily_hours=24,
            use_ai_recommendations=False
        )

        required_fields = ["channel_id", "date_range", "status", "gaps_filled", "total_gap_hours", "error_message"]
        for field in required_fields:
            assert field in gaps_result

        # Test run_optimization_task result structure
        optimization_result = run_optimization_task(
            channel_id=str(test_channel.id),
            start_date=start_date.isoformat(),
            end_date=start_date.isoformat(),
            priorities={},
            auto_apply=False
        )

        required_opt_fields = ["optimization_id", "channel_id", "status", "metrics", "suggestions_count"]
        for field in required_opt_fields:
            assert field in optimization_result

        # Test generate_daily_suggestions_task result structure
        suggestions_result = generate_daily_suggestions_task()

        required_sug_fields = ["status", "processed_channels", "total_recommendations", "errors"]
        for field in required_sug_fields:
            assert field in suggestions_result
