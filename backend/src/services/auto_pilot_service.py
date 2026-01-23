"""
AutoPilotService for one-click schedule generation.

Features:
- Automatic schedule generation based on AI recommendations
- Gap filling with optimal content
- Template-based recurring schedule creation
- Conflict resolution during generation
- Background task support for large date ranges

External Library: APScheduler 3.10+, Celery 5.3+
"""

import logging
import uuid
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from src.models.schedule import ScheduleSlot, ScheduleTemplate, RepeatType
from src.models.playlist import Playlist
from src.models.schedule_optimization import ScheduleOptimization, OptimizationStatus
from src.schemas.schedule_ai import (
    AutoPilotRequest,
    AutoPilotResponse,
    AutoPilotProgress,
    AutoPilotTemplate,
    OptimizationParameters,
    ScheduleSlotSuggestion,
    AppliedChanges,
)
from src.services.schedule_recommendation_service import ScheduleRecommendationService
from src.services.schedule_optimization_service import ScheduleOptimizationService


logger = logging.getLogger(__name__)

# Lazy Celery import
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False


def _get_celery_app():
    """Get or create Celery application."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


class AutoPilotService:
    """Manages automatic schedule generation (auto-pilot mode)."""

    def __init__(self, db_session: Session):
        """
        Initialize auto-pilot service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logger

        # Initialize recommendation and optimization services
        self.recommendation_service: Optional[ScheduleRecommendationService] = None
        self.optimization_service: Optional[ScheduleOptimizationService] = None

    def _init_services(self, redis_client=None):
        """
        Lazy initialization of dependent services.

        Args:
            redis_client: Optional Redis client for caching
        """
        if self.recommendation_service is None:
            self.recommendation_service = ScheduleRecommendationService(
                self.db, redis_client
            )
        if self.optimization_service is None:
            self.optimization_service = ScheduleOptimizationService(
                self.db, redis_client
            )

    async def generate_schedule(
        self,
        request: AutoPilotRequest,
        user_id: Optional[str] = None,
        redis_client=None
    ) -> AutoPilotResponse:
        """
        Generate complete schedule automatically (one-click generation).

        Args:
            request: Auto-pilot request with date range and options
            user_id: Optional user ID who initiated generation
            redis_client: Optional Redis client for caching

        Returns:
            AutoPilotResponse with generation results
        """
        self._init_services(redis_client)

        # Parse date range
        start_date = date.fromisoformat(request.date_range["start"])
        end_date = date.fromisoformat(request.date_range["end"])

        # Validate date range
        if end_date < start_date:
            raise ValueError("End date must be after start date")

        task_id = str(uuid.uuid4())

        self.logger.info(
            f"Starting auto-pilot schedule generation for channel {request.channel_id}, "
            f"dates {start_date} to {end_date}"
        )

        try:
            # Apply template if provided
            slots_created = 0
            if request.template:
                template_slots = await self._apply_template(
                    request.channel_id,
                    request.template,
                    start_date,
                    end_date,
                    user_id
                )
                slots_created += template_slots

            # Fill gaps with AI recommendations
            gaps_filled = 0
            if request.fill_gaps:
                filled = await self._fill_gaps_with_recommendations(
                    request.channel_id,
                    start_date,
                    end_date,
                    request.max_daily_hours,
                    request.use_ai_recommendations,
                    user_id
                )
                gaps_filled = filled

            # Resolve conflicts if requested
            conflicts_resolved = 0
            if request.resolve_conflicts:
                resolved = await self._resolve_schedule_conflicts(
                    request.channel_id,
                    start_date,
                    end_date
                )
                conflicts_resolved = resolved

            total_slots = slots_created + gaps_filled

            self.logger.info(
                f"Auto-pilot generation completed: {total_slots} slots created, "
                f"{gaps_filled} gaps filled, {conflicts_resolved} conflicts resolved"
            )

            return AutoPilotResponse(
                task_id=task_id,
                channel_id=request.channel_id,
                status="completed",
                date_range=request.date_range,
                slots_created=total_slots,
                gaps_filled=gaps_filled,
                conflicts_resolved=conflicts_resolved,
                created_at=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error(f"Auto-pilot generation failed: {e}")
            return AutoPilotResponse(
                task_id=task_id,
                channel_id=request.channel_id,
                status="failed",
                date_range=request.date_range,
                slots_created=0,
                gaps_filled=0,
                conflicts_resolved=0,
                error_message=str(e),
                created_at=datetime.utcnow()
            )

    def generate_schedule_async(
        self,
        request: AutoPilotRequest,
        user_id: Optional[str] = None
    ) -> str:
        """
        Submit background task for schedule generation.

        This method queues a Celery task for background schedule generation.
        The actual generation happens asynchronously in the worker process.

        Args:
            request: Auto-pilot request
            user_id: Optional user ID

        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())

        # Parse date range
        start_date = request.date_range["start"]
        end_date = request.date_range["end"]

        # Convert template to dict if present
        template_dict = None
        if request.template:
            template_dict = request.template.dict()

        # Check if Celery is available
        if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
            app = _get_celery_app()
            try:
                # Queue the task
                app.send_task(
                    'services.auto_pilot.generate_schedule',
                    args=[
                        task_id,
                        request.channel_id,
                        start_date,
                        end_date,
                        template_dict,
                        request.fill_gaps,
                        request.max_daily_hours,
                        request.use_ai_recommendations,
                        request.resolve_conflicts,
                        user_id
                    ]
                )
                self.logger.info(f"Background task queued: {task_id}")
                return task_id
            except Exception as e:
                self.logger.warning(f"Failed to queue Celery task: {e}, falling back to sync")

        # Fallback: Run synchronously if Celery not available
        self.logger.info(f"Running schedule generation synchronously: {task_id}")
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                self.generate_schedule(request, user_id)
            )
        finally:
            loop.close()

        if response.status == "failed":
            self.logger.error(f"Synchronous generation failed: {response.error_message}")

        return task_id

    async def get_generation_progress(
        self,
        task_id: str
    ) -> Optional[AutoPilotProgress]:
        """
        Get progress of background generation task.

        Args:
            task_id: Task ID from generate_schedule_async

        Returns:
            AutoPilotProgress or None if task not found
        """
        # TODO: Implement progress tracking with Redis/Celery result backend
        return None

    async def _apply_template(
        self,
        channel_id: str,
        template: AutoPilotTemplate,
        start_date: date,
        end_date: date,
        user_id: Optional[str] = None
    ) -> int:
        """
        Apply schedule template to date range.

        Args:
            channel_id: Channel ID
            template: Template to apply
            start_date: Start date
            end_date: End date
            user_id: Optional user ID

        Returns:
            Number of slots created
        """
        slots_created = 0
        channel_uuid = UUID(channel_id)

        # Determine which days to apply template
        target_days = self._get_target_days(template, start_date, end_date)

        for target_date in target_days:
            for time_slot in template.time_slots:
                # Parse times
                start_time = time.fromisoformat(time_slot["start_time"])
                end_time = time.fromisoformat(time_slot["end_time"])

                # Get playlist ID if provided
                playlist_id = UUID(time_slot["playlist_id"]) if time_slot.get("playlist_id") else None

                # Create slot
                slot = ScheduleSlot(
                    channel_id=channel_uuid,
                    playlist_id=playlist_id,
                    start_date=target_date,
                    start_time=start_time,
                    end_time=end_time,
                    title=time_slot.get("title"),
                    description=time_slot.get("description"),
                    color=time_slot.get("color", "#3B82F6"),
                    is_active=True,
                    priority=time_slot.get("priority", 5),
                    created_by=UUID(user_id) if user_id else None
                )

                self.db.add(slot)
                slots_created += 1

        self.db.commit()

        self.logger.info(
            f"Template applied: {slots_created} slots created from {start_date} to {end_date}"
        )

        return slots_created

    def _get_target_days(
        self,
        template: AutoPilotTemplate,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        Get list of target dates based on template repeat pattern.

        Args:
            template: Template with repeat pattern
            start_date: Start date
            end_date: End date

        Returns:
            List of dates to apply template
        """
        target_days = []
        current_date = start_date

        while current_date <= end_date:
            weekday = current_date.weekday()  # 0=Monday, 6=Sunday

            should_apply = False
            if template.repeat_pattern == "daily":
                should_apply = True
            elif template.repeat_pattern == "weekdays":
                should_apply = weekday < 5  # Mon-Fri
            elif template.repeat_pattern == "weekends":
                should_apply = weekday >= 5  # Sat-Sun
            elif template.repeat_pattern == "custom" and template.repeat_days:
                should_apply = weekday in template.repeat_days

            if should_apply:
                target_days.append(current_date)

            current_date += timedelta(days=1)

        return target_days

    async def _fill_gaps_with_recommendations(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        max_daily_hours: int,
        use_ai: bool,
        user_id: Optional[str] = None
    ) -> int:
        """
        Fill schedule gaps using AI recommendations.

        Args:
            channel_id: Channel ID
            start_date: Start date
            end_date: End date
            max_daily_hours: Maximum hours per day
            use_ai: Whether to use AI recommendations
            user_id: Optional user ID

        Returns:
            Number of gaps filled
        """
        # Detect gaps
        from src.schemas.schedule_ai import GapDetectionRequest

        gap_request = GapDetectionRequest(
            channel_id=channel_id,
            start_date=start_date,
            end_date=end_date,
            consider_peak_hours=True
        )

        gaps_response = await self.optimization_service.detect_gaps(gap_request)

        if not gaps_response.gaps:
            self.logger.info("No gaps to fill")
            return 0

        gaps_filled = 0

        # Group gaps by date
        gaps_by_date: Dict[date, List] = {}
        for gap in gaps_response.gaps:
            if gap.date not in gaps_by_date:
                gaps_by_date[gap.date] = []
            gaps_by_date[gap.date].append(gap)

        # Fill gaps for each day
        for gap_date, day_gaps in gaps_by_date.items():
            # Calculate current daily hours
            current_hours = await self._get_daily_hours(channel_id, gap_date)

            if current_hours >= max_daily_hours:
                self.logger.debug(f"Skipping {gap_date}: already {current_hours} hours")
                continue

            remaining_hours = max_daily_hours - current_hours

            # Sort gaps by priority (peak hours first)
            day_gaps.sort(key=lambda g: g.is_peak_hour, reverse=True)

            for gap in day_gaps:
                if remaining_hours <= 0:
                    break

                if gap.duration_hours > remaining_hours:
                    # Truncate gap to fit remaining hours
                    continue

                # Get recommendation for this gap
                if use_ai:
                    recommendation = await self._get_recommendation_for_gap(
                        channel_id, gap
                    )
                else:
                    # Get first available playlist
                    recommendation = await self._get_fallback_playlist(channel_id)

                if recommendation:
                    # Create slot from recommendation
                    slot = await self._create_slot_from_recommendation(
                        channel_id,
                        gap,
                        recommendation,
                        user_id
                    )

                    if slot:
                        gaps_filled += 1
                        remaining_hours -= gap.duration_hours

        self.db.commit()

        self.logger.info(f"Filled {gaps_filled} gaps in schedule")

        return gaps_filled

    async def _get_daily_hours(self, channel_id: str, target_date: date) -> float:
        """
        Calculate total scheduled hours for a day.

        Args:
            channel_id: Channel ID
            target_date: Date to check

        Returns:
            Total hours scheduled
        """
        channel_uuid = UUID(channel_id)

        slots = self.db.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == channel_uuid,
                    ScheduleSlot.start_date == target_date,
                    ScheduleSlot.is_active == True
                )
            )
        ).scalars().all()

        total_hours = 0.0
        for slot in slots:
            duration = (
                slot.end_time.hour - slot.start_time.hour +
                (slot.end_time.minute - slot.start_time.minute) / 60.0
            )
            total_hours += duration

        return total_hours

    async def _get_recommendation_for_gap(
        self,
        channel_id: str,
        gap
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI recommendation for filling a gap.

        Args:
            channel_id: Channel ID
            gap: Schedule gap

        Returns:
            Recommendation dict or None
        """
        from src.schemas.schedule_ai import ScheduleRecommendationRequest

        request = ScheduleRecommendationRequest(
            channel_id=channel_id,
            target_date=gap.date,
            max_recommendations=1,
            min_confidence=50.0
        )

        response = await self.recommendation_service.get_recommendations(request)

        if response.recommendations:
            rec = response.recommendations[0]
            return {
                "playlist_id": rec.playlist_id,
                "playlist_name": rec.playlist_name,
                "confidence": rec.confidence_score,
                "reason": f"{rec.description} (confidence: {rec.confidence_score}%)"
            }

        return None

    async def _get_fallback_playlist(
        self,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get fallback playlist when AI recommendations unavailable.

        Args:
            channel_id: Channel ID

        Returns:
            Playlist dict or None
        """
        channel_uuid = UUID(channel_id)

        # Get first active playlist for channel
        playlist = self.db.execute(
            select(Playlist).where(
                and_(
                    Playlist.channel_id == channel_uuid,
                    Playlist.is_active == True
                )
            ).order_by(Playlist.created_at)
        ).scalar_one_or_none()

        if playlist:
            return {
                "playlist_id": str(playlist.id),
                "playlist_name": playlist.name,
                "confidence": 50.0,
                "reason": "Fallback playlist (default selection)"
            }

        return None

    async def _create_slot_from_recommendation(
        self,
        channel_id: str,
        gap,
        recommendation: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[ScheduleSlot]:
        """
        Create schedule slot from recommendation.

        Args:
            channel_id: Channel ID
            gap: Schedule gap
            recommendation: Recommendation dict
            user_id: Optional user ID

        Returns:
            Created ScheduleSlot or None
        """
        try:
            slot = ScheduleSlot(
                channel_id=UUID(channel_id),
                playlist_id=UUID(recommendation["playlist_id"]) if recommendation["playlist_id"] else None,
                start_date=gap.date,
                start_time=time.fromisoformat(gap.start_time),
                end_time=time.fromisoformat(gap.end_time),
                title=recommendation.get("playlist_name", "Auto-generated"),
                description=recommendation.get("reason", "Generated by auto-pilot"),
                color="#10B981",  # Green for auto-generated
                is_active=True,
                priority=5,
                created_by=UUID(user_id) if user_id else None
            )

            self.db.add(slot)

            self.logger.debug(
                f"Created slot from recommendation: {gap.date} {gap.start_time}-{gap.end_time}"
            )

            return slot

        except Exception as e:
            self.logger.warning(f"Failed to create slot from recommendation: {e}")
            return None

    async def _resolve_schedule_conflicts(
        self,
        channel_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        Resolve conflicts in generated schedule.

        Args:
            channel_id: Channel ID
            start_date: Start date
            end_date: End date

        Returns:
            Number of conflicts resolved
        """
        from src.schemas.schedule_ai import ConflictDetectionRequest

        request = ConflictDetectionRequest(
            channel_id=channel_id,
            start_date=start_date,
            end_date=end_date
        )

        response = await self.optimization_service.resolve_conflicts(request)

        self.logger.info(f"Resolved {response.total_conflicts} conflicts")

        return response.total_conflicts

    async def create_template_from_schedule(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ScheduleTemplate:
        """
        Create template from existing schedule.

        Analyzes the schedule to detect recurring patterns and creates
        a template with proper repeat configuration.

        Args:
            channel_id: Channel ID
            start_date: Start date
            end_date: End date
            name: Template name
            description: Optional description
            user_id: User ID creating template

        Returns:
            Created ScheduleTemplate
        """
        channel_uuid = UUID(channel_id)

        # Get slots for the date range
        slots = self.db.execute(
            select(ScheduleSlot).where(
                and_(
                    ScheduleSlot.channel_id == channel_uuid,
                    ScheduleSlot.start_date >= start_date,
                    ScheduleSlot.start_date <= end_date,
                    ScheduleSlot.is_active == True
                )
            ).order_by(ScheduleSlot.start_time)
        ).scalars().all()

        # Analyze patterns and detect repeat type
        repeat_info = self._detect_repeat_pattern(slots, start_date, end_date)

        # Extract unique time patterns based on detected repeat type
        time_patterns = self._extract_time_patterns(slots, repeat_info)

        # Create template with repeat information
        template = ScheduleTemplate(
            user_id=UUID(user_id) if user_id else None,
            channel_id=channel_uuid,
            name=name,
            description=description,
            slots=list(time_patterns.values()),
            is_public=False
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        self.logger.info(
            f"Created template '{name}' with {len(template.slots)} slots, "
            f"repeat pattern: {repeat_info['repeat_type'].value}"
        )

        return template

    def _detect_repeat_pattern(
        self,
        slots: List[ScheduleSlot],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Detect repeat pattern from schedule slots.

        Args:
            slots: List of schedule slots
            start_date: Start date of period
            end_date: End date of period

        Returns:
            Dict with repeat_type, repeat_days, and detected pattern info
        """
        if not slots:
            return {"repeat_type": RepeatType.NONE, "repeat_days": None}

        # Group slots by time pattern
        time_patterns: Dict[tuple, List[date]] = {}
        for slot in slots:
            key = (slot.start_time, slot.end_time, slot.playlist_id)
            if key not in time_patterns:
                time_patterns[key] = []
            time_patterns[key].append(slot.start_date)

        # Analyze pattern for first time slot
        first_pattern_dates = list(time_patterns.values())[0]
        first_pattern_dates.sort()

        # Check for daily pattern (same slots every day)
        total_days = (end_date - start_date).days + 1
        coverage_ratio = len(first_pattern_dates) / total_days if total_days > 0 else 0

        if coverage_ratio >= 0.9:
            # Daily pattern
            return {
                "repeat_type": RepeatType.DAILY,
                "repeat_days": None,
                "confidence": coverage_ratio
            }

        # Check for weekdays pattern
        weekdays_count = sum(1 for d in first_pattern_dates if d.weekday() < 5)
        if weekdays_count / len(first_pattern_dates) >= 0.9:
            return {
                "repeat_type": RepeatType.WEEKDAYS,
                "repeat_days": None,
                "confidence": weekdays_count / len(first_pattern_dates)
            }

        # Check for weekends pattern
        weekends_count = sum(1 for d in first_pattern_dates if d.weekday() >= 5)
        if weekends_count / len(first_pattern_dates) >= 0.9:
            return {
                "repeat_type": RepeatType.WEEKENDS,
                "repeat_days": None,
                "confidence": weekends_count / len(first_pattern_dates)
            }

        # Check for weekly pattern (same day of week)
        weekdays_in_pattern = set(d.weekday() for d in first_pattern_dates)
        if len(weekdays_in_pattern) <= 3:
            # Custom repeat with specific days
            return {
                "repeat_type": RepeatType.CUSTOM,
                "repeat_days": sorted(list(weekdays_in_pattern)),
                "confidence": len(first_pattern_dates) / (len(weekdays_in_pattern) * (total_days / 7))
            }

        # Default to no repeat
        return {
            "repeat_type": RepeatType.NONE,
            "repeat_days": None,
            "confidence": 0.0
        }

    def _extract_time_patterns(
        self,
        slots: List[ScheduleSlot],
        repeat_info: Dict[str, Any]
    ) -> Dict[tuple, Dict[str, Any]]:
        """
        Extract unique time patterns from slots.

        Args:
            slots: List of schedule slots
            repeat_info: Detected repeat pattern info

        Returns:
            Dict of time patterns keyed by (start_time, end_time)
        """
        time_patterns = {}

        for slot in slots:
            key = (slot.start_time.strftime("%H:%M"), slot.end_time.strftime("%H:%M"))

            if key not in time_patterns:
                time_patterns[key] = {
                    "start_time": key[0],
                    "end_time": key[1],
                    "playlist_id": str(slot.playlist_id) if slot.playlist_id else None,
                    "title": slot.title,
                    "description": slot.description,
                    "color": slot.color,
                    "priority": slot.priority,
                    "repeat_type": repeat_info["repeat_type"].value,
                    "repeat_days": repeat_info.get("repeat_days"),
                }

        return time_patterns

    async def generate_recurring_slots_from_template(
        self,
        channel_id: str,
        template_id: str,
        start_date: date,
        end_date: date,
        user_id: Optional[str] = None
    ) -> int:
        """
        Generate recurring schedule slots from a template.

        Creates ScheduleSlot entries with proper repeat configuration
        (DAILY, WEEKLY, WEEKDAYS, WEEKENDS, CUSTOM) based on the template.

        Args:
            channel_id: Channel ID
            template_id: Template ID
            start_date: Start date for recurrence
            end_date: End date for recurrence
            user_id: Optional user ID

        Returns:
            Number of slots created
        """
        channel_uuid = UUID(channel_id)
        template_uuid = UUID(template_id)

        # Get template
        template = self.db.execute(
            select(ScheduleTemplate).where(
                ScheduleTemplate.id == template_uuid
            )
        ).scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        slots_created = 0

        # Analyze template slots to detect repeat pattern
        repeat_info = self._detect_template_repeat_pattern(template)

        # Create recurring slot based on detected pattern
        for slot_data in template.slots:
            start_time = time.fromisoformat(slot_data["start_time"])
            end_time = time.fromisoformat(slot_data["end_time"])

            # Create slot with repeat configuration
            slot = ScheduleSlot(
                channel_id=channel_uuid,
                playlist_id=UUID(slot_data["playlist_id"]) if slot_data.get("playlist_id") else None,
                start_date=start_date,
                start_time=start_time,
                end_time=end_time,
                title=slot_data.get("title"),
                description=slot_data.get("description"),
                color=slot_data.get("color", "#3B82F6"),
                is_active=True,
                priority=slot_data.get("priority", 5),
                repeat_type=repeat_info["repeat_type"],
                repeat_days=repeat_info.get("repeat_days"),
                repeat_until=end_date,
                created_by=UUID(user_id) if user_id else None
            )

            self.db.add(slot)
            slots_created += 1

        self.db.commit()

        self.logger.info(
            f"Generated {slots_created} recurring slots from template '{template.name}', "
            f"repeat type: {repeat_info['repeat_type'].value}"
        )

        return slots_created

    def _detect_template_repeat_pattern(
        self,
        template: ScheduleTemplate
    ) -> Dict[str, Any]:
        """
        Detect repeat pattern from template slots.

        Args:
            template: ScheduleTemplate to analyze

        Returns:
            Dict with repeat_type and repeat_days
        """
        if not template.slots:
            return {"repeat_type": RepeatType.NONE, "repeat_days": None}

        # Check if template already has repeat information stored
        first_slot = template.slots[0]
        if "repeat_type" in first_slot:
            repeat_type_str = first_slot["repeat_type"]
            try:
                repeat_type = RepeatType(repeat_type_str)
                return {
                    "repeat_type": repeat_type,
                    "repeat_days": first_slot.get("repeat_days")
                }
            except ValueError:
                pass

        # Default to daily for templates without explicit repeat info
        return {
            "repeat_type": RepeatType.DAILY,
            "repeat_days": None
        }

    async def preview_schedule(
        self,
        channel_id: str,
        start_date: date,
        end_date: date,
        use_ai: bool = True,
        redis_client=None
    ) -> List[ScheduleSlotSuggestion]:
        """
        Preview schedule without creating slots.

        Args:
            channel_id: Channel ID
            start_date: Start date
            end_date: End date
            use_ai: Use AI recommendations
            redis_client: Optional Redis client

        Returns:
            List of slot suggestions
        """
        self._init_services(redis_client)

        # Get optimization suggestions
        from src.schemas.schedule_ai import (
            ScheduleOptimizationRequest,
            OptimizationParameters
        )

        request = ScheduleOptimizationRequest(
            channel_id=channel_id,
            start_date=start_date,
            end_date=end_date,
            parameters=OptimizationParameters(
                maximize_engagement=use_ai,
                minimize_gaps=True,
                balance_variety=True,
                respect_priority=True
            )
        )

        suggestions = await self.optimization_service.generate_optimization_suggestions(
            channel_id=channel_id,
            start_date=start_date,
            end_date=end_date,
            parameters=request.parameters
        )

        self.logger.info(f"Generated {len(suggestions)} preview suggestions")

        return suggestions


# ============================================================================
# Celery Task (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='services.auto_pilot.generate_schedule', bind=True, max_retries=3)
    def generate_schedule_task(
        self,
        task_id: str,
        channel_id: str,
        date_range_start: str,
        date_range_end: str,
        template: Optional[Dict[str, Any]] = None,
        fill_gaps: bool = True,
        max_daily_hours: int = 24,
        use_ai_recommendations: bool = True,
        resolve_conflicts: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Celery task: Generate schedule in the background.

        Performs automatic schedule generation including template application,
        gap filling, and conflict resolution.

        Args:
            task_id: Task UUID for tracking
            channel_id: Channel ID to generate schedule for
            date_range_start: Start date (ISO format)
            date_range_end: End date (ISO format)
            template: Optional template dict to apply
            fill_gaps: Whether to fill gaps with recommendations
            max_daily_hours: Maximum hours per day
            use_ai_recommendations: Whether to use AI for recommendations
            resolve_conflicts: Whether to resolve conflicts
            user_id: Optional user ID who initiated generation

        Returns:
            dict with generation results:
            - task_id: str
            - channel_id: str
            - status: str (completed/failed)
            - slots_created: int
            - gaps_filled: int
            - conflicts_resolved: int
            - error_message: str or None
        """
        logger.info(
            f"[worker] generate_schedule_task for {task_id}, "
            f"channel {channel_id}, dates {date_range_start} to {date_range_end}"
        )

        from database import SessionLocal

        db = SessionLocal()
        try:
            # Create service instance
            service = AutoPilotService(db)

            # Build request object
            from src.schemas.schedule_ai import AutoPilotRequest, AutoPilotTemplate

            template_obj = None
            if template:
                template_obj = AutoPilotTemplate(**template)

            request = AutoPilotRequest(
                channel_id=channel_id,
                date_range={"start": date_range_start, "end": date_range_end},
                template=template_obj,
                fill_gaps=fill_gaps,
                max_daily_hours=max_daily_hours,
                use_ai_recommendations=use_ai_recommendations,
                resolve_conflicts=resolve_conflicts
            )

            # Run async generation in sync context
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    service.generate_schedule(request, user_id)
                )
            finally:
                loop.close()

            # Return result as dict
            return {
                "task_id": task_id,
                "channel_id": response.channel_id,
                "status": response.status,
                "date_range": response.date_range,
                "slots_created": response.slots_created,
                "gaps_filled": response.gaps_filled,
                "conflicts_resolved": response.conflicts_resolved,
                "error_message": response.error_message,
            }

        except Exception as e:
            logger.exception(f"Error in generate_schedule_task for {task_id}")
            # Retry on temporary errors
            error_msg = str(e).lower()
            if any(err in error_msg for err in ["timeout", "network", "connection", "database"]):
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            return {
                "task_id": task_id,
                "channel_id": channel_id,
                "status": "failed",
                "date_range": {"start": date_range_start, "end": date_range_end},
                "slots_created": 0,
                "gaps_filled": 0,
                "conflicts_resolved": 0,
                "error_message": str(e),
            }

        finally:
            db.close()

    @celery_app.task(name='services.auto_pilot.fill_gaps', bind=True, max_retries=3)
    def fill_gaps_task(
        self,
        channel_id: str,
        date_range_start: str,
        date_range_end: str,
        max_daily_hours: int = 24,
        use_ai_recommendations: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Celery task: Auto-fill schedule gaps in the background.

        Detects gaps in the schedule and fills them with optimal content
        based on engagement data and AI recommendations.

        Args:
            channel_id: Channel ID to fill gaps for
            date_range_start: Start date (ISO format)
            date_range_end: End date (ISO format)
            max_daily_hours: Maximum hours per day (default: 24)
            use_ai_recommendations: Whether to use AI for recommendations (default: True)
            user_id: Optional user ID who initiated the task

        Returns:
            dict with gap filling results:
            - channel_id: str
            - date_range: dict with start/end dates
            - status: str (completed/failed)
            - gaps_filled: int
            - total_gap_hours: float
            - error_message: str or None
        """
        logger.info(
            f"[worker] fill_gaps_task for channel {channel_id}, "
            f"dates {date_range_start} to {date_range_end}"
        )

        from database import SessionLocal

        db = SessionLocal()
        try:
            # Create service instance and initialize dependencies
            service = AutoPilotService(db)
            service._init_services()

            # Parse dates
            start_date = date.fromisoformat(date_range_start)
            end_date = date.fromisoformat(date_range_end)

            # Run gap filling in sync context
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                gaps_filled = loop.run_until_complete(
                    service._fill_gaps_with_recommendations(
                        channel_id,
                        start_date,
                        end_date,
                        max_daily_hours,
                        use_ai_recommendations,
                        user_id
                    )
                )
            finally:
                loop.close()

            # Calculate total gap hours for reporting
            total_gap_hours = 0.0
            try:
                from src.schemas.schedule_ai import GapDetectionRequest
                gap_request = GapDetectionRequest(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    consider_peak_hours=True
                )
                gaps_response = loop.run_until_complete(
                    service.optimization_service.detect_gaps(gap_request)
                )
                if gaps_response.gaps:
                    total_gap_hours = sum(g.duration_hours for g in gaps_response.gaps)
            except Exception as e:
                logger.warning(f"Could not calculate total gap hours: {e}")

            logger.info(
                f"fill_gaps_task completed: {gaps_filled} gaps filled, "
                f"{total_gap_hours:.1f} total gap hours"
            )

            return {
                "channel_id": channel_id,
                "date_range": {"start": date_range_start, "end": date_range_end},
                "status": "completed",
                "gaps_filled": gaps_filled,
                "total_gap_hours": total_gap_hours,
                "error_message": None,
            }

        except Exception as e:
            logger.exception(f"Error in fill_gaps_task for channel {channel_id}")
            # Retry on temporary errors
            error_msg = str(e).lower()
            if any(err in error_msg for err in ["timeout", "network", "connection", "database"]):
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            return {
                "channel_id": channel_id,
                "date_range": {"start": date_range_start, "end": date_range_end},
                "status": "failed",
                "gaps_filled": 0,
                "total_gap_hours": 0.0,
                "error_message": str(e),
            }

        finally:
            db.close()


def get_auto_pilot_service(db: Session) -> AutoPilotService:
    """
    Factory for creating auto-pilot service.

    Args:
        db: SQLAlchemy database session

    Returns:
        AutoPilotService instance
    """
    return AutoPilotService(db)
