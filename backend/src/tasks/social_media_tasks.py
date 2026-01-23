"""
Celery tasks для автоматического постинга в социальные сети.

Включает:
- Автоматическая публикация о начале стрима
- Публикация на несколько платформ одновременно
"""
import os
import logging
from typing import Optional

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
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


def _generate_stream_start_message(channel_name: str, platform_type: str) -> str:
    """
    Генерирует сообщение о начале стрима для платформы.

    Args:
        channel_name: Название канала
        platform_type: Тип платформы (twitter, discord, etc.)

    Returns:
        Текст сообщения для публикации
    """
    if platform_type == "twitter":
        # Twitter has 280 char limit
        return f"🔴 LIVE NOW: {channel_name} is streaming! Watch now: #livestream #streaming"
    elif platform_type == "discord":
        # Discord allows 2000 chars
        return f"🔴 **STREAM STARTED**\n\n{channel_name} has started streaming!\n\n📺 Tune in now to watch the stream live!"
    else:
        # Generic message
        return f"🔴 LIVE NOW: {channel_name} is streaming!"


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.post_stream_start_announcement', bind=True, max_retries=3)
    def post_stream_start_announcement_task(self, channel_id: str):
        """
        Celery task: публикует announcement о начале стрима на все подключенные платформы.

        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).

        Args:
            channel_id: UUID канала

        Returns:
            dict с результатом публикации (success, total, posted, failed)
        """
        logger.info(f"[worker] post_stream_start_announcement_task for channel {channel_id}")

        try:
            from database import SessionLocal
            from src.models.telegram import Channel
            from src.models.streaming_platform import StreamingPlatform
            from src.models.broadcast_destination import BroadcastDestination
            from src.services.social_media_poster import get_social_media_poster
            import asyncio

            db = SessionLocal()
            try:
                # Get channel
                channel = db.query(Channel).filter(Channel.id == channel_id).first()
                if not channel:
                    logger.warning(f"Channel {channel_id} not found for social media posting")
                    return {"success": False, "error": "Channel not found"}

                # Get all active broadcast destinations for this channel
                destinations = db.query(BroadcastDestination).filter(
                    BroadcastDestination.channel_id == channel_id,
                    BroadcastDestination.enabled == True
                ).all()

                if not destinations:
                    logger.info(f"No broadcast destinations configured for channel {channel_id}")
                    return {"success": True, "total": 0, "posted": 0, "failed": 0}

                # Get social media platforms only (exclude streaming platforms like YouTube/Twitch)
                social_platform_ids = [
                    d.platform_id for d in destinations
                    if d.platform and d.platform.platform_type in ['twitter', 'discord']
                ]

                if not social_platform_ids:
                    logger.info(f"No social media platforms configured for channel {channel_id}")
                    return {"success": True, "total": 0, "posted": 0, "failed": 0}

                # Create poster service
                poster = get_social_media_poster(db)

                # Run async publish in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = []

                    for platform_id in social_platform_ids:
                        platform = db.query(StreamingPlatform).filter(
                            StreamingPlatform.id == platform_id
                        ).first()

                        if not platform:
                            logger.warning(f"Platform {platform_id} not found")
                            continue

                        # Generate message for platform
                        content = _generate_stream_start_message(
                            channel.name,
                            platform.platform_type
                        )

                        try:
                            # Publish to this platform
                            result = loop.run_until_complete(
                                poster.publish_to_platforms(
                                    channel_id=channel.id,
                                    content=content,
                                    post_type="stream_start",
                                    platform_types=[platform.platform_type]
                                )
                            )
                            results.extend(result)
                        except Exception as e:
                            logger.error(f"Failed to publish to {platform.platform_type}: {str(e)}")
                            results.append({
                                "platform_type": platform.platform_type,
                                "status": "failed",
                                "error": str(e)
                            })

                    # Count results
                    total = len(results)
                    posted = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "posted")
                    failed = total - posted

                    logger.info(
                        f"Posted stream start announcement for channel {channel_id}: "
                        f"{posted}/{total} successful"
                    )

                    return {
                        "success": True,
                        "total": total,
                        "posted": posted,
                        "failed": failed
                    }

                finally:
                    loop.close()

            except Exception as e:
                logger.exception(f"Error in post_stream_start_announcement_task for {channel_id}")
                raise self.retry(exc=e, countdown=60)
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Unhandled error in post_stream_start_announcement_task for {channel_id}")
            raise self.retry(exc=e, countdown=60)


# ============================================================================
# Public API
# ============================================================================

def post_stream_start_announcement(channel_id: str) -> bool:
    """
    Запускает асинхронную публикацию announcement о начале стрима.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        channel_id: UUID канала

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.post_stream_start_announcement', args=[str(channel_id)])
            logger.info(f"Enqueued stream start announcement for channel {channel_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Posting stream start announcement synchronously for channel {channel_id}")
    try:
        from database import SessionLocal
        from src.models.telegram import Channel
        from src.models.streaming_platform import StreamingPlatform
        from src.models.broadcast_destination import BroadcastDestination
        from src.services.social_media_poster import get_social_media_poster
        import asyncio

        db = SessionLocal()
        try:
            # Get channel
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return False

            # Get active social media destinations
            destinations = db.query(BroadcastDestination).filter(
                BroadcastDestination.channel_id == channel_id,
                BroadcastDestination.enabled == True
            ).all()

            social_platform_ids = [
                d.platform_id for d in destinations
                if d.platform and d.platform.platform_type in ['twitter', 'discord']
            ]

            if not social_platform_ids:
                return True  # No platforms configured, not an error

            poster = get_social_media_poster(db)

            # Run async publish in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for platform_id in social_platform_ids:
                    platform = db.query(StreamingPlatform).filter(
                        StreamingPlatform.id == platform_id
                    ).first()

                    if not platform:
                        continue

                    content = _generate_stream_start_message(
                        channel.name,
                        platform.platform_type
                    )

                    loop.run_until_complete(
                        poster.publish_to_platforms(
                            channel_id=channel.id,
                            content=content,
                            post_type="stream_start",
                            platform_types=[platform.platform_type]
                        )
                    )
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.exception(f"Failed to post stream start announcement synchronously")
            return False
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to post stream start announcement")
        return False
