"""
Middleware модуль для FastAPI.

Содержит:
- PrometheusMiddleware: сбор метрик HTTP запросов
- RateLimiterMiddleware: защита от злоупотреблений (Redis Fixed Window Counter)
"""

from src.middleware.prometheus import PrometheusMiddleware

__all__ = ["PrometheusMiddleware", "RateLimiterMiddleware"]
