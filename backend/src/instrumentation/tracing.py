"""
OpenTelemetry Tracing Setup для Audio API.

Интеграция с AI Toolkit trace viewer для мониторинга:
- HTTP запросов к rust-transcoder
- Операций с базой данных (PlaybackSettings)
- User authentication flow
- Audio processing pipeline
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Переменные окружения для записи контента (prompts, completions)
os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
os.environ["AZURE_SDK_TRACING_IMPLEMENTATION"] = "opentelemetry"


def init_tracing(service_name: str = "audio-api", otlp_endpoint: str = "http://localhost:4318/v1/traces"):
    """
    Инициализация OpenTelemetry трассировки.
    
    Args:
        service_name: Имя сервиса для идентификации в trace viewer
        otlp_endpoint: Endpoint OTLP collector (AI Toolkit по умолчанию)
    """
    
    # Создать resource с метаданными сервиса
    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Создать TracerProvider
    provider = TracerProvider(resource=resource)
    
    # Настроить OTLP exporter (HTTP)
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    
    # Добавить batch processor для эффективной отправки spans
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    # Установить глобальный tracer provider
    trace.set_tracer_provider(provider)
    
    print(f"✓ OpenTelemetry tracing initialized")
    print(f"  Service: {service_name}")
    print(f"  OTLP Endpoint: {otlp_endpoint}")
    
    return provider


def instrument_fastapi(app):
    """
    Автоматическая инструментация FastAPI приложения.
    
    Args:
        app: FastAPI application instance
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    
    FastAPIInstrumentor.instrument_app(app)
    print("✓ FastAPI instrumentation enabled")


def instrument_httpx():
    """
    Автоматическая инструментация httpx клиента (для rust-transcoder запросов).
    """
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    
    HTTPXClientInstrumentor().instrument()
    print("✓ HTTPX instrumentation enabled")


def instrument_sqlalchemy():
    """
    Автоматическая инструментация SQLAlchemy (для PlaybackSettings DB операций).
    """
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from src.database import engine
    
    SQLAlchemyInstrumentor().instrument(engine=engine)
    print("✓ SQLAlchemy instrumentation enabled")


def instrument_redis():
    """
    Автоматическая инструментация Redis клиента.
    """
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    
    RedisInstrumentor().instrument()
    print("✓ Redis instrumentation enabled")


def setup_full_tracing(app, service_name: str = "audio-api"):
    """
    Полная настройка трассировки для audio API.
    
    Args:
        app: FastAPI application instance
        service_name: Имя сервиса
    """
    print("\n" + "="*60)
    print("Setting up OpenTelemetry Tracing")
    print("="*60)
    
    # Инициализировать базовую трассировку
    init_tracing(service_name=service_name)
    
    # Инструментировать компоненты
    instrument_fastapi(app)
    instrument_httpx()
    
    try:
        instrument_sqlalchemy()
    except Exception as e:
        print(f"⚠ SQLAlchemy instrumentation failed: {e}")
    
    try:
        instrument_redis()
    except Exception as e:
        print(f"⚠ Redis instrumentation failed: {e}")
    
    print("="*60)
    print("Tracing setup complete!")
    print("Open AI Toolkit trace viewer to see spans.")
    print("="*60 + "\n")


# Пример использования в main.py:
# 
# from src.instrumentation.tracing import setup_full_tracing
# 
# app = FastAPI(...)
# 
# # После создания app, но до регистрации роутеров
# setup_full_tracing(app, service_name="sattva-audio-api")
