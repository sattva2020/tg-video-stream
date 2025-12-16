"""
Test-friendly FastAPI app без middleware и сложных зависимостей.
Используется только для unit тестов audio API.
"""

from fastapi import FastAPI
from src.api.audio import router as audio_router

# Создать минимальное приложение для тестов
app = FastAPI(title="Audio API Tests")

# Зарегистрировать только audio router
app.include_router(audio_router, prefix="/api/v1", tags=["Audio Processing"])
