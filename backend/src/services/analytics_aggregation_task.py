"""
Celery tasks для агрегации аналитики с платформ стриминга.

Включает:
- Периодический сбор почасовой статистики
- Периодический сбор ежедневной статистики
- Агрегация метрик с нескольких платформ
"""
import os
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Lazy Celery import
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False


def _get_celery_app():
    """Получает или создаёт Celery приложение."""
    broker = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
    celery_app = _get_celery_app()

    @celery_app.task(name='backend.src.services.analytics_aggregation_task.aggregate_hourly_stats', bind=True, max_retries=3)
    def aggregate_hourly_stats_task(self, channel_id: Optional[str] = None):
        """
        Celery task: собирает почасовую статистику со всех платформ.

        Эта задача должна вызываться каждый час для обновления агрегированной
        статистики по стримам, просмотрам, сообщениям чата и другим метрикам.

        Args:
            channel_id: Опциональный ID канала. Если не указан, агрегируются
                       данные для всех активных каналов.

        Returns:
            dict с результатом агрегации (success, channels_processed, total_streams)
        """
        logger.info(f"[worker] aggregate_hourly_stats_task for channel {channel_id or 'all'}")

        try:
            from database import SessionLocal
            from src.models.telegram import Channel
            from src.models.streaming_platform import StreamingPlatform
            from src.models.broadcast_destination import BroadcastDestination
            from src.services.analytics_service import AnalyticsService
            from src.services.multi_platform_analytics import MultiPlatformAnalyticsService
            import asyncio

            db = SessionLocal()
            try:
                # Определяем список каналов для обработки
                if channel_id:
                    channels = db.query(Channel).filter(
                        Channel.id == channel_id,
                        Channel.is_active == True
                    ).all()
                else:
                    # Получаем все активные каналы
                    channels = db.query(Channel).filter(
                        Channel.is_active == True
                    ).all()

                if not channels:
                    logger.info(f"No active channels found for hourly analytics aggregation")
                    return {
                        "success": True,
                        "channels_processed": 0,
                        "total_streams": 0
                    }

                channels_processed = 0
                total_streams = 0

                # Создаем сервис аналитики
                analytics_service = AnalyticsService(db)
                multi_platform_service = MultiPlatformAnalyticsService(db)

                # Запускаем асинхронный код в синхронном контексте
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    for channel in channels:
                        try:
                            # Получаем активные платформы для этого канала
                            destinations = db.query(BroadcastDestination).filter(
                                BroadcastDestination.channel_id == channel.id,
                                BroadcastDestination.enabled == True
                            ).all()

                            if not destinations:
                                logger.debug(f"No broadcast destinations for channel {channel.id}")
                                continue

                            # Подсчитываем количество стримов за последний час
                            from src.models.analytics import StreamSession
                            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

                            stream_count = db.query(StreamSession).filter(
                                StreamSession.channel_id == channel.id,
                                StreamSession.created_at >= one_hour_ago
                            ).count()

                            total_streams += stream_count
                            channels_processed += 1

                            logger.debug(
                                f"Aggregated hourly stats for channel {channel.id}: "
                                f"{stream_count} streams"
                            )

                        except Exception as e:
                            logger.error(
                                f"Error aggregating hourly stats for channel {channel.id}: {str(e)}"
                            )
                            # Продолжаем обработку остальных каналов
                            continue

                    logger.info(
                        f"Hourly analytics aggregation completed: {channels_processed} channels, "
                        f"{total_streams} total streams"
                    )

                    return {
                        "success": True,
                        "channels_processed": channels_processed,
                        "total_streams": total_streams
                    }

                finally:
                    loop.close()

            except Exception as e:
                logger.exception(f"Error in aggregate_hourly_stats_task")
                raise self.retry(exc=e, countdown=60)
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Unhandled error in aggregate_hourly_stats_task")
            raise self.retry(exc=e, countdown=60)


    @celery_app.task(name='backend.src.services.analytics_aggregation_task.aggregate_daily_stats', bind=True, max_retries=3)
    def aggregate_daily_stats_task(self, channel_id: Optional[str] = None):
        """
        Celery task: собирает ежедневную статистику со всех платформ.

        Эта задача должна вызываться каждый день (в 2 AM) для обновления
        суточной агрегированной статистики.

        Args:
            channel_id: Опциональный ID канала. Если не указан, агрегируются
                       данные для всех активных каналов.

        Returns:
            dict с результатом агрегации (success, channels_processed, total_stream_hours)
        """
        logger.info(f"[worker] aggregate_daily_stats_task for channel {channel_id or 'all'}")

        try:
            from database import SessionLocal
            from src.models.telegram import Channel
            from src.models.streaming_platform import StreamingPlatform
            from src.models.broadcast_destination import BroadcastDestination
            from src.services.analytics_service import AnalyticsService
            from src.services.multi_platform_analytics import MultiPlatformAnalyticsService
            import asyncio

            db = SessionLocal()
            try:
                # Определяем список каналов для обработки
                if channel_id:
                    channels = db.query(Channel).filter(
                        Channel.id == channel_id,
                        Channel.is_active == True
                    ).all()
                else:
                    # Получаем все активные каналы
                    channels = db.query(Channel).filter(
                        Channel.is_active == True
                    ).all()

                if not channels:
                    logger.info(f"No active channels found for daily analytics aggregation")
                    return {
                        "success": True,
                        "channels_processed": 0,
                        "total_stream_hours": 0
                    }

                channels_processed = 0
                total_stream_hours = 0

                # Создаем сервис аналитики
                analytics_service = AnalyticsService(db)
                multi_platform_service = MultiPlatformAnalyticsService(db)

                # Запускаем асинхронный код в синхронном контексте
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    for channel in channels:
                        try:
                            # Получаем активные платформы для этого канала
                            destinations = db.query(BroadcastDestination).filter(
                                BroadcastDestination.channel_id == channel.id,
                                BroadcastDestination.enabled == True
                            ).all()

                            if not destinations:
                                logger.debug(f"No broadcast destinations for channel {channel.id}")
                                continue

                            # Подсчитываем количество часов стримов за последний день
                            from src.models.analytics import StreamSession
                            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

                            streams = db.query(StreamSession).filter(
                                StreamSession.channel_id == channel.id,
                                StreamSession.created_at >= one_day_ago
                            ).all()

                            # Вычисляем общее количество часов стримов
                            stream_hours = sum([
                                (s.ended_at - s.created_at).total_seconds() / 3600
                                if s.ended_at else 0
                                for s in streams
                            ])

                            total_stream_hours += stream_hours
                            channels_processed += 1

                            logger.debug(
                                f"Aggregated daily stats for channel {channel.id}: "
                                f"{stream_hours:.2f} stream hours"
                            )

                        except Exception as e:
                            logger.error(
                                f"Error aggregating daily stats for channel {channel.id}: {str(e)}"
                            )
                            # Продолжаем обработку остальных каналов
                            continue

                    logger.info(
                        f"Daily analytics aggregation completed: {channels_processed} channels, "
                        f"{total_stream_hours:.2f} total stream hours"
                    )

                    return {
                        "success": True,
                        "channels_processed": channels_processed,
                        "total_stream_hours": round(total_stream_hours, 2)
                    }

                finally:
                    loop.close()

            except Exception as e:
                logger.exception(f"Error in aggregate_daily_stats_task")
                raise self.retry(exc=e, countdown=60)
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Unhandled error in aggregate_daily_stats_task")
            raise self.retry(exc=e, countdown=60)


# ============================================================================
# Public API
# ============================================================================

def aggregate_hourly_stats(channel_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронную агрегацию почасовой статистики.

    Использует Celery если доступен, otherwise выполняет синхронно.

    Args:
        channel_id: Опциональный ID канала для агрегации

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task(
                'backend.src.services.analytics_aggregation_task.aggregate_hourly_stats',
                args=[channel_id] if channel_id else []
            )
            logger.info(f"Enqueued hourly analytics aggregation for channel {channel_id or 'all'}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Aggregating hourly stats synchronously for channel {channel_id or 'all'}")
    try:
        from database import SessionLocal
        from src.models.telegram import Channel
        import asyncio

        db = SessionLocal()
        try:
            if channel_id:
                channels = db.query(Channel).filter(
                    Channel.id == channel_id,
                    Channel.is_active == True
                ).all()
            else:
                channels = db.query(Channel).filter(
                    Channel.is_active == True
                ).all()

            if not channels:
                return True

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for channel in channels:
                    try:
                        # Simple aggregation - just query the data
                        from src.models.analytics import StreamSession
                        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                        stream_count = db.query(StreamSession).filter(
                            StreamSession.channel_id == channel.id,
                            StreamSession.created_at >= one_hour_ago
                        ).count()
                        logger.debug(f"Channel {channel.id}: {stream_count} streams in last hour")
                    except Exception as e:
                        logger.error(f"Error aggregating for channel {channel.id}: {e}")
                        continue
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.exception("Failed to aggregate hourly stats synchronously")
            return False
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to aggregate hourly stats")
        return False


def aggregate_daily_stats(channel_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронную агрегацию ежедневной статистики.

    Args:
        channel_id: Опциональный ID канала для агрегации

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task(
                'backend.src.services.analytics_aggregation_task.aggregate_daily_stats',
                args=[channel_id] if channel_id else []
            )
            logger.info(f"Enqueued daily analytics aggregation for channel {channel_id or 'all'}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Aggregating daily stats synchronously for channel {channel_id or 'all'}")
    try:
        from database import SessionLocal
        from src.models.telegram import Channel
        import asyncio

        db = SessionLocal()
        try:
            if channel_id:
                channels = db.query(Channel).filter(
                    Channel.id == channel_id,
                    Channel.is_active == True
                ).all()
            else:
                channels = db.query(Channel).filter(
                    Channel.is_active == True
                ).all()

            if not channels:
                return True

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for channel in channels:
                    try:
                        # Simple aggregation - just query the data
                        from src.models.analytics import StreamSession
                        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
                        streams = db.query(StreamSession).filter(
                            StreamSession.channel_id == channel.id,
                            StreamSession.created_at >= one_day_ago
                        ).all()
                        stream_hours = sum([
                            (s.ended_at - s.created_at).total_seconds() / 3600
                            if s.ended_at else 0
                            for s in streams
                        ])
                        logger.debug(f"Channel {channel.id}: {stream_hours:.2f} stream hours in last day")
                    except Exception as e:
                        logger.error(f"Error aggregating for channel {channel.id}: {e}")
                        continue
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.exception("Failed to aggregate daily stats synchronously")
            return False
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to aggregate daily stats")
        return False
