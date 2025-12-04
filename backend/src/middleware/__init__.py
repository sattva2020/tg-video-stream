"""
Middleware модуль для FastAPI.

Содержит:
- PrometheusMiddleware: сбор метрик HTTP запросов
- RateLimiterMiddleware: защита от злоупотреблений (Redis Fixed Window Counter)
- SlidingSessionMiddleware: автоматическое продление JWT токенов
"""

from src.middleware.prometheus import PrometheusMiddleware
from src.middleware.sliding_session import SlidingSessionMiddleware

__all__ = ["PrometheusMiddleware", "RateLimiterMiddleware", "SlidingSessionMiddleware"]

