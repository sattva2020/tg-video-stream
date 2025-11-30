# Feature 015: Real System Monitoring

## Summary
Реализация реального мониторинга системы на Dashboard с использованием psutil и pg_stat_activity.

## Changes

### Backend
- ✅ `psutil>=5.9.0` — зависимость для сбора метрик
- ✅ `ActivityEvent` модель с JSONB details
- ✅ Миграция `015_add_activity_events` с индексами
- ✅ `MetricsService` — psutil + pg_stat_activity
- ✅ `ActivityService` — логирование событий с auto-cleanup
- ✅ `/api/system/metrics` и `/api/system/activity` endpoints
- ✅ Интеграция событий в auth, admin, playlist routes

### Frontend
- ✅ TypeScript типы `SystemMetrics`, `ActivityEvent`
- ✅ `useSystemMetrics` хук с TanStack Query (30s refresh)
- ✅ `useActivityEvents` хук с пагинацией/фильтрацией
- ✅ Обновлён `SystemHealth` для реальных метрик
- ✅ Обновлён `ActivityTimeline` с фильтром UI
- ✅ Обновлён `StreamStatusCard` для отображения ошибок

### Tests
- ✅ Contract tests для `/api/system/metrics`
- ✅ Contract tests для `/api/system/activity`
- ✅ Unit tests для `ActivityService`
- ✅ Hook tests для `useSystemMetrics`
- ✅ E2E tests для dashboard monitoring (US1-US4)

### Docs
- ✅ `docs/api/system-metrics.md`
- ✅ `docs/api/activity-events.md`

## Spec Compliance
- **Tasks**: 44/44 complete
- **Checklists**: requirements.md (17/17), spec-quality.md (45/45)

## Deployment Notes
После мержа на VPS:
```bash
cd /opt/sattva-streamer/backend
alembic upgrade head
systemctl restart sattva-backend
```
