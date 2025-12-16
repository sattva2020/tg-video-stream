"""
Test-friendly FastAPI app без middleware и сложных зависимостей.
Используется только для unit тестов audio API.
"""
import sys
import os

# Добавить backend/src в sys.path для импорта модулей (database, models и т.д.)
backend_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if backend_src_path not in sys.path:
    sys.path.insert(0, backend_src_path)

from fastapi import FastAPI
from src.api.audio import router as audio_router

# Создать минимальное приложение для тестов
app = FastAPI(title="Audio API Tests")

# Зарегистрировать только audio router
app.include_router(audio_router, prefix="/api/v1", tags=["Audio Processing"])
