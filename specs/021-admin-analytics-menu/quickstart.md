# Quickstart: Admin Analytics Menu

**Feature**: 021-admin-analytics-menu  
**Date**: 2024-12-07

## Быстрый старт для разработчика

### Предварительные требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Docker (опционально)

### 1. Backend: Добавить миграцию

```bash
cd backend
source venv/bin/activate  # или активация своего venv

# Создать миграцию
alembic revision --autogenerate -m "add_track_plays_analytics"

# Применить миграцию
alembic upgrade head
```

### 2. Backend: Проверить зависимости

Зависимости уже должны быть установлены. Если нет:

```bash
pip install redis  # для кеширования
```

### 3. Frontend: Установить Recharts

```bash
cd frontend
npm install recharts
```

### 4. Локальный запуск

**Backend:**
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### 5. Проверка работы

1. Авторизоваться как ADMIN
2. Открыть `/admin/analytics`
3. Должен отображаться дашборд (возможно с пустыми данными)

### 6. Тестирование API

```bash
# Получить токен (используя существующий auth)
TOKEN="your_jwt_token"

# Проверить сводку
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/summary

# Проверить топ треков
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/analytics/top-tracks?period=7d&limit=5

# Проверить защиту (должен вернуть 403 для USER)
USER_TOKEN="token_from_user_role"
curl -H "Authorization: Bearer $USER_TOKEN" \
  http://localhost:8000/api/analytics/summary
# Expected: {"detail": "Access denied..."}
```

### 7. Генерация тестовых данных

Для разработки можно добавить тестовые данные:

```python
# backend/scripts/seed_analytics.py
from datetime import datetime, timedelta
import random
from src.database import SessionLocal
from src.models.track_play import TrackPlay

def seed_analytics():
    db = SessionLocal()
    
    # Получить все треки
    tracks = db.execute("SELECT id FROM tracks LIMIT 50").fetchall()
    
    if not tracks:
        print("No tracks found. Add tracks first.")
        return
    
    # Генерировать данные за 30 дней
    now = datetime.utcnow()
    for days_ago in range(30):
        timestamp = now - timedelta(days=days_ago)
        
        # 10-50 воспроизведений в день
        for _ in range(random.randint(10, 50)):
            track = random.choice(tracks)
            play = TrackPlay(
                track_id=track[0],
                played_at=timestamp - timedelta(hours=random.randint(0, 23)),
                duration_seconds=random.randint(180, 360),
                listeners_count=random.randint(5, 100)
            )
            db.add(play)
    
    db.commit()
    print("Seeded analytics data")

if __name__ == "__main__":
    seed_analytics()
```

### 8. Структура файлов для создания

**Backend:**
```
backend/src/
├── api/
│   └── analytics.py          # 4 эндпоинта
├── models/
│   └── track_play.py         # 2 модели
├── services/
│   └── analytics_service.py  # Бизнес-логика + кеш
└── schemas/
    └── analytics.py          # Pydantic схемы
```

**Frontend:**
```
frontend/src/
├── api/
│   └── analytics.ts          # API клиент
├── types/
│   └── analytics.ts          # TypeScript типы
├── components/analytics/
│   ├── MetricCard.tsx
│   ├── ListenersChart.tsx
│   └── TopTracksTable.tsx
└── pages/admin/
    └── Analytics.tsx         # Страница
```

### 9. Ключевые изменения в существующих файлах

| Файл | Изменение |
|------|-----------|
| `frontend/src/types/permissions.ts` | Добавить `canViewAnalytics: boolean` |
| `frontend/src/components/layout/DesktopNav.tsx` | Добавить пункт меню Analytics |
| `frontend/src/components/layout/MobileNav.tsx` | Добавить пункт меню Analytics |
| `backend/src/main.py` | Подключить analytics router |

### 10. Полезные команды

```bash
# Backend тесты
cd backend && pytest tests/test_analytics.py -v

# Frontend тесты
cd frontend && npm test -- --grep "analytics"

# E2E тесты
cd frontend && npm run test:e2e -- --grep "analytics"

# Type check
cd frontend && npm run typecheck
```

## FAQ

**Q: Откуда берутся данные?**  
A: Streamer отправляет POST на `/api/internal/track-play` при воспроизведении трека.

**Q: Почему данные не обновляются?**  
A: Кеширование 5 минут. Подождите или очистите Redis: `redis-cli DEL analytics:*`

**Q: Как проверить роли?**  
A: Смотрите `backend/src/lib/rbac.py`, роли ADMIN/MODERATOR имеют `analytics_view`.
