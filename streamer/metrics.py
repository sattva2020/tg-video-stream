import psutil
import redis
import json
import os
import time
import logging
from collections import deque
from typing import Dict, List, Optional

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

        # Initialize latency tracking
        self.latency_samples = deque(maxlen=1000)  # Store last 1000 samples
        self.redis_latency_samples = deque(maxlen=100)
        self.processing_latency_samples = deque(maxlen=100)

    def record_latency(self, latency_ms: float, category: str = 'general'):
        """Record a latency measurement in milliseconds."""
        if category == 'redis':
            self.redis_latency_samples.append(latency_ms)
        elif category == 'processing':
            self.processing_latency_samples.append(latency_ms)
        self.latency_samples.append(latency_ms)

    def _calculate_latency_stats(self, samples: deque) -> Optional[Dict]:
        """Calculate statistics for latency samples."""
        if not samples:
            return None

        samples_list = list(samples)
        samples_list.sort()

        return {
            'count': len(samples_list),
            'min_ms': round(samples_list[0], 2),
            'max_ms': round(samples_list[-1], 2),
            'avg_ms': round(sum(samples_list) / len(samples_list), 2),
            'p50_ms': round(samples_list[int(len(samples_list) * 0.5)], 2),
            'p95_ms': round(samples_list[int(len(samples_list) * 0.95)], 2) if len(samples_list) > 1 else samples_list[0],
            'p99_ms': round(samples_list[int(len(samples_list) * 0.99)], 2) if len(samples_list) > 1 else samples_list[0]
        }

    def collect_metrics(self):
        """Collect system and process metrics."""
        try:
            start_time = time.time()

            # System metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()

            # Process metrics
            process_cpu = self.process.cpu_percent(interval=None)
            process_memory = self.process.memory_info()

            # Latency metrics
            overall_latency = self._calculate_latency_stats(self.latency_samples)
            redis_latency = self._calculate_latency_stats(self.redis_latency_samples)
            processing_latency = self._calculate_latency_stats(self.processing_latency_samples)

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
                },
                'latency': {}
            }

            # Add latency statistics if available
            if overall_latency:
                metrics['latency']['overall'] = overall_latency
            if redis_latency:
                metrics['latency']['redis_operations'] = redis_latency
            if processing_latency:
                metrics['latency']['processing'] = processing_latency

            # Record collection time as processing latency
            collection_time_ms = (time.time() - start_time) * 1000
            self.record_latency(collection_time_ms, 'processing')

            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return None

    def push_metrics(self, metrics):
        """Push metrics to Redis."""
        if not metrics:
            return

        try:
            start_time = time.time()

            # Store latest metrics
            self.redis_client.set('streamer:metrics:latest', json.dumps(metrics))

            # Store in a list for history (trim to last 1000 entries)
            self.redis_client.lpush('streamer:metrics:history', json.dumps(metrics))
            self.redis_client.ltrim('streamer:metrics:history', 0, 999)

            # Record Redis operation latency
            redis_latency_ms = (time.time() - start_time) * 1000
            self.record_latency(redis_latency_ms, 'redis')

            logger.debug(f"Pushed metrics: {metrics}")
        except Exception as e:
            logger.error(f"Error pushing metrics to Redis: {e}")

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
