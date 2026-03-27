import psutil
import redis
import json
import os
import time
import logging
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(
        self,
        redis_host='redis',
        redis_port=6379,
        redis_db=0,
        redis_url: str | None = None,
    ):
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        else:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.process = psutil.Process(os.getpid())

    def collect_metrics(self):
        """Collect system and process metrics."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()

            # Process metrics
            process_cpu = self.process.cpu_percent(interval=None)
            process_memory = self.process.memory_info()

            metrics = {
                'timestamp': time.time(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used': memory.used,
                    'memory_total': memory.total
                },
                'process': {
                    'cpu_percent': process_cpu,
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms
                }
            }
            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None

    def collect_encoding_metrics(self, running_channels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect encoding performance metrics for all active channels.

        Args:
            running_channels: Dictionary of channel_id -> channel_data

        Returns:
            Dictionary with encoding metrics per channel
        """
        try:
            encoding_metrics = {
                'timestamp': time.time(),
                'channels': {}
            }

            for channel_id, channel_data in running_channels.items():
                config = channel_data.get('config')
                if not config:
                    continue

                # Collect encoding profile information
                channel_metrics = {
                    'video_codec': getattr(config, 'video_codec', None) or 'default',
                    'audio_codec': getattr(config, 'audio_codec', None) or 'aac',
                    'video_bitrate': getattr(config, 'video_bitrate', None) or 'default',
                    'audio_bitrate': getattr(config, 'audio_bitrate', None) or '128',
                    'resolution': getattr(config, 'resolution', None) or 'default',
                    'video_quality': getattr(config, 'video_quality', None) or '720p',
                    'audio_quality': getattr(config, 'audio_quality', None) or 'studio',
                    'stream_type': getattr(config, 'stream_type', 'video'),
                    'chat_id': channel_data.get('chat_id'),
                    'status': 'running'
                }

                # Add FFmpeg parameters info if available
                if hasattr(config, 'ffmpeg_args') and config.ffmpeg_args:
                    channel_metrics['has_custom_ffmpeg_args'] = True
                else:
                    channel_metrics['has_custom_ffmpeg_args'] = False

                # Add stream headers info if available
                if hasattr(config, 'stream_headers') and config.stream_headers:
                    channel_metrics['has_stream_headers'] = True
                else:
                    channel_metrics['has_stream_headers'] = False

                encoding_metrics['channels'][channel_id] = channel_metrics

            # Add channel count
            encoding_metrics['active_channels'] = len(encoding_metrics['channels'])

            return encoding_metrics

        except Exception as e:
            logger.error(f"Error collecting encoding metrics: {e}")
            return {
                'timestamp': time.time(),
                'channels': {},
                'active_channels': 0,
                'error': str(e)
            }

    def push_metrics(self, metrics):
        """Push metrics to Redis."""
        if not metrics:
            return

        try:
            # Store latest metrics
            self.redis_client.set('streamer:metrics:latest', json.dumps(metrics))

            # Store in a list for history (trim to last 1000 entries)
            self.redis_client.lpush('streamer:metrics:history', json.dumps(metrics))
            self.redis_client.ltrim('streamer:metrics:history', 0, 999)

            logger.debug(f"Pushed metrics: {metrics}")
        except Exception as e:
            logger.error(f"Error pushing metrics to Redis: {e}")

    def push_encoding_metrics(self, encoding_metrics: Dict[str, Any]):
        """Push encoding metrics to Redis."""
        if not encoding_metrics:
            return

        try:
            # Store latest encoding metrics
            self.redis_client.set('streamer:metrics:encoding:latest', json.dumps(encoding_metrics))

            # Store in a list for history (trim to last 1000 entries)
            self.redis_client.lpush('streamer:metrics:encoding:history', json.dumps(encoding_metrics))
            self.redis_client.ltrim('streamer:metrics:encoding:history', 0, 999)

            logger.debug(f"Pushed encoding metrics for {encoding_metrics.get('active_channels', 0)} channels")
        except Exception as e:
            logger.error(f"Error pushing encoding metrics to Redis: {e}")

    def run_loop(self, interval=5):
        """Run the collection loop."""
        logger.info(f"Starting metrics collection loop (interval={interval}s)")
        while True:
            metrics = self.collect_metrics()
            self.push_metrics(metrics)
            time.sleep(interval)

if __name__ == "__main__":
    # Allow configuration via environment variables
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT', '6379')
    REDIS_DB = os.getenv('REDIS_DB', '0')
    REDIS_URL = os.getenv('REDIS_URL')

    resolved_url = None
    if REDIS_HOST:
        resolved_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    elif REDIS_URL:
        resolved_url = REDIS_URL

    collector = MetricsCollector(
        redis_host=REDIS_HOST or 'redis',
        redis_port=int(REDIS_PORT),
        redis_db=int(REDIS_DB),
        redis_url=resolved_url,
    )
    collector.run_loop()
