# Research: Admin Analytics Menu

**Feature**: 021-admin-analytics-menu  
**Date**: 2024-12-07  
**Status**: Complete

## 1. Библиотека для графиков (Frontend)

### Решение: Recharts

**Обоснование**:
- Популярная React-библиотека для визуализации данных
- Декларативный API с React-компонентами
- Поддержка адаптивных графиков (ResponsiveContainer)
- Простая интеграция с TypeScript
- Небольшой размер бандла (~45KB gzipped)

**Альтернативы рассмотренные**:
- **Chart.js + react-chartjs-2**: Более низкоуровневый, требует больше настройки
- **Nivo**: Мощный, но более сложный для простых кейсов
- **Victory**: Хороший, но менее популярен и больший бандл

**Пример использования**:
```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={listenersHistory}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="timestamp" />
    <YAxis />
    <Tooltip />
    <Line type="monotone" dataKey="count" stroke="#8884d8" />
  </LineChart>
</ResponsiveContainer>
```

## 2. Стратегия кеширования (Backend)

### Решение: Redis с TTL 5 минут

**Обоснование**:
- Redis уже используется в проекте (`streamer:metrics:latest`)
- Простой TTL-механизм
- Атомарные операции get/set
- Поддержка JSON-сериализации

**Структура ключей**:
```
analytics:listeners:current     # TTL: 5 мин
analytics:listeners:history:7d  # TTL: 5 мин
analytics:top_tracks:7d         # TTL: 5 мин
analytics:summary               # TTL: 5 мин
```

**Альтернативы рассмотренные**:
- **In-memory cache (functools.lru_cache)**: Не шарится между воркерами
- **PostgreSQL materialized views**: Более сложно в обновлении
- **Memcached**: Нет JSON-типа, меньше функций

**Пример реализации**:
```python
import json
from datetime import timedelta
from redis import Redis

redis = Redis.from_url(settings.REDIS_URL)
CACHE_TTL = timedelta(minutes=5)

async def get_listener_stats() -> dict:
    cache_key = "analytics:listeners:current"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Calculate from DB
    stats = await calculate_listener_stats()
    redis.setex(cache_key, CACHE_TTL, json.dumps(stats))
    return stats
```

## 3. Retention Policy (90 дней + агрегация)

### Решение: Scheduled job для агрегации

**Обоснование**:
- Простая реализация через background task
- Минимальное влияние на производительность
- Прозрачная логика

**Структура данных**:
```sql
-- Детальные данные (хранятся 90 дней)
CREATE TABLE track_plays (
    id SERIAL PRIMARY KEY,
    track_id INTEGER NOT NULL,
    played_at TIMESTAMP NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER,
    listeners_count INTEGER NOT NULL,
    CONSTRAINT fk_track FOREIGN KEY (track_id) REFERENCES tracks(id)
);

CREATE INDEX idx_track_plays_played_at ON track_plays(played_at);

-- Месячные агрегаты (хранятся постоянно)
CREATE TABLE monthly_analytics (
    id SERIAL PRIMARY KEY,
    month DATE NOT NULL,
    total_plays INTEGER NOT NULL,
    total_duration_seconds BIGINT NOT NULL,
    peak_listeners INTEGER NOT NULL,
    avg_listeners DECIMAL(10,2) NOT NULL,
    unique_tracks INTEGER NOT NULL,
    UNIQUE(month)
);
```

**Агрегация (ежедневно)**:
```python
async def aggregate_old_analytics():
    """Агрегирует данные старше 90 дней в месячные записи."""
    cutoff = datetime.now() - timedelta(days=90)
    
    # Агрегируем данные за месяц
    await db.execute("""
        INSERT INTO monthly_analytics (month, total_plays, ...)
        SELECT DATE_TRUNC('month', played_at), COUNT(*), ...
        FROM track_plays
        WHERE played_at < :cutoff
        GROUP BY DATE_TRUNC('month', played_at)
        ON CONFLICT (month) DO UPDATE SET ...
    """, {"cutoff": cutoff})
    
    # Удаляем старые детальные данные
    await db.execute("""
        DELETE FROM track_plays WHERE played_at < :cutoff
    """, {"cutoff": cutoff})
```

## 4. Структура API эндпоинтов

### Решение: RESTful API с query параметрами

**Эндпоинты**:
```
GET /api/analytics/summary?period=7d
GET /api/analytics/listeners?period=7d
GET /api/analytics/top-tracks?period=7d&limit=5
GET /api/analytics/history?period=7d&metric=listeners
```

**Периоды**:
- `7d` - последние 7 дней (default)
- `30d` - последние 30 дней
- `90d` - последние 90 дней
- `all` - всё время (включая месячные агрегаты)

## 5. Интеграция с навигацией

### Решение: Расширение NavItem

**Текущий паттерн** (из DesktopNav.tsx):
```tsx
{ 
  path: '/admin/monitoring', 
  label: t('nav.monitoring', 'Мониторинг'), 
  icon: <Activity className="w-4 h-4" />,
  adminOnly: true,
  moderatorAllowed: true,
}
```

**Новый пункт** (аналогичная структура):
```tsx
{ 
  path: '/admin/analytics', 
  label: t('nav.analytics', 'Аналитика'), 
  icon: <BarChart2 className="w-4 h-4" />,  // lucide-react
  adminOnly: true,
  moderatorAllowed: true,
}
```

**Обоснование**:
- Полностью совместимо с `filterNavItems()`
- `adminOnly: true` скрывает от OPERATOR и USER
- `moderatorAllowed: true` разрешает MODERATOR

## 6. Интеграция со Streamer

### Решение: HTTP POST при воспроизведении

**Streamer → Backend**:
```python
# При начале воспроизведения трека
async def log_track_play(track_id: int, listeners: int):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.BACKEND_URL}/api/internal/track-play",
            json={
                "track_id": track_id,
                "listeners_count": listeners,
                "timestamp": datetime.now().isoformat()
            },
            headers={"X-Internal-Token": settings.INTERNAL_TOKEN}
        )
```

**Альтернативы рассмотренные**:
- **Direct DB insert**: Streamer не имеет доступа к DB
- **Redis queue → worker**: Overengineering для текущего масштаба
- **WebSocket**: Не нужен для однонаправленных событий

## Выводы

Все технические решения приняты. Готово к переходу на Phase 1 (data-model.md).
