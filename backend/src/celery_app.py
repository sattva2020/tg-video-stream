"""
Celery application factory — optional. If CELERY_BROKER_URL is set and Celery
is installed, the app will be configured and can be used to run background workers.

Запуск worker:
    cd backend/src && celery -A celery_app worker --loglevel=info

Запуск beat (для периодических задач):
    cd backend/src && celery -A celery_app beat --loglevel=info
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
except ImportError:
    Celery = None


def make_celery():
    """Создаёт и конфигурирует Celery приложение."""
    broker = os.getenv('CELERY_BROKER_URL')
    backend = os.getenv('CELERY_RESULT_BACKEND', broker)
    
    if not broker:
        logger.info('CELERY_BROKER_URL not set — Celery disabled')
        return None
    if Celery is None:
        logger.warning('Celery package not found in environment')
        return None
    
    app = Celery(
        'tg_video_streamer',
        broker=broker,
        backend=backend,
        include=[
            'tasks.notifications',
            'tasks.media',
        ]
    )
    
    # Celery configuration
    app.conf.update(
        # Task settings
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Task execution
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,
        
        # Worker settings
        worker_prefetch_multiplier=1,  # Fetch one task at a time
        worker_concurrency=4,  # Number of concurrent workers
        
        # Result backend
        result_expires=3600,  # Results expire after 1 hour
        
        # Task routes (for dedicated queues)
        task_routes={
            'tasks.fetch_video_metadata': {'queue': 'media'},
            'tasks.fetch_playlist_metadata': {'queue': 'media'},
            'tasks.send_admin_notification': {'queue': 'notifications'},
        },
        
        # Rate limits
        task_annotations={
            'tasks.fetch_video_metadata': {
                'rate_limit': '10/m',  # Max 10 per minute (yt-dlp rate limiting)
            },
            'tasks.fetch_playlist_metadata': {
                'rate_limit': '2/m',  # Max 2 playlists per minute
            },
        },
        
        # Retry policy
        task_default_retry_delay=60,
        task_max_retries=3,
    )
    
    return app


celery_app = make_celery()
