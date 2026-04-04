"""
Report Service
Feature: 012-comprehensive-analytics-dashboard

Сервис для генерации отчетов в формате CSV:
- Сводные отчеты
- Отчеты по истории слушателей
- Отчеты по топ трекам
- Отчеты по вовлеченности
- Отчеты по производительности потока
- Отчеты по контенту и точкам отказа
"""

import csv
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List
from io import StringIO

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from src.models.analytics import TrackPlay, MonthlyAnalytics
from src.models.playlist import PlaylistItem
from src.models.engagement import EngagementEvent
from src.models.stream_quality import StreamQualityHistory
from src.models.viewer_session import ViewerSession
from src.schemas.analytics import (
    AnalyticsPeriod,
    ListenerHistoryPoint,
    TopTrackItem,
    EngagementTrendPoint,
    ActiveUserItem,
    QualityTrendPoint,
    QualityDistributionItem,
    ContentPerformanceItem,
    DropOffPoint,
)

from src.services.analytics_service import _period_to_days

logger = logging.getLogger(__name__)


class ReportService:
    """
    Сервис генерации отчетов.

    Методы:
    - generate_summary_report: Сводный отчет
    - generate_listener_history_report: История слушателей
    - generate_top_tracks_report: Топ треков
    - generate_engagement_report: Метрики вовлеченности
    - generate_stream_performance_report: Производительность потока
    - generate_content_insights_report: Аналитика контента
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
        """
        self.db = db

    def _get_period_filter(self, period: AnalyticsPeriod) -> Optional[datetime]:
        """
        Получение фильтра по времени для периода.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            Datetime или None для всех данных
        """
        days = _period_to_days(period)
        if days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=days)

    def _write_csv_header(self, writer: csv.DictWriter, headers: List[str]) -> None:
        """
        Запись заголовков CSV.

        Args:
            writer: CSV DictWriter
            headers: Список заголовков
        """
        writer.writerow({h: h for h in headers})

    async def generate_summary_report(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> str:
        """
        Генерация сводного отчета в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating summary report for period: {period}")

        period_start = self._get_period_filter(period)
        base_filter = TrackPlay.played_at >= period_start if period_start else True

        # Сбор данных
        total_plays = self.db.execute(
            select(func.count(TrackPlay.id)).where(base_filter)
        ).scalar() or 0

        total_seconds = self.db.execute(
            select(func.sum(TrackPlay.duration_seconds)).where(base_filter)
        ).scalar() or 0

        unique_tracks = self.db.execute(
            select(func.count(func.distinct(TrackPlay.playlist_item_id))).where(base_filter)
        ).scalar() or 0

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        current = self.db.execute(
            select(TrackPlay.listeners_count)
            .order_by(desc(TrackPlay.played_at))
            .limit(1)
        ).scalar() or 0

        peak_today = self.db.execute(
            select(func.max(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= today_start)
        ).scalar() or 0

        peak_week = self.db.execute(
            select(func.max(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= week_ago)
        ).scalar() or 0

        avg_week = self.db.execute(
            select(func.avg(TrackPlay.listeners_count))
            .where(TrackPlay.played_at >= week_ago)
        ).scalar() or 0.0

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "metric",
            "value",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        writer.writerow({
            "metric": "Total Plays",
            "value": total_plays,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Total Duration (hours)",
            "value": round(total_seconds / 3600, 2),
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Unique Tracks",
            "value": unique_tracks,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Current Listeners",
            "value": current,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Peak Today",
            "value": peak_today,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Peak Week",
            "value": peak_week,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "metric": "Average Week",
            "value": round(float(avg_week), 2),
            "period": period,
            "generated_at": generated_at
        })

        csv_data = output.getvalue()
        logger.info(f"Summary report generated: {len(csv_data)} bytes")
        return csv_data

    async def generate_listener_history_report(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> str:
        """
        Генерация отчета по истории слушателей в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating listener history report for period: {period}")

        period_start = self._get_period_filter(period)

        time_trunc = func.date_trunc('day', TrackPlay.played_at)

        query = select(
            time_trunc.label('timestamp'),
            func.avg(TrackPlay.listeners_count).label('avg_count')
        ).group_by(time_trunc).order_by(time_trunc)

        if period_start:
            query = query.where(TrackPlay.played_at >= period_start)

        rows = self.db.execute(query).fetchall()

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "date",
            "average_listeners",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        for row in rows:
            writer.writerow({
                "date": row.timestamp.strftime("%Y-%m-%d") if row.timestamp else "",
                "average_listeners": round(row.avg_count) if row.avg_count else 0,
                "period": period,
                "generated_at": generated_at
            })

        csv_data = output.getvalue()
        logger.info(f"Listener history report generated: {len(csv_data)} bytes, {len(rows)} rows")
        return csv_data

    async def generate_top_tracks_report(
        self,
        period: AnalyticsPeriod = "7d",
        limit: int = 10
    ) -> str:
        """
        Генерация отчета по топ трекам в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)
            limit: Количество треков

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating top tracks report for period: {period}, limit: {limit}")

        period_start = self._get_period_filter(period)

        query = (
            select(
                TrackPlay.playlist_item_id,
                PlaylistItem.title,
                func.count(TrackPlay.id).label('play_count'),
                func.sum(TrackPlay.duration_seconds).label('total_duration')
            )
            .join(PlaylistItem, TrackPlay.playlist_item_id == PlaylistItem.id)
            .group_by(TrackPlay.playlist_item_id, PlaylistItem.title)
            .order_by(desc('play_count'))
            .limit(limit)
        )

        if period_start:
            query = query.where(TrackPlay.played_at >= period_start)

        rows = self.db.execute(query).fetchall()

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "rank",
            "title",
            "play_count",
            "total_duration_seconds",
            "total_duration_minutes",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        for idx, row in enumerate(rows, start=1):
            total_duration_seconds = row.total_duration or 0
            writer.writerow({
                "rank": idx,
                "title": row.title or "Unknown",
                "play_count": row.play_count,
                "total_duration_seconds": total_duration_seconds,
                "total_duration_minutes": round(total_duration_seconds / 60, 2),
                "period": period,
                "generated_at": generated_at
            })

        csv_data = output.getvalue()
        logger.info(f"Top tracks report generated: {len(csv_data)} bytes, {len(rows)} rows")
        return csv_data

    async def generate_engagement_report(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> str:
        """
        Генерация отчета по вовлеченности в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating engagement report for period: {period}")

        period_start = self._get_period_filter(period)
        base_filter = EngagementEvent.event_timestamp >= period_start if period_start else True

        # Агрегированные метрики
        total_messages = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "chat_message"))
        ).scalar() or 0

        total_reactions = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "reaction"))
        ).scalar() or 0

        total_comments = self.db.execute(
            select(func.count(EngagementEvent.id))
            .where(and_(base_filter, EngagementEvent.event_type == "comment"))
        ).scalar() or 0

        unique_users = self.db.execute(
            select(func.count(func.distinct(EngagementEvent.user_id))).where(base_filter)
        ).scalar() or 0

        # Топ пользователей
        top_users_query = (
            select(
                EngagementEvent.user_id,
                EngagementEvent.username,
                func.sum(func.case((EngagementEvent.event_type == "chat_message", 1), else_=0)).label('message_count'),
                func.sum(func.case((EngagementEvent.event_type == "reaction", 1), else_=0)).label('reaction_count'),
                func.max(EngagementEvent.event_timestamp).label('last_activity')
            )
            .where(base_filter)
            .group_by(EngagementEvent.user_id, EngagementEvent.username)
            .order_by(desc('message_count'))
            .limit(10)
        )
        top_users_rows = self.db.execute(top_users_query).fetchall()

        # Данные по времени
        time_trunc = func.date_trunc('day', EngagementEvent.event_timestamp)
        engagement_query = select(
            time_trunc.label('timestamp'),
            func.sum(func.case((EngagementEvent.event_type == "chat_message", 1), else_=0)).label('message_count'),
            func.sum(func.case((EngagementEvent.event_type == "reaction", 1), else_=0)).label('reaction_count'),
            func.count(func.distinct(EngagementEvent.user_id)).label('unique_users')
        ).where(base_filter).group_by(time_trunc).order_by(time_trunc)

        engagement_rows = self.db.execute(engagement_query).fetchall()

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "section",
            "date",
            "metric",
            "value",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        # Сводные метрики
        writer.writerow({
            "section": "summary",
            "date": "",
            "metric": "Total Messages",
            "value": total_messages,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "date": "",
            "metric": "Total Reactions",
            "value": total_reactions,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "date": "",
            "metric": "Total Comments",
            "value": total_comments,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "date": "",
            "metric": "Unique Users",
            "value": unique_users,
            "period": period,
            "generated_at": generated_at
        })

        # Топ пользователей
        for row in top_users_rows:
            writer.writerow({
                "section": "top_users",
                "date": "",
                "metric": f"User: {row.username or 'Unknown'}",
                "value": f"Messages: {row.message_count or 0}, Reactions: {row.reaction_count or 0}",
                "period": period,
                "generated_at": generated_at
            })

        # Вовлеченность по времени
        for row in engagement_rows:
            date_str = row.timestamp.strftime("%Y-%m-%d") if row.timestamp else ""
            writer.writerow({
                "section": "daily",
                "date": date_str,
                "metric": "Messages",
                "value": row.message_count or 0,
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "daily",
                "date": date_str,
                "metric": "Reactions",
                "value": row.reaction_count or 0,
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "daily",
                "date": date_str,
                "metric": "Unique Users",
                "value": row.unique_users or 0,
                "period": period,
                "generated_at": generated_at
            })

        csv_data = output.getvalue()
        logger.info(f"Engagement report generated: {len(csv_data)} bytes")
        return csv_data

    async def generate_stream_performance_report(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> str:
        """
        Генерация отчета по производительности потока в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating stream performance report for period: {period}")

        period_start = self._get_period_filter(period)
        base_filter = StreamQualityHistory.analyzed_at >= period_start if period_start else True

        # Метрики производительности
        total_records = self.db.execute(
            select(func.count(StreamQualityHistory.id)).where(base_filter)
        ).scalar() or 0

        successful_records = self.db.execute(
            select(func.count(StreamQualityHistory.id))
            .where(and_(base_filter, StreamQualityHistory.success == True))
        ).scalar() or 0

        uptime_percentage = round((successful_records / total_records * 100), 2) if total_records > 0 else 100.0

        avg_buffering = self.db.execute(
            select(func.avg(StreamQualityHistory.buffering_percentage))
            .where(and_(base_filter, StreamQualityHistory.buffering_percentage.isnot(None)))
        ).scalar() or 0.0

        # Распределение по качеству
        quality_dist_query = select(
            StreamQualityHistory.overall_quality,
            func.count(StreamQualityHistory.id).label('count')
        ).where(base_filter).group_by(StreamQualityHistory.overall_quality)

        quality_dist_rows = self.db.execute(quality_dist_query).fetchall()

        # Данные по времени
        time_trunc = func.date_trunc('hour', StreamQualityHistory.analyzed_at)
        quality_query = select(
            time_trunc.label('timestamp'),
            func.max(StreamQualityHistory.overall_quality).label('overall_quality'),
            func.avg(StreamQualityHistory.audio_bitrate_kbps).label('audio_bitrate_kbps'),
            func.avg(StreamQualityHistory.video_bitrate_kbps).label('video_bitrate_kbps'),
            func.avg(StreamQualityHistory.buffering_percentage).label('buffering_percentage')
        ).where(base_filter).group_by(time_trunc).order_by(time_trunc)

        quality_rows = self.db.execute(quality_query).fetchall()

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "section",
            "timestamp",
            "metric",
            "value",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        # Сводные метрики
        writer.writerow({
            "section": "summary",
            "timestamp": "",
            "metric": "Uptime Percentage",
            "value": f"{uptime_percentage}%",
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "timestamp": "",
            "metric": "Total Records",
            "value": total_records,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "timestamp": "",
            "metric": "Average Buffering Percentage",
            "value": f"{round(float(avg_buffering), 2)}%",
            "period": period,
            "generated_at": generated_at
        })

        # Распределение по качеству
        for row in quality_dist_rows:
            percentage = round(row.count / total_records * 100, 2) if total_records > 0 else 0.0
            writer.writerow({
                "section": "quality_distribution",
                "timestamp": "",
                "metric": f"Quality: {row.overall_quality}",
                "value": f"{row.count} ({percentage}%)",
                "period": period,
                "generated_at": generated_at
            })

        # Данные по времени
        for row in quality_rows:
            timestamp_str = row.timestamp.strftime("%Y-%m-%d %H:00") if row.timestamp else ""

            writer.writerow({
                "section": "hourly",
                "timestamp": timestamp_str,
                "metric": "Overall Quality",
                "value": row.overall_quality or "unknown",
                "period": period,
                "generated_at": generated_at
            })

            if row.audio_bitrate_kbps:
                writer.writerow({
                    "section": "hourly",
                    "timestamp": timestamp_str,
                    "metric": "Audio Bitrate (kbps)",
                    "value": round(row.audio_bitrate_kbps),
                    "period": period,
                    "generated_at": generated_at
                })

            if row.video_bitrate_kbps:
                writer.writerow({
                    "section": "hourly",
                    "timestamp": timestamp_str,
                    "metric": "Video Bitrate (kbps)",
                    "value": round(row.video_bitrate_kbps),
                    "period": period,
                    "generated_at": generated_at
                })

            if row.buffering_percentage:
                writer.writerow({
                    "section": "hourly",
                    "timestamp": timestamp_str,
                    "metric": "Buffering Percentage",
                    "value": f"{round(row.buffering_percentage, 2)}%",
                    "period": period,
                    "generated_at": generated_at
                })

        csv_data = output.getvalue()
        logger.info(f"Stream performance report generated: {len(csv_data)} bytes")
        return csv_data

    async def generate_content_insights_report(
        self,
        period: AnalyticsPeriod = "7d"
    ) -> str:
        """
        Генерация отчета по аналитике контента в формате CSV.

        Args:
            period: Период данных (7d, 30d, 90d, all)

        Returns:
            CSV данные в виде строки
        """
        logger.info(f"Generating content insights report for period: {period}")

        period_start = self._get_period_filter(period)
        base_filter = ViewerSession.started_at >= period_start if period_start else True

        # Самый просматриваемый контент
        content_query = (
            select(
                PlaylistItem.id.label('content_id'),
                PlaylistItem.title,
                func.count(ViewerSession.id).label('total_views'),
                func.avg(ViewerSession.completion_percentage).label('avg_completion'),
                func.sum(ViewerSession.drop_off_position_seconds).label('total_watch_time'),
                func.avg(ViewerSession.drop_off_position_seconds).label('avg_duration')
            )
            .join(ViewerSession, ViewerSession.playlist_item_id == PlaylistItem.id)
            .where(base_filter)
            .group_by(PlaylistItem.id, PlaylistItem.title)
            .order_by(desc('total_views'))
            .limit(10)
        )

        content_rows = self.db.execute(content_query).fetchall()

        # Точки отказа
        interval_seconds = 10

        drop_off_query = select(
            (func.floor(ViewerSession.drop_off_position_seconds / interval_seconds) * interval_seconds).label('position_seconds'),
            func.count(ViewerSession.id).label('viewers_count')
        ).where(
            and_(base_filter, ViewerSession.drop_off_position_seconds.isnot(None))
        ).group_by(
            (func.floor(ViewerSession.drop_off_position_seconds / interval_seconds) * interval_seconds)
        ).order_by('position_seconds')

        drop_off_rows = self.db.execute(drop_off_query).fetchall()

        total_sessions = sum(row.viewers_count for row in drop_off_rows) or 1

        # Средние метрики
        avg_completion = self.db.execute(
            select(func.avg(ViewerSession.completion_percentage))
            .where(and_(base_filter, ViewerSession.completion_percentage.isnot(None)))
        ).scalar() or 0.0

        total_sessions_count = self.db.execute(
            select(func.count(ViewerSession.id)).where(base_filter)
        ).scalar() or 0

        avg_session_duration = self.db.execute(
            select(func.avg(ViewerSession.drop_off_position_seconds))
            .where(and_(base_filter, ViewerSession.drop_off_position_seconds.isnot(None)))
        ).scalar() or 0.0

        # Генерация CSV
        output = StringIO()
        fieldnames = [
            "section",
            "content",
            "metric",
            "value",
            "period",
            "generated_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        generated_at = datetime.now(timezone.utc).isoformat()

        # Сводные метрики
        writer.writerow({
            "section": "summary",
            "content": "",
            "metric": "Total Sessions",
            "value": total_sessions_count,
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "content": "",
            "metric": "Average Completion Rate",
            "value": f"{round(float(avg_completion), 2)}%",
            "period": period,
            "generated_at": generated_at
        })

        writer.writerow({
            "section": "summary",
            "content": "",
            "metric": "Average Session Duration (seconds)",
            "value": round(float(avg_session_duration), 2),
            "period": period,
            "generated_at": generated_at
        })

        # Самый просматриваемый контент
        for row in content_rows:
            title = row.title or "Unknown"
            writer.writerow({
                "section": "most_watched",
                "content": title,
                "metric": "Total Views",
                "value": row.total_views or 0,
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "most_watched",
                "content": title,
                "metric": "Average Completion Percentage",
                "value": f"{round(float(row.avg_completion or 0), 2)}%",
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "most_watched",
                "content": title,
                "metric": "Total Watch Time (minutes)",
                "value": round((row.total_watch_time or 0) / 60, 2),
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "most_watched",
                "content": title,
                "metric": "Average Duration (seconds)",
                "value": round(float(row.avg_duration or 0), 2),
                "period": period,
                "generated_at": generated_at
            })

        # Точки отказа
        cumulative_drop_off = 0.0
        for row in drop_off_rows:
            percentage = round(row.viewers_count / total_sessions * 100, 2)
            cumulative_drop_off += percentage

            position_minutes = int(row.position_seconds // 60)
            position_seconds = int(row.position_seconds % 60)

            writer.writerow({
                "section": "drop_off_points",
                "content": f"{position_minutes}m {position_seconds}s",
                "metric": "Viewers Count",
                "value": row.viewers_count,
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "drop_off_points",
                "content": f"{position_minutes}m {position_seconds}s",
                "metric": "Percentage",
                "value": f"{percentage}%",
                "period": period,
                "generated_at": generated_at
            })

            writer.writerow({
                "section": "drop_off_points",
                "content": f"{position_minutes}m {position_seconds}s",
                "metric": "Cumulative Drop-off",
                "value": f"{round(min(cumulative_drop_off, 100.0), 2)}%",
                "period": period,
                "generated_at": generated_at
            })

        csv_data = output.getvalue()
        logger.info(f"Content insights report generated: {len(csv_data)} bytes")
        return csv_data


def get_report_service(db: Session) -> ReportService:
    """
    Фабрика для создания сервиса отчетов.

    Args:
        db: SQLAlchemy сессия

    Returns:
        ReportService instance
    """
    return ReportService(db=db)
