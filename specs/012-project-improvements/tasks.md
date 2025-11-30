# Tasks: План улучшения проекта 24/7 TV Telegram

**Input**: Design documents from `/specs/012-project-improvements/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Тесты включены по необходимости для валидации критических изменений.

**Organization**: Задачи сгруппированы по user stories для независимой реализации и тестирования.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Можно выполнять параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой user story относится задача (US1, US2, US3...)
- Указаны точные пути к файлам

> ⚖️ Конституция: для каждой пользовательской истории фиксируем связанные тесты в `tests/`
> и необходимые обновления документации (`docs/`, `ai-instructions/`). Задачи по работе с
> окружением ссылаются на `template.env`, временные файлы направляются в `.internal/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка структуры проекта для изменений

- [x] T001 Создать backup текущего docker-compose.yml в `.internal/backups/`
- [x] T002 [P] Создать директорию `config/monitoring/` для конфигов Prometheus/Grafana
- [x] T003 [P] Создать директорию `config/monitoring/grafana/dashboards/`
- [x] T004 [P] Создать директорию `backend/src/api/schedule/` для рефакторинга
- [x] T005 [P] Добавить `pytest-cov` в `backend/requirements-dev.txt`
- [x] T006 [P] Добавить `@vitest/coverage-v8` в `frontend/package.json` devDependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Базовые изменения, которые ДОЛЖНЫ быть завершены до начала работы над User Stories

**⚠️ CRITICAL**: Работа над user stories не может начаться до завершения этой фазы

- [x] T007 Добавить переменные мониторинга в `template.env`: GRAFANA_ADMIN_PASSWORD, TELEGRAM_ALERT_BOT_TOKEN, TELEGRAM_ALERT_CHAT_ID
- [x] T008 Добавить переменную DB_PASSWORD в `template.env` для замены hardcoded credentials
- [x] T009 Обновить `scripts/generate_env.sh` для генерации новых переменных

**Checkpoint**: Foundational готов — можно начинать работу над User Stories параллельно

---

## Phase 3: User Story 1 — Устранение критических уязвимостей безопасности (Priority: P1) 🔐

**Goal**: Удалить Docker socket mount, изолировать сети, защитить credentials

**Independent Test**: Запустить Trivy security scan, проверить отсутствие socket mount, подтвердить network isolation

### Smoke Test для User Story 1

- [x] T010 [US1] Создать smoke test `tests/smoke/test_security_docker.sh` для проверки отсутствия socket mount

### Implementation для User Story 1

- [x] T011 [US1] Удалить volume `/var/run/docker.sock:/var/run/docker.sock` из backend service в `docker-compose.yml`
- [x] T012 [US1] Заменить hardcoded `POSTGRES_PASSWORD=postgres` на `${DB_PASSWORD}` в `docker-compose.yml`
- [x] T013 [US1] Добавить Docker networks (external, internal, streamer) в `docker-compose.yml`
- [x] T014 [US1] Назначить сети сервисам: frontend→external, backend→external+internal, db→internal, redis→internal+streamer, streamer→streamer
- [x] T015 [US1] Обновить `backend/.env.example` с новыми переменными
- [x] T016 [US1] Обновить документацию `docs/architecture/docker-networks.md` с диаграммой сетей

**Checkpoint**: US-1 завершён — security scan должен проходить, сети изолированы

---

## Phase 4: User Story 2 — Модернизация deprecated кода (Priority: P1) 🔧

**Goal**: Обновить SQLAlchemy и Pydantic до современных API без DeprecationWarnings

**Independent Test**: Запустить `pytest -W error::DeprecationWarning` — все тесты должны пройти

### Implementation для User Story 2

- [x] T017 [P] [US2] Мигрировать `backend/src/database.py`: заменить `declarative_base()` на class `Base(DeclarativeBase)`
- [x] T018 [P] [US2] Мигрировать `backend/src/api/telegram_auth.py` line 29: заменить `class Config` на `model_config = ConfigDict(from_attributes=True)`
- [x] T019 [P] [US2] Мигрировать `backend/src/api/schedule.py` lines 90, 113, 155: заменить `class Config` на `model_config = ConfigDict(...)`
- [x] T020 [P] [US2] Мигрировать `backend/src/api/playlist.py` line 57: заменить `class Config` на `model_config = ConfigDict(...)`
- [x] T021 [P] [US2] Мигрировать `backend/src/api/channels.py` line 30: заменить `class Config` на `model_config = ConfigDict(...)`
- [x] T022 [US2] Проверить все модели в `backend/src/models/` на deprecated patterns
- [x] T023 [US2] Добавить import `from pydantic import ConfigDict` во все затронутые файлы
- [x] T024 [US2] Запустить `pytest -W error::DeprecationWarning` и убедиться что все тесты проходят

**Checkpoint**: US-2 завершён — никаких DeprecationWarnings в нашем коде (pyrogram warnings исключены через filterwarnings)

---

## Phase 5: User Story 3 — Добавление Health Checks в Docker (Priority: P2) 🏥

**Goal**: Добавить health checks для всех сервисов, создать /health endpoint

**Independent Test**: Запустить `docker compose up`, дождаться healthy статуса всех сервисов

### Contract Test для User Story 3

- [x] T025 [US3] Создать contract test `backend/tests/api/test_health.py` для endpoint `/health` согласно `contracts/health-api.yaml`

### Implementation для User Story 3

- [x] T026 [US3] Создать endpoint `/health` в `backend/src/api/health.py` с проверкой db и redis
- [x] T027 [US3] Создать endpoint `/health/live` (liveness probe) в `backend/src/api/health.py`
- [x] T028 [US3] Создать endpoint `/health/ready` (readiness probe) в `backend/src/api/health.py`
- [x] T029 [US3] Зарегистрировать health router в `backend/src/main.py`
- [x] T030 [US3] Добавить healthcheck для backend service в `docker-compose.yml`: `curl -f http://localhost:8000/health`
- [x] T031 [US3] Добавить healthcheck для db service в `docker-compose.yml`: `pg_isready -U postgres`
- [x] T032 [US3] Добавить healthcheck для redis service в `docker-compose.yml`: `redis-cli ping`
- [x] T033 [US3] Добавить healthcheck для frontend service в `docker-compose.yml`: `curl -f http://localhost:80/`
- [x] T034 [US3] Добавить healthcheck для streamer service в `docker-compose.yml`: `curl -f http://localhost:9090/metrics`
- [x] T035 [US3] Настроить `depends_on: condition: service_healthy` для backend→db, backend→redis

**Checkpoint**: US-3 завершён — все сервисы показывают healthy статус

---

## Phase 6: User Story 4 — Внедрение CD Pipeline (Priority: P2) 🚀

**Goal**: Автоматический deployment на VPS 37.53.91.144 при merge в main

**Independent Test**: Создать тестовый tag, убедиться что workflow запускается

### Implementation для User Story 4

- [x] T036 [US4] Создать `.github/workflows/cd.yml` с trigger на push to main
- [x] T037 [US4] Добавить job deploy с использованием `appleboy/ssh-action@v1`
- [x] T038 [US4] Настроить SSH connection к 37.53.91.144 с secret `SSH_PRIVATE_KEY`
- [x] T039 [US4] Добавить deploy commands: git pull, docker compose pull, docker compose up -d --build
- [x] T040 [US4] Добавить environment `staging` для push to main
- [x] T041 [US4] Добавить environment `production` с approval gate для release tags
- [x] T042 [US4] Добавить rollback step с инструкциями в workflow comments
- [x] T043 [US4] Создать документацию `docs/development/cd-pipeline.md` с описанием workflow и rollback
- [x] T043a [US4] Задокументировать существующий `scripts/rollback_release.sh` в `quickstart.md` секция "Emergency Procedures"
- [x] T043b [US4] Добавить smoke test для rollback: `tests/smoke/test_rollback.sh`

**Checkpoint**: US-4 завершён — push в main автоматически деплоит на VPS

---

## Phase 7: User Story 5 — Настройка мониторинга и алертов (Priority: P2) 📊

**Goal**: Grafana dashboards + Alertmanager для проактивного обнаружения проблем

**Independent Test**: Открыть Grafana, убедиться что dashboards показывают данные

### Implementation для User Story 5

- [x] T044 [P] [US5] Создать `config/monitoring/prometheus.yml` с scrape configs для backend и streamer
- [x] T045 [P] [US5] Создать `config/monitoring/alertmanager.yml` с Telegram receiver
- [x] T046 [P] [US5] Создать `config/monitoring/rules/critical.yml` с alert rules (StreamerDown, HighErrorRate)
- [x] T047 [P] [US5] Создать `config/monitoring/rules/warning.yml` с alert rules (HighLatency, BufferUnderruns)
- [x] T048 [US5] Создать Grafana дашборд `config/monitoring/grafana/dashboards/streamer-overview.json` (provisioning via JSON, не через UI)
- [x] T049 [US5] Добавить prometheus service в `docker-compose.yml` с volume для rules
- [x] T050 [US5] Добавить grafana service в `docker-compose.yml` на порту 3001
- [x] T051 [US5] Добавить alertmanager service в `docker-compose.yml`
- [x] T052 [US5] Добавить prometheus, grafana, alertmanager в internal network
- [x] T053 [US5] Добавить grafana в external network для доступа с frontend

**Checkpoint**: US-5 завершён — Grafana показывает метрики, алерты настроены

---

## Phase 8: User Story 6 — Рефакторинг schedule.py (Priority: P3) 📦

**Goal**: Разбить 997-строчный файл на модули <300 строк каждый

**Independent Test**: Все существующие тесты schedule API проходят без изменений

### Implementation для User Story 6

- [x] T054 [US6] Создать `backend/src/api/schedule/__init__.py` с re-exports для backward compatibility
- [x] T055 [US6] Создать `backend/src/api/schedule/router.py` (~50 строк) с агрегацией роутеров
- [x] T056 [US6] Вынести slots endpoints в `backend/src/api/schedule/slots.py` (~200 строк): get_schedule_slots, create_schedule_slot, update_schedule_slot, delete_schedule_slot, copy_schedule
- [x] T057 [US6] Вынести templates endpoints в `backend/src/api/schedule/templates.py` (~200 строк): get_templates, create_template, apply_template, delete_template
- [x] T058 [US6] Вынести playlists endpoints в `backend/src/api/schedule/playlists.py` (~200 строк): get_playlists, create_playlist, update_playlist, delete_playlist
- [x] T059 [US6] Вынести utility functions в `backend/src/api/schedule/utils.py`: parse_time, format_time, check_slot_overlap
- [x] T060 [US6] Вынести Pydantic schemas в `backend/src/api/schedule/schemas.py`
- [x] T061 [US6] Обновить импорты в `backend/src/main.py` для использования нового модуля
- [x] T062 [US6] Удалить старый `backend/src/api/schedule.py` после подтверждения тестов
- [x] T063 [US6] Запустить `pytest tests/api/test_schedule*.py` для проверки совместимости

**Checkpoint**: US-6 завершён — schedule модуль разбит, все тесты проходят ✅

---

## Phase 9: User Story 7 — Добавление Storybook для UI компонентов (Priority: P3) 📚

**Goal**: Интерактивная документация UI компонентов

**Independent Test**: Запустить `npm run storybook`, все компоненты отображаются корректно

### Implementation для User Story 7

- [x] T064 [US7] Инициализировать Storybook: `cd frontend && npx storybook@latest init --type react --builder vite`
- [x] T065 [US7] Настроить `.storybook/main.ts` с путями к stories и addons
- [x] T066 [US7] Настроить `.storybook/preview.ts` с TailwindCSS и темой
- [X] T067 [P] [US7] Создать `frontend/src/components/ui/Pagination.stories.tsx`
- [X] T068 [P] [US7] Создать `frontend/src/components/ui/PasswordInput.stories.tsx`
- [X] T069 [P] [US7] Создать `frontend/src/components/ui/Skeleton.stories.tsx`
- [X] T070 [US7] Добавить npm script `storybook` в `frontend/package.json`
- [X] T071 [US7] Добавить npm script `build-storybook` в `frontend/package.json`

**Checkpoint**: US-7 завершён — Storybook запускается на порту 6006

---

## Phase 10: User Story 8 — Настройка Code Coverage (Priority: P3) 📈

**Goal**: Coverage reports для backend (≥70%) и frontend (≥60%)

**Independent Test**: Запустить `pytest --cov` и `npm run test:coverage`, отчёты генерируются

### Implementation для User Story 8

- [x] T072 [P] [US8] Настроить pytest-cov в `backend/pyproject.toml` с threshold 70%
- [x] T073 [P] [US8] Настроить vitest coverage в `frontend/vitest.config.ts` с threshold 60%
- [x] T074 [US8] Добавить npm script `test:coverage` в `frontend/package.json`
- [x] T075 [US8] Добавить coverage check в `.github/workflows/ci.yml` для backend
- [x] T076 [US8] Добавить coverage check в `.github/workflows/ci.yml` для frontend
- [x] T077 [US8] Добавить `.gitignore` entries для `htmlcov/`, `coverage/`, `.coverage`
- [x] T078 [US8] Создать baseline coverage report и сохранить в `.internal/coverage-baseline.md`

**Checkpoint**: US-8 завершён — coverage enforced в CI

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Финальные улучшения, затрагивающие несколько user stories

- [x] T079 [P] Обновить `docs/README.md` со ссылками на новую документацию
- [x] T080 [P] Обновить `ai-instructions/` с информацией о новых возможностях
- [x] T081 Запустить `npm run docs:validate` и исправить broken links
- [ ] T082 Выполнить полный smoke test: `docker compose up -d && docker compose ps`
- [ ] T083 Проверить Trivy security scan: `trivy config docker-compose.yml`
- [ ] T084 Запустить полный тест suite: `pytest && npm run test && npm run test:e2e`
- [ ] T085 Обновить `OUTSTANDING_TASKS_REPORT.md` с выполненными задачами
- [ ] T086 Выполнить валидацию по quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────► Phase 2: Foundational
                                       │
                                       ▼
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
             Phase 3: US-1      Phase 4: US-2      Phase 5-7: US-3,4,5
             (Security P1)      (Deprecated P1)    (Infrastructure P2)
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                                       ▼
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
             Phase 8: US-6      Phase 9: US-7      Phase 10: US-8
             (Refactor P3)      (Storybook P3)     (Coverage P3)
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                                       ▼
                              Phase 11: Polish
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US-1 (Security) | Foundational | US-2 |
| US-2 (Deprecated) | Foundational | US-1 |
| US-3 (Health) | Foundational | US-4, US-5 |
| US-4 (CD Pipeline) | Foundational | US-3, US-5 |
| US-5 (Monitoring) | Foundational | US-3, US-4 |
| US-6 (Refactor) | US-2 (clean code base) | US-7, US-8 |
| US-7 (Storybook) | Foundational | US-6, US-8 |
| US-8 (Coverage) | Foundational | US-6, US-7 |

### Within Each User Story

1. Tests (если есть) ДОЛЖНЫ быть написаны и FAIL до реализации
2. Models/Schemas до Services
3. Services до Endpoints
4. Core implementation до интеграции
5. Story complete до перехода к следующему приоритету

---

## Parallel Opportunities

### P1 Priority (US-1 + US-2 параллельно)

```bash
# Developer A: Security (US-1)
T011 → T012 → T013 → T014 → T015 → T016

# Developer B: Deprecated code (US-2)  
T017, T018, T019, T020, T021 [all parallel] → T022 → T023 → T024
```

### P2 Priority (US-3 + US-4 + US-5 параллельно)

```bash
# Developer A: Health Checks (US-3)
T025 → T026-T029 → T030-T035

# Developer B: CD Pipeline (US-4)
T036 → T037-T042 → T043

# Developer C: Monitoring (US-5)
T044-T047 [parallel] → T048 → T049-T053
```

### P3 Priority (US-6 + US-7 + US-8 параллельно)

```bash
# Developer A: Refactoring (US-6)
T054 → T055 → T056-T060 [parallel] → T061 → T062 → T063

# Developer B: Storybook (US-7)
T064 → T065-T066 → T067-T069 [parallel] → T070-T071

# Developer C: Coverage (US-8)
T072, T073 [parallel] → T074 → T075-T076 → T077-T078
```

---

## Implementation Strategy

### MVP First (US-1 + US-2 Only)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational
3. Complete Phase 3: US-1 (Security)
4. Complete Phase 4: US-2 (Deprecated)
5. **STOP and VALIDATE**: Trivy scan + pytest -W error::DeprecationWarning
6. **MVP DEPLOYED**: Security fixed, no deprecated warnings

### Incremental Delivery

| Increment | Stories | Delivered Value |
|-----------|---------|-----------------|
| MVP | US-1, US-2 | Безопасность + Чистый код |
| v1.1 | + US-3, US-4 | Health checks + Auto-deploy |
| v1.2 | + US-5 | Мониторинг и алерты |
| v1.3 | + US-6, US-7, US-8 | Качество кода |

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 88 |
| Phase 1 (Setup) | 6 tasks |
| Phase 2 (Foundational) | 3 tasks |
| US-1 (Security P1) | 7 tasks |
| US-2 (Deprecated P1) | 8 tasks |
| US-3 (Health P2) | 11 tasks |
| US-4 (CD Pipeline P2) | 10 tasks |
| US-5 (Monitoring P2) | 10 tasks |
| US-6 (Refactor P3) | 10 tasks |
| US-7 (Storybook P3) | 8 tasks |
| US-8 (Coverage P3) | 7 tasks |
| Phase 11 (Polish) | 8 tasks |

### Parallel Opportunities

- **Setup Phase**: 5 из 6 tasks [P]
- **P1 Priority**: US-1 и US-2 полностью параллельны
- **P2 Priority**: US-3, US-4, US-5 полностью параллельны
- **P3 Priority**: US-6, US-7, US-8 полностью параллельны
- **Within Stories**: Множество [P] tasks внутри каждой story

### Independent Test Criteria

| Story | Independent Test |
|-------|-----------------|
| US-1 | Trivy scan passes, no socket mount, networks isolated |
| US-2 | `pytest -W error::DeprecationWarning` passes |
| US-3 | All services reach healthy status in 2 min |
| US-4 | Push to main triggers successful deploy |
| US-5 | Grafana dashboards show live data |
| US-6 | All schedule tests pass after refactor |
| US-7 | `npm run storybook` opens on port 6006 |
| US-8 | Coverage reports generate with thresholds |

### Format Validation

✅ Все 88 tasks следуют формату: `- [ ] [TaskID] [P?] [Story?] Description with file path`

---

## Notes

- [P] tasks = разные файлы, нет зависимостей
- [Story] label связывает task с конкретной user story для трейсинга
- Каждая user story может быть завершена и протестирована независимо
- Коммит после каждой task или логической группы
- Остановка на любом checkpoint для валидации story независимо
- Избегать: расплывчатых tasks, конфликтов в одном файле, cross-story зависимостей
