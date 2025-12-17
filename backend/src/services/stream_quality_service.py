"""
Feature 022 Phase 2: Stream Quality Service

Сервис для интеграции FFprobe анализа качества потока в backend API.
Использует streamer/ffprobe_utils.py для анализа потоков.
"""

import asyncio
import logging
import re
from typing import Optional, Dict
from datetime import datetime
import sys
import os

from src.services.stream_controller import get_stream_controller

# Add streamer to path for imports
streamer_path = os.path.join(os.path.dirname(__file__), '../../../streamer')
if streamer_path not in sys.path:
    sys.path.insert(0, streamer_path)

log = logging.getLogger(__name__)


class StreamQualityService:
    """
    Phase 022 Phase 2: Сервис для анализа качества потока
    
    Предоставляет удобный API для backend для анализа качества потоков
    используя FFprobe интеграцию из streamer/ffprobe_utils.py
    """
    
    _instance = None
    _cache: Dict[str, tuple] = {}
    _cache_ttl = 5 * 60  # 5 minutes
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_performance_metrics(self) -> Optional[Dict]:
        """
        Получает метрики производительности из логов FFmpeg.
        """
        try:
            controller = get_stream_controller()
            logs = controller.get_logs(lines=20)
            if not logs:
                return None
            
            # Ищем последнюю строку статуса FFmpeg
            # frame=  234 fps= 24 q=28.0 size=    1234kB time=00:00:10.00 bitrate=1000.0kbits/s speed=1.0x drop= 0
            for line in reversed(logs):
                if "frame=" in line and "fps=" in line:
                    metrics = {}
                    
                    # Dropped frames
                    drop_match = re.search(r'drop=\s*(\d+)', line)
                    if drop_match:
                        metrics['dropped_frames'] = int(drop_match.group(1))
                    
                    # Speed
                    speed_match = re.search(r'speed=\s*([\d\.]+)x', line)
                    if speed_match:
                        metrics['speed'] = float(speed_match.group(1))
                        
                    # FPS
                    fps_match = re.search(r'fps=\s*([\d\.]+)', line)
                    if fps_match:
                        metrics['fps'] = float(fps_match.group(1))
                        
                    # Bitrate
                    bitrate_match = re.search(r'bitrate=\s*([\d\.]+)kbits/s', line)
                    if bitrate_match:
                        metrics['bitrate_kbps'] = float(bitrate_match.group(1))
                        
                    return metrics
            
            return None
        except Exception as e:
            log.error(f"Error getting performance metrics: {e}")
            return None

    async def analyze_stream_quality(
        self,
        url: str,
        timeout: int = 10,
        use_cache: bool = True,
        force: bool = False
    ) -> Optional[Dict]:
        """
        Анализирует качество потока.
        
        Args:
            url: URL потока для анализа
            timeout: Таймаут для FFprobe
            use_cache: Использовать ли кеш
            force: Форсировать переанализ, игнорируя кеш
            
        Returns:
            Dict с информацией о качестве или None
        """
        try:
            # Lazy import to avoid dependency issues
            from ffprobe_utils import analyze_stream_quality_cached
            
            # Используем кешированную версию если нужно
            if use_cache:
                stream_quality = await analyze_stream_quality_cached(
                    url,
                    timeout=timeout,
                    force=force
                )
            else:
                # Без кеша
                from ffprobe_utils import analyze_stream_quality
                stream_quality = await analyze_stream_quality(url, timeout)
            
            if stream_quality:
                result = self._serialize_quality(stream_quality)
                
                # Добавляем метрики производительности
                perf_metrics = self._get_performance_metrics()
                if perf_metrics:
                    result['performance'] = perf_metrics
                
                return result
            return None
            
        except ImportError as e:
            log.error(f"FFprobe utils not available: {e}")
            return None
        except Exception as e:
            log.error(f"Error analyzing stream quality for {url}: {e}")
            return None
    
    @staticmethod
    def _serialize_quality(stream_quality) -> Dict:
        """
        Сериализует StreamQuality объект в словарь для JSON ответа.
        
        Использует to_dict() метод StreamQuality класса.
        """
        return stream_quality.to_dict()
    
    async def analyze_batch_streams(
        self,
        urls: list[str],
        timeout: int = 10
    ) -> Dict[str, Optional[Dict]]:
        """
        Анализирует качество множественных потоков параллельно.
        
        Args:
            urls: Список URL для анализа
            timeout: Таймаут для каждого FFprobe
            
        Returns:
            Dict {url: quality_metrics}
        """
        try:
            from ffprobe_utils import batch_analyze_streams
            
            results = await batch_analyze_streams(urls, timeout)
            
            # Сериализуем результаты
            serialized = {}
            for url, quality in results.items():
                serialized[url] = self._serialize_quality(quality) if quality else None
            
            return serialized
            
        except Exception as e:
            log.error(f"Error batch analyzing streams: {e}")
            return {url: None for url in urls}
    
    def clear_cache(self, url: Optional[str] = None):
        """
        Очищает кеш анализов.
        
        Args:
            url: Если указан, очищает только кеш для этого URL
                 Если None, очищает весь кеш
        """
        if url:
            if url in self._cache:
                del self._cache[url]
                log.debug(f"Cleared cache for {url}")
        else:
            self._cache.clear()
            log.debug("Cleared all quality cache")


# Singleton instance
stream_quality_service = StreamQualityService()


# Dependency для FastAPI
async def get_stream_quality_service() -> StreamQualityService:
    """FastAPI dependency для получения сервиса качества потока"""
    return stream_quality_service
