# Tasks: Реальные данные мониторинга системы

**Input**: Design documents from `/specs/015-real-system-monitoring/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Включены (pytest, Vitest, Playwright) — указано в plan.md и spec.md.

**Organization**: Задачи сгруппированы по user stories для независимой реализации и тестирования.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Можно запускать параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой user story относится задача (US1, US2, US3, US4)
- Указаны точные пути к файлам

> ⚖️ Конституция: для каждой пользовательской истории фиксируются связанные тесты в `tests/`
> и необходимые обновления документации (`docs/`). Временные файлы направляются в `.internal/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Инициализация проекта, зависимости, типы

- [ ] T001 Добавить `psutil>=5.9.0` в `backend/requirements.txt`
- [ ] T002 [P] Создать TypeScript типы `SystemMetrics`, `ActivityEvent` в `frontend/src/types/system.ts`
- [ ] T003 [P] Создать Pydantic схемы `SystemMetricsResponse`, `ActivityEventResponse` в `backend/src/api/schemas/system.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: База данных, модель, сервисы — БЛОКИРУЕТ все user stories

**⚠️ CRITICAL**: Работа над user stories невозможна до завершения этой фазы

- [ ] T004 Создать SQLAlchemy модель `ActivityEvent` в `backend/src/models/activity_event.py`
- [ ] T005 Зарегистрировать модель в `backend/src/models/__init__.py`
- [ ] T006 Создать Alembic миграцию для таблицы `activity_events` в `backend/migrations/versions/`
- [ ] T007 [P] Создать `MetricsService` с методами сбора psutil + pg_stat в `backend/src/services/metrics_service.py`
- [ ] T008 [P] Создать `ActivityService` с методами log_event, get_events, cleanup в `backend/src/services/activity_service.py`
- [ ] T009 Создать API роутер `/api/system` в `backend/src/api/system.py`
- [ ] T010 Зарегистрировать роутер в `backend/src/api/__init__.py` или `backend/src/main.py`

**Checkpoint**: Foundation ready — можно начинать user stories

---

## Phase 3: User Story 1 - Просмотр реальных метрик здоровья системы (Priority: P1) 🎯 MVP

**Goal**: Администратор видит актуальные CPU, RAM, диск, латентность, DB connections на Dashboard

**Independent Test**: Открыть Dashboard → блок "Здоровье системы" показывает реальные данные → через 30 сек данные обновляются

### Tests for User Story 1

- [ ] T011 [P] [US1] Написать pytest тест для `GET /api/system/metrics` в `backend/tests/api/test_system_metrics.py`
- [ ] T012 [P] [US1] Написать Vitest тест для хука useSystemMetrics в `frontend/src/hooks/__tests__/useSystemMetrics.test.ts`

### Implementation for User Story 1

- [ ] T013 [US1] Реализовать endpoint `GET /api/system/metrics` в `backend/src/api/system.py`
- [ ] T014 [P] [US1] Создать API клиент `systemApi.getMetrics()` в `frontend/src/api/system.ts`
- [ ] T015 [P] [US1] Создать TanStack Query хук `useSystemMetrics` с refetchInterval 30s в `frontend/src/hooks/useSystemMetrics.ts`
- [ ] T016 [US1] Обновить компонент `SystemHealth.tsx` — подключить реальные данные вместо пропсов `frontend/src/components/dashboard/SystemHealth.tsx`
- [ ] T017 [US1] Обновить `AdminDashboardV2.tsx` — убрать mock данные для SystemHealth `frontend/src/components/dashboard/AdminDashboardV2.tsx`
- [ ] T018 [US1] Добавить обработку ошибок и состояние "Данные временно недоступны" в `SystemHealth.tsx`
- [ ] T019 [US1] Добавить визуальную индикацию критических порогов (красный при >90% CPU и т.д.)

**Checkpoint**: US1 полностью функционален — метрики отображаются и обновляются

---

## Phase 4: User Story 2 - Просмотр истории последних событий системы (Priority: P1)

**Goal**: Администратор видит ленту реальных событий (регистрации, трансляции, треки)

**Independent Test**: Зарегистрировать нового пользователя → событие появляется в ленте активности

### Tests for User Story 2

- [ ] T020 [P] [US2] Написать pytest тест для `GET /api/system/activity` в `backend/tests/api/test_activity_events.py`
- [ ] T021 [P] [US2] Написать pytest тест для записи событий в `backend/tests/api/test_activity_logging.py`

### Implementation for User Story 2

- [ ] T022 [US2] Реализовать endpoint `GET /api/system/activity` с пагинацией в `backend/src/api/system.py`
- [ ] T023 [P] [US2] Создать API клиент `systemApi.getActivity()` в `frontend/src/api/system.ts`
- [ ] T024 [P] [US2] Создать хук `useActivityEvents` с refetchInterval 30s в `frontend/src/hooks/useActivityEvents.ts`
- [ ] T025 [US2] Обновить компонент `ActivityTimeline.tsx` — подключить реальные данные `frontend/src/components/dashboard/ActivityTimeline.tsx`
- [ ] T026 [US2] Обновить `AdminDashboardV2.tsx` — убрать mockActivityEvents `frontend/src/components/dashboard/AdminDashboardV2.tsx`
- [ ] T027 [US2] Интегрировать запись событий в `backend/src/api/auth/routes.py` — user_registered
- [ ] T028 [US2] Интегрировать запись событий в `backend/src/api/users.py` — user_approved, user_rejected
- [ ] T029 [US2] Интегрировать запись событий в `backend/src/api/admin.py` — stream_started, stream_stopped
- [ ] T030 [US2] Интегрировать запись событий в `backend/src/api/playlist.py` — track_added, track_removed
- [ ] T031 [US2] Реализовать cleanup старых событий (>1000) в ActivityService

**Checkpoint**: US2 полностью функционален — реальные события отображаются в ленте

---

## Phase 5: User Story 3 - Индикация статуса трансляции в реальном времени (Priority: P2)

**Goal**: Администратор видит актуальный статус стрима (онлайн/офлайн/ошибка) с деталями

**Independent Test**: Запустить стрим → статус "Онлайн" (зелёный); остановить → "Офлайн" (серый)

### Implementation for User Story 3

- [ ] T032 [US3] Добавить детальную информацию о статусе в существующий `GET /api/admin/stream/status`
- [ ] T033 [US3] Обновить `StreamStatusCard.tsx` — добавить описание ошибки при статусе error `frontend/src/components/dashboard/StreamStatusCard.tsx`
- [ ] T034 [US3] Записывать событие stream_error при ошибках трансляции в соответствующий сервис

**Checkpoint**: US3 функционален — статус трансляции отображается корректно

---

## Phase 6: User Story 4 - Фильтрация и поиск по истории событий (Priority: P3)

**Goal**: Администратор может фильтровать события по типу и искать по тексту

**Independent Test**: Выбрать фильтр "Регистрации" → только события user_registered в списке

### Implementation for User Story 4

- [ ] T035 [US4] Добавить query-параметры `type`, `search` в endpoint `GET /api/system/activity`
- [ ] T036 [P] [US4] Добавить UI фильтра по типу в `ActivityTimeline.tsx`
- [ ] T037 [P] [US4] Добавить UI поиска по тексту в `ActivityTimeline.tsx`
- [ ] T038 [US4] Обновить хук `useActivityEvents` для поддержки фильтров

**Checkpoint**: US4 функционален — фильтры и поиск работают

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Документация, локализация, E2E тесты

- [ ] T039 [P] Создать документацию API в `docs/api/system-metrics.md`
- [ ] T040 [P] Создать документацию API в `docs/api/activity-events.md`
- [ ] T041 [P] Добавить ключи локализации `dashboard.health.*`, `dashboard.activity.*` в i18n файлы
- [ ] T042 Написать Playwright E2E тест в `frontend/tests/dashboard-monitoring.spec.ts`
- [ ] T043 Запустить quickstart.md валидацию — проверить все чекпоинты
- [ ] T044 Запустить `npm run docs:validate` и исправить broken links

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Нет зависимостей — старт сразу
- **Phase 2 (Foundational)**: Зависит от Phase 1 — БЛОКИРУЕТ все user stories
- **Phase 3-6 (User Stories)**: Все зависят от Phase 2 completion
  - US1 и US2 (оба P1) могут выполняться параллельно
  - US3 (P2) может начаться после US1/US2 или параллельно
  - US4 (P3) зависит от US2 (нужна лента событий)
- **Phase 7 (Polish)**: Зависит от всех user stories

### User Story Dependencies

```
┌─────────────────────────────────────┐
│        Phase 2: Foundational        │
│   T004→T010 (BLOCKING)              │
└────────────────┬────────────────────┘
                 │
    ┌────────────┼────────────┐
    ↓            ↓            ↓
┌───────┐   ┌───────┐   ┌───────┐
│  US1  │   │  US2  │   │  US3  │
│ (P1)  │   │ (P1)  │   │ (P2)  │
│T011-19│   │T020-31│   │T032-34│
└───────┘   └───┬───┘   └───────┘
                │
                ↓
           ┌───────┐
           │  US4  │
           │ (P3)  │
           │T035-38│
           └───────┘
```

### Parallel Opportunities

**Phase 1** — все задачи [P] параллельно:
```
T001 ─┬─ T002
      └─ T003
```

**Phase 2** — T007 и T008 параллельно:
```
T004 → T005 → T006
              ↓
         T007 ─┬─ T008
               ↓
         T009 → T010
```

**User Stories** — тесты и API клиенты параллельно:
```
# US1
T011 ─┬─ T012
T014 ─┴─ T015

# US2
T020 ─┬─ T021
T023 ─┴─ T024

# US4
T036 ─┬─ T037
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. ✅ Complete Phase 1: Setup (T001-T003)
2. ✅ Complete Phase 2: Foundational (T004-T010)
3. ✅ Complete Phase 3: User Story 1 (T011-T019)
4. ✅ Complete Phase 4: User Story 2 (T020-T031)
5. **STOP and VALIDATE**: Запустить quickstart.md чекпоинты
6. Deploy MVP — администратор видит реальные метрики и события

### Incremental Delivery

1. Setup + Foundational → API endpoints готовы
2. US1 → Метрики системы работают → Demo
3. US2 → Лента событий работает → Demo
4. US3 → Статус трансляции улучшен → Demo
5. US4 → Фильтры добавлены → Demo

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 44 |
| **Setup (Phase 1)** | 3 |
| **Foundational (Phase 2)** | 7 |
| **US1 Tasks** | 9 |
| **US2 Tasks** | 12 |
| **US3 Tasks** | 3 |
| **US4 Tasks** | 4 |
| **Polish Tasks** | 6 |
| **Parallel Opportunities** | 15 tasks marked [P] |
| **MVP Scope** | US1 + US2 (Phase 1-4, 31 tasks) |

---

## Notes

- [P] tasks = разные файлы, нет зависимостей
- [Story] label связывает задачу с user story для трассируемости
- Каждая user story независимо тестируема
- Коммит после каждой задачи или логической группы
- Остановка на любом checkpoint для валидации
- Избегать: неясных задач, конфликтов в одном файле, кросс-story зависимостей
