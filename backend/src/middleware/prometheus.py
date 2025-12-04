"""
Prometheus Middleware

Middleware для автоматического сбора метрик HTTP запросов:
- Количество запросов (Counter)
- Длительность запросов (Histogram)
- Статус коды
- Методы и пути

Использование:
    from src.middleware.prometheus import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
"""

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.services.prometheus_metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
)

log = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware для сбора метрик HTTP запросов.
    
    Отслеживает:
    - Общее количество запросов по методу, пути и статусу
    - Время выполнения запросов
    - Количество запросов в обработке
    
    Исключает из метрик:
    - /metrics (чтобы не создавать рекурсию)
    - /health
    - /favicon.ico
    """
    
    # Пути, которые не нужно отслеживать
    EXCLUDED_PATHS = {
        "/metrics",
        "/health",
        "/healthz",
        "/favicon.ico",
        "/api/health",
    }
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """
        Обработка запроса с записью метрик.
        
        Args:
            request: HTTP запрос
            call_next: Следующий обработчик
            
        Returns:
            Response: HTTP ответ
        """
        path = request.url.path
        method = request.method
        
        # Пропускаем исключенные пути
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Нормализуем путь для метрик (убираем ID из путей)
        normalized_path = self._normalize_path(path)
        
        # Увеличиваем счетчик запросов в обработке
        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=method,
            path=normalized_path
        ).inc()
        
        # Замеряем время
        start_time = time.perf_counter()
        
        try:
            # Выполняем запрос
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # При ошибке записываем 500
            status_code = 500
            log.error(f"Request failed: {method} {path} - {e}")
            raise
            
        finally:
            # Вычисляем длительность
            duration = time.perf_counter() - start_time
            
            # Записываем метрики
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path=normalized_path,
                status=str(status_code)
            ).inc()
            
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                path=normalized_path
            ).observe(duration)
            
            # Уменьшаем счетчик запросов в обработке
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=method,
                path=normalized_path
            ).dec()
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Нормализация пути для метрик.
        
        Заменяет динамические сегменты (UUID, числа) на плейсхолдеры,
        чтобы не создавать слишком много уникальных лейблов.
        
        Args:
            path: Оригинальный путь
            
        Returns:
            str: Нормализованный путь
        """
        import re
        
        # Заменяем UUID
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Заменяем числовые ID
        path = re.sub(
            r'/\d+(?=/|$)',
            '/{id}',
            path
        )
        
        # Заменяем длинные строки (токены и т.п.)
        path = re.sub(
            r'/[a-zA-Z0-9_-]{32,}(?=/|$)',
            '/{token}',
            path
        )
        
        return path
