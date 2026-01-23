"""
Celery tasks для агрегации чат-сообщений с платформ стриминга.

Включает:
- Периодический сбор сообщений со всех подключенных платформ
- Агрегация сообщений в единый формат
- Очистка старых сообщений
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
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.aggregate_chat_messages', bind=True, max_retries=3)
    def aggregate_chat_messages_task(self, channel_id: Optional[str] = None):
        """
        Celery task: собирает сообщения чата со всех платформ для канала.

        Эта задача должна вызываться периодически для обновления агрегированных
        сообщений чата. Она подключается к активным платформам (YouTube, Twitch,
        Telegram) и собирает новые сообщения.

        Args:
            channel_id: Опциональный ID канала. Если не указан, агрегируются
                       сообщения для всех активных каналов.

        Returns:
            dict с результатом агрегации (success, total_messages, channels_processed)
        """
        logger.info(f"[worker] aggregate_chat_messages_task for channel {channel_id or 'all'}")

        try:
            from database import SessionLocal
            from src.models.telegram import Channel
            from src.models.streaming_platform import StreamingPlatform
            from src.models.broadcast_destination import BroadcastDestination
            from src.services.chat_aggregator import get_chat_aggregator
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
                    logger.info(f"No active channels found for chat aggregation")
                    return {"success": True, "total_messages": 0, "channels_processed": 0}

                total_messages = 0
                channels_processed = 0

                # Создаем агрегатор
                aggregator = get_chat_aggregator(db)

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

                            # Получаем уникальные платформы
                            platform_ids = list(set([
                                d.platform_id for d in destinations
                                if d.platform
                            ]))

                            if not platform_ids:
                                logger.debug(f"No valid platforms for channel {channel.id}")
                                continue

                            # Для каждой платформы собираем сообщения
                            # (здесь можно добавить логику подключения к API платформ)
                            # В данном случае мы просто агрегируем уже сохраненные сообщения
                            channel_messages = loop.run_until_complete(
                                aggregator.get_aggregated_messages(
                                    channel_id=channel.id,
                                    limit=100,
                                    offset=0
                                )
                            )

                            message_count = len(channel_messages.messages)
                            total_messages += message_count
                            channels_processed += 1

                            logger.debug(
                                f"Aggregated {message_count} messages for channel {channel.id}"
                            )

                        except Exception as e:
                            logger.error(
                                f"Error aggregating messages for channel {channel.id}: {str(e)}"
                            )
                            # Продолжаем обработку остальных каналов
                            continue

                    logger.info(
                        f"Chat aggregation completed: {channels_processed} channels, "
                        f"{total_messages} total messages"
                    )

                    return {
                        "success": True,
                        "total_messages": total_messages,
                        "channels_processed": channels_processed
                    }

                finally:
                    loop.close()

            except Exception as e:
                logger.exception(f"Error in aggregate_chat_messages_task")
                raise self.retry(exc=e, countdown=60)
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Unhandled error in aggregate_chat_messages_task")
            raise self.retry(exc=e, countdown=60)


    @celery_app.task(name='tasks.cleanup_old_chat_messages', bind=True, max_retries=3)
    def cleanup_old_chat_messages_task(self, days_to_keep: int = 7):
        """
        Celery task: удаляет старые сообщения чата.

        Args:
            days_to_keep: Количество дней для хранения сообщений (по умолчанию 7)

        Returns:
            dict с результатом очистки (success, deleted_count)
        """
        logger.info(f"[worker] cleanup_old_chat_messages_task for {days_to_keep} days")

        try:
            from database import SessionLocal
            from src.models.chat_message import ChatMessage
            from sqlalchemy import delete

            db = SessionLocal()
            try:
                # Вычисляем дату отсечки
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

                # Удаляем старые сообщения
                stmt = delete(ChatMessage).where(
                    ChatMessage.message_timestamp < cutoff_date
                )

                result = db.execute(stmt)
                deleted_count = result.rowcount
                db.commit()

                logger.info(f"Deleted {deleted_count} old chat messages")

                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "days_to_keep": days_to_keep
                }

            except Exception as e:
                logger.exception(f"Error in cleanup_old_chat_messages_task")
                db.rollback()
                raise self.retry(exc=e, countdown=60)
            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Unhandled error in cleanup_old_chat_messages_task")
            raise self.retry(exc=e, countdown=60)


# ============================================================================
# Public API
# ============================================================================

def aggregate_chat_messages(channel_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронную агрегацию сообщений чата.

    Использует Celery если доступен, otherwise выполняет синхронно.

    Args:
        channel_id: Опциональный ID канала для агрегации

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.aggregate_chat_messages',
                args=[channel_id] if channel_id else []
            )
            logger.info(f"Enqueued chat aggregation for channel {channel_id or 'all'}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Aggregating chat messages synchronously for channel {channel_id or 'all'}")
    try:
        from database import SessionLocal
        from src.models.telegram import Channel
        from src.services.chat_aggregator import get_chat_aggregator
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

            aggregator = get_chat_aggregator(db)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for channel in channels:
                    try:
                        loop.run_until_complete(
                            aggregator.get_aggregated_messages(
                                channel_id=channel.id,
                                limit=100,
                                offset=0
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error aggregating for channel {channel.id}: {e}")
                        continue
                return True
            finally:
                loop.close()

        except Exception as e:
            logger.exception("Failed to aggregate chat messages synchronously")
            return False
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to aggregate chat messages")
        return False


def cleanup_old_chat_messages(days_to_keep: int = 7) -> bool:
    """
    Запускает асинхронную очистку старых сообщений чата.

    Args:
        days_to_keep: Количество дней для хранения сообщений

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.cleanup_old_chat_messages',
                args=[days_to_keep]
            )
            logger.info(f"Enqueued chat cleanup for {days_to_keep} days")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Cleaning up old chat messages synchronously ({days_to_keep} days)")
    try:
        from database import SessionLocal
        from src.models.chat_message import ChatMessage
        from sqlalchemy import delete
        from datetime import timedelta

        db = SessionLocal()
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            stmt = delete(ChatMessage).where(
                ChatMessage.message_timestamp < cutoff_date
            )
            result = db.execute(stmt)
            deleted_count = result.rowcount
            db.commit()
            logger.info(f"Deleted {deleted_count} old chat messages")
            return True
        except Exception as e:
            logger.exception("Failed to cleanup old chat messages")
            db.rollback()
            return False
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to cleanup old chat messages")
        return False
