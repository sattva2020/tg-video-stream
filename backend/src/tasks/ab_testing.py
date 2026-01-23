"""A/B Testing background tasks for automatic test stopping and winner selection.

This module provides:
- `stop_ab_test_async(test_id, select_winner)` — schedules a background job to stop an A/B test
  and optionally select a winner based on statistical analysis
- Automatic test stopping based on duration or statistical significance
- Fallback to synchronous execution in development mode

The task uses ABTestingService to perform the actual test stopping and winner selection.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Try to lazily import Celery when available
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except Exception:
    Celery = None
    CELERY_AVAILABLE = False


def _build_celery_app():
    """Build Celery app instance for task sending."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    app = Celery('tg_video_streamer', broker=broker)
    return app


# Define the actual worker function (registered only if Celery available)
if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _build_celery_app()

    @celery_app.task(name='tasks.stop_ab_test')
    def stop_ab_test_task(test_id: str, select_winner: bool = True):
        """Worker entrypoint for stopping A/B tests and selecting winners.

        Args:
            test_id: UUID of the A/B test to stop
            select_winner: Whether to automatically select a winner based on analysis

        Returns:
            bool: True if successful, False otherwise
        """
        from database import SessionLocal
        from src.services.ab_testing_service import ABTestingService

        logger.info(f"[worker] stop_ab_test_task called for test {test_id}, select_winner={select_winner}")

        db = SessionLocal()
        try:
            # Import UUID for conversion
            from uuid import UUID

            # Convert test_id to UUID
            test_uuid = UUID(test_id)

            # Create service instance (no Redis needed for stop operation)
            service = ABTestingService(db=db, redis_client=None)

            # Call stop_test method (synchronous wrapper for async method)
            import asyncio
            try:
                # Try to get event loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                service.stop_test(test_uuid, select_winner=select_winner)
            )

            logger.info(f"A/B test {test_id} stopped successfully, winner: {result.winner_variant_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to stop A/B test {test_id}: {e}")
            return False
        finally:
            db.close()


def stop_ab_test_async(test_id: str, select_winner: bool = True) -> bool:
    """Schedule an A/B test to stop with optional winner selection.

    This function will either:
    - Enqueue a background job using Celery (if CELERY_BROKER_URL is configured), or
    - Fall back to a synchronous call (dev-mode)

    Args:
        test_id: UUID of the A/B test to stop
        select_winner: Whether to automatically select a winner based on analysis

    Returns:
        bool: True if task was scheduled or executed successfully, False otherwise
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _build_celery_app()
        try:
            app.send_task('tasks.stop_ab_test', args=[str(test_id), select_winner])
            logger.info(f"Enqueued A/B test stop for test {test_id}, select_winner={select_winner}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task for A/B test stop")
            # Fall through to sync execution
    else:
        logger.info(f"Celery not available, using synchronous mode for test {test_id}")

    # Dev fallback (synchronous) — attempt to stop test now
    logger.info(f"Dev-mode: stopping A/B test {test_id} synchronously")
    return stop_ab_test_sync(test_id, select_winner)


def stop_ab_test_sync(test_id: str, select_winner: bool = True) -> bool:
    """Synchronous helper to stop an A/B test and optionally select winner.

    Used by tests and dev fallback when Celery is not available.

    Args:
        test_id: UUID of the A/B test to stop
        select_winner: Whether to automatically select a winner based on analysis

    Returns:
        bool: True if successful, False otherwise
    """
    from database import SessionLocal
    from src.services.ab_testing_service import ABTestingService
    from uuid import UUID

    db = SessionLocal()
    try:
        test_uuid = UUID(test_id)
        service = ABTestingService(db=db, redis_client=None)

        # Run async method synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            service.stop_test(test_uuid, select_winner=select_winner)
        )

        logger.info(f"Synchronous stop of A/B test {test_id} completed, winner: {result.winner_variant_id}")
        return True

    except Exception as e:
        logger.exception(f"Failed to stop A/B test {test_id} synchronously: {e}")
        return False
    finally:
        db.close()
