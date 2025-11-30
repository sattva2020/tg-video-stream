import psutil
import redis
import json
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, redis_host='redis', redis_port=6379, redis_db=0):
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

    def run_loop(self, interval=5):
        """Run the collection loop."""
        logger.info(f"Starting metrics collection loop (interval={interval}s)")
        while True:
            metrics = self.collect_metrics()
            self.push_metrics(metrics)
            time.sleep(interval)

if __name__ == "__main__":
    # Allow configuration via environment variables
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    collector = MetricsCollector(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
    collector.run_loop()
