"""Celery application factory — optional. If CELERY_BROKER_URL is set and Celery
is installed, the app will be configured and can be used to run background workers.
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
except Exception:
    Celery = None


def make_celery():
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        logger.info('CELERY_BROKER_URL not set — Celery disabled')
        return None
    if Celery is None:
        logger.warning('Celery package not found in environment')
        return None
    app = Celery('tg_video_streamer', broker=broker)
    return app


celery_app = make_celery()
