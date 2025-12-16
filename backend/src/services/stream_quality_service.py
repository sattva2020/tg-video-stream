"""
Feature 022 Phase 2: Stream Quality Service

Сервис для интеграции FFprobe анализа качества потока в backend API.
Использует streamer/ffprobe_utils.py для анализа потоков.
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
import sys
import os

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
                return self._serialize_quality(stream_quality)
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
