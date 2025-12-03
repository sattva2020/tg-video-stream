"""
SchedulerService for scheduled playlist automation.

Features:
- APScheduler-based scheduling
- Persists across restarts via database
- Supports daily/weekly recurrence
- Timezone-aware scheduling
- Automatic trigger on schedule

External Library: APScheduler 3.10+
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from src.models import ScheduledPlaylist


logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled playlist playback."""
    
    def __init__(self, db_session: Session):
        """
        Initialize scheduler service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logger
        
        # Initialize APScheduler
        self.scheduler = BackgroundScheduler()
        self._jobs = {}  # Map of scheduled_id -> job_id
    
    def start(self) -> None:
        """Start the background scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self._restore_schedules()
            self.logger.info("Scheduler started and schedules restored")
    
    def stop(self) -> None:
        """Stop the background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")
    
    def create_schedule(
        self,
        playlist_id: int,
        schedule_time: str,
        name: str,
        days_of_week: Optional[List[int]] = None,
        timezone: str = "UTC",
        description: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> ScheduledPlaylist:
        """
        Create new schedule.
        
        Args:
            playlist_id: Playlist identifier
            schedule_time: Time in HH:MM format
            name: Schedule name
            days_of_week: List of days (0-6 = Mon-Sun)
            timezone: Timezone name
            description: Optional description
            created_by: Admin user ID
            
        Returns:
            Created ScheduledPlaylist object
        """
        if days_of_week is None:
            days_of_week = list(range(7))  # All days
        
        schedule = ScheduledPlaylist(
            playlist_id=playlist_id,
            schedule_time=schedule_time,
            name=name,
            days_of_week=days_of_week,
            timezone=timezone,
            description=description,
            created_by=created_by,
            is_active=True
        )
        
        self.db.add(schedule)
        self.db.commit()
        
        # Schedule in APScheduler
        self._schedule_job(schedule)
        
        self.logger.info(f"Schedule created: {name} at {schedule_time}")
        
        return schedule
    
    def get_schedule(self, schedule_id: int) -> Optional[ScheduledPlaylist]:
        """Get schedule by ID."""
        return self.db.query(ScheduledPlaylist).filter(
            ScheduledPlaylist.id == schedule_id
        ).first()
    
    def get_all_schedules(self, active_only: bool = True) -> List[ScheduledPlaylist]:
        """Get all schedules."""
        query = self.db.query(ScheduledPlaylist)
        
        if active_only:
            query = query.filter(ScheduledPlaylist.is_active == True)
        
        return query.order_by(ScheduledPlaylist.schedule_time).all()
    
    def update_schedule(self, schedule_id: int, **kwargs) -> Optional[ScheduledPlaylist]:
        """
        Update schedule properties.
        
        Args:
            schedule_id: Schedule identifier
            **kwargs: Fields to update (schedule_time, days_of_week, etc.)
            
        Returns:
            Updated ScheduledPlaylist object or None if not found
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        self.db.commit()
        
        # Re-schedule job if timing changed
        if "schedule_time" in kwargs or "days_of_week" in kwargs:
            self._reschedule_job(schedule)
        
        self.logger.info(f"Schedule updated: {schedule.name}")
        
        return schedule
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """
        Delete schedule (soft delete by marking inactive).
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            True if schedule was found and deleted
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.is_active = False
        self.db.commit()
        
        # Remove from scheduler
        self._unschedule_job(schedule)
        
        self.logger.info(f"Schedule deleted: {schedule.name}")
        
        return True
    
    def _schedule_job(self, schedule: ScheduledPlaylist) -> str:
        """
        Add job to APScheduler.
        
        Args:
            schedule: ScheduledPlaylist object
            
        Returns:
            APScheduler job ID
        """
        hour, minute = schedule.schedule_time.split(":")
        
        # Build day_of_week string for CronTrigger (0-6 = Mon-Sun)
        days = ",".join(str(d) for d in schedule.days_of_week)
        
        trigger = CronTrigger(
            hour=int(hour),
            minute=int(minute),
            day_of_week=days,
            timezone=schedule.timezone
        )
        
        job = self.scheduler.add_job(
            self._trigger_playlist,
            trigger=trigger,
            args=[schedule.id],
            id=f"schedule_{schedule.id}"
        )
        
        self._jobs[schedule.id] = job.id
        
        self.logger.debug(f"Job scheduled: {schedule.name} -> {job.id}")
        
        return job.id
    
    def _reschedule_job(self, schedule: ScheduledPlaylist) -> None:
        """Re-schedule existing job."""
        self._unschedule_job(schedule)
        self._schedule_job(schedule)
    
    def _unschedule_job(self, schedule: ScheduledPlaylist) -> None:
        """Remove job from scheduler."""
        if schedule.id in self._jobs:
            job_id = self._jobs[schedule.id]
            self.scheduler.remove_job(job_id)
            del self._jobs[schedule.id]
    
    def _trigger_playlist(self, schedule_id: int) -> None:
        """
        Trigger playlist playback (called by scheduler).
        
        Args:
            schedule_id: Schedule identifier
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return
        
        # Update statistics
        schedule.last_triggered = datetime.utcnow()
        schedule.trigger_count += 1
        self.db.commit()
        
        # TODO: Implement actual playlist trigger
        # This would call playback service to start the playlist
        
        self.logger.info(f"Schedule triggered: {schedule.name} (playlist {schedule.playlist_id})")
    
    def _restore_schedules(self) -> None:
        """Restore active schedules from database on startup."""
        schedules = self.get_all_schedules(active_only=True)
        
        for schedule in schedules:
            self._schedule_job(schedule)
        
        self.logger.info(f"Restored {len(schedules)} schedules from database")
