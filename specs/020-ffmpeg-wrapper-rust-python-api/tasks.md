# Tasks: Rust FFmpeg Microservice

**Input**: Design documents from `/specs/020-ffmpeg-wrapper-rust-python-api/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅, quickstart.md ✅

**Tests**: Тесты включены (контрактные и интеграционные) для каждой user story.

**Organization**: Задачи сгруппированы по user story для независимой имплементации и тестирования.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно запускать параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой user story относится задача (US1, US2, US3, US4)
- Пути указаны относительно корня репозитория

## Path Conventions

- **Rust microservice**: `rust-transcoder/src/`
- **Python orchestrator**: `streamer/`
- **Tests Rust**: `rust-transcoder/tests/`
- **Tests Python**: `streamer/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Инициализация Rust проекта и базовая структура

- [X] T001 Создать директорию rust-transcoder/ с базовой структурой (src/, tests/)
- [X] T002 Инициализировать Cargo.toml с зависимостями (axum, tokio, serde, uuid, tracing) в rust-transcoder/Cargo.toml
- [X] T003 [P] Создать Dockerfile для Rust-сервиса с multi-stage build в rust-transcoder/Dockerfile
- [X] T004 [P] Настроить clippy и rustfmt конфигурацию в rust-transcoder/.rustfmt.toml и rust-transcoder/clippy.toml
- [X] T005 [P] Создать .gitignore для Rust проекта в rust-transcoder/.gitignore
- [X] T006 Добавить rust-transcoder сервис в docker-compose.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Базовая инфраструктура Rust-сервиса, которая ДОЛЖНА быть готова ДО начала user stories

**⚠️ CRITICAL**: Работа над user stories не может начаться до завершения этой фазы

- [X] T007 Создать main.rs с базовым Axum сервером (bind на 0.0.0.0:8090) в rust-transcoder/src/main.rs
- [X] T008 [P] Создать модуль api/mod.rs с маршрутизацией в rust-transcoder/src/api/mod.rs
- [X] T009 [P] Создать модуль models/mod.rs для Request/Response типов в rust-transcoder/src/models/mod.rs
- [X] T010 [P] Создать модуль transcoder/mod.rs для транскодирования в rust-transcoder/src/transcoder/mod.rs
- [X] T011 Настроить tracing и structured logging в rust-transcoder/src/main.rs
- [X] T012 [P] Создать модуль error.rs для структурированных ошибок в rust-transcoder/src/error.rs
- [X] T013 Создать базовые модели TranscodeRequest, AudioFilters, TranscodeError в rust-transcoder/src/models/transcode.rs
- [X] T014 [P] Создать enum OutputFormat (opus, pcm, aac) и EqPreset в rust-transcoder/src/models/enums.rs
- [X] T014.1 Настроить bounded concurrency с tokio::sync::Semaphore (max 50 concurrent) в rust-transcoder/src/main.rs

**Checkpoint**: Foundational ready - можно начинать user stories

---

## Phase 3: User Story 1 - Базовое транскодирование через Rust сервис (Priority: P1) 🎯 MVP

**Goal**: Python-оркестратор отправляет запрос в Rust-сервис, получает транскодированный поток Opus/AAC

**Independent Test**: Отправить HTTP POST /transcode с URL аудиофайла, получить streaming response с корректным форматом

### Tests for User Story 1 ⚠️

> **NOTE: Написать эти тесты ПЕРВЫМИ, убедиться что они FAIL до имплементации**

- [X] T015 [P] [US1] Contract test для POST /transcode в rust-transcoder/tests/contract_transcode_test.rs
- [X] T016 [P] [US1] Unit test для ffmpeg command builder в rust-transcoder/tests/unit_ffmpeg_test.rs

### Implementation for User Story 1

- [X] T017 [US1] Реализовать profiles.rs с TRANSCODING_PROFILES (opus, pcm, aac) в rust-transcoder/src/transcoder/profiles.rs
- [X] T018 [US1] Реализовать ffmpeg.rs с subprocess ffmpeg вызовом в rust-transcoder/src/transcoder/ffmpeg.rs
- [X] T019 [US1] Реализовать transcode.rs endpoint с streaming response в rust-transcoder/src/api/transcode.rs
- [X] T020 [US1] Добавить валидацию TranscodeRequest (URL формат, output_format) в rust-transcoder/src/models/transcode.rs
- [X] T021 [US1] Добавить X-Transcode-Id и X-Source-Format headers в response в rust-transcoder/src/api/transcode.rs
- [X] T022 [US1] Подключить transcode endpoint в api/mod.rs маршрутизацию в rust-transcoder/src/api/mod.rs
- [X] T023 [US1] Добавить logging для всех операций транскодирования в rust-transcoder/src/transcoder/ffmpeg.rs

**Checkpoint**: User Story 1 полностью функциональна — можно отправить запрос и получить Opus поток

---

## Phase 4: User Story 4 - Graceful Degradation (Priority: P2)

**Goal**: При недоступности Rust-сервиса Python автоматически переключается на subprocess ffmpeg

**Independent Test**: Остановить Rust-сервис, проверить что вещание продолжается через fallback

**Примечание**: P2 fallback важнее фильтров (US2), т.к. критичен для production reliability

### Tests for User Story 4 ⚠️

- [X] T024 [P] [US4] Integration test для fallback механизма в streamer/tests/test_transcode_client.py
- [X] T025 [P] [US4] Unit test для retry/circuit breaker логики в streamer/tests/test_fallback.py

### Implementation for User Story 4

- [X] T026 [US4] Создать transcode_client.py с httpx async клиентом в streamer/transcode_client.py
- [X] T027 [US4] Реализовать fallback на subprocess ffmpeg при connection error в streamer/transcode_client.py
- [X] T028 [US4] Добавить retry logic с exponential backoff в streamer/transcode_client.py
- [X] T029 [US4] Добавить circuit breaker pattern для переключения между Rust и subprocess в streamer/transcode_client.py
- [X] T030 [US4] Интегрировать transcode_client в main.py вместо прямого subprocess в streamer/main.py
- [X] T031 [US4] Добавить logging для fallback events с уровнем WARNING в streamer/transcode_client.py
- [X] T032 [US4] Добавить конфигурацию RUST_TRANSCODER_URL в environment в streamer/transcode_client.py

**Checkpoint**: User Stories 1 AND 4 работают — транскодирование через Rust + fallback

---

## Phase 5: User Story 2 - Применение аудио-фильтров (Priority: P2)

**Goal**: Поддержка speed и EQ параметров в запросах транскодирования

**Independent Test**: Отправить запрос с speed=1.25 и eq_preset=bass_boost, проверить что ffmpeg применяет фильтры

### Tests for User Story 2 ⚠️

- [X] T033 [P] [US2] Contract test для /transcode с фильтрами в rust-transcoder/tests/contract_filters_test.rs
- [X] T034 [P] [US2] Unit test для filters.rs в rust-transcoder/tests/unit_filters_test.rs

### Implementation for User Story 2

- [X] T035 [US2] Реализовать filters.rs с EQ presets (flat, bass_boost, voice, treble) в rust-transcoder/src/transcoder/filters.rs
- [X] T036 [US2] Добавить speed filter (atempo) в ffmpeg command builder в rust-transcoder/src/transcoder/ffmpeg.rs
- [X] T037 [US2] Добавить валидацию speed (0.5-2.0) и volume (0.0-2.0) в rust-transcoder/src/models/transcode.rs
- [X] T038 [US2] Интегрировать фильтры в transcode endpoint в rust-transcoder/src/api/transcode.rs
- [X] T039 [US2] Обновить Python клиент для передачи фильтров в streamer/transcode_client.py
- [X] T040 [US2] Добавить error handling для FILTER_INVALID в rust-transcoder/src/error.rs

**Checkpoint**: Фильтры работают — speed, EQ, volume применяются к потоку

---

## Phase 6: User Story 3 - Мониторинг и метрики (Priority: P3)

**Goal**: /health и /metrics endpoints для production мониторинга

**Independent Test**: Запросить /metrics, проверить наличие active_streams, transcode_latency_ms

### Tests for User Story 3 ⚠️

- [ ] T041 [P] [US3] Contract test для GET /health в rust-transcoder/tests/contract_health_test.rs
- [ ] T042 [P] [US3] Contract test для GET /metrics в rust-transcoder/tests/contract_metrics_test.rs

### Implementation for User Story 3

- [ ] T043 [US3] Реализовать health.rs endpoint с ServiceHealth response в rust-transcoder/src/api/health.rs
- [ ] T044 [US3] Добавить version, uptime_seconds, ffmpeg_version в /health в rust-transcoder/src/api/health.rs
- [ ] T045 [US3] Реализовать metrics.rs endpoint в Prometheus формате в rust-transcoder/src/api/metrics.rs
- [ ] T046 [US3] Добавить метрики: transcode_requests_total, active_streams, transcode_latency_ms в rust-transcoder/src/api/metrics.rs
- [ ] T047 [US3] Подключить /health и /metrics в api/mod.rs маршрутизацию в rust-transcoder/src/api/mod.rs
- [ ] T048 [US3] Добавить graceful shutdown handling (SIGTERM) в rust-transcoder/src/main.rs

**Checkpoint**: Все user stories работают — можно мониторить сервис

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Улучшения затрагивающие несколько user stories

- [ ] T049 [P] Обновить README.md с инструкциями по запуску Rust-сервиса
- [ ] T050 [P] Добавить документацию API в docs/api/rust-transcoder.md
- [ ] T051 Code cleanup: убрать дублирование между profiles.rs и audio_utils.py
- [ ] T052 [P] Добавить unit tests для всех enums в rust-transcoder/tests/unit_enums_test.rs
- [ ] T053 Проверить quickstart.md — все примеры должны работать
- [ ] T054 [P] Обновить конфигурацию Prometheus для scrape rust-transcoder:8090/metrics
- [ ] T055 Security: проверить что source_url не позволяет SSRF (file://, internal IPs)
- [ ] T056 [P] Benchmark: замерить latency старта транскодирования (SC-001: <200ms) в rust-transcoder/tests/benchmark_latency.rs
- [ ] T057 [P] Benchmark: замерить memory usage при 10 concurrent streams (SC-002: <256MB)
- [ ] T058 Load test: проверить 50 concurrent streams (SC-006) с k6 или wrk

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Нет зависимостей — можно начинать сразу
- **Foundational (Phase 2)**: Зависит от Setup — БЛОКИРУЕТ все user stories
- **User Stories (Phase 3+)**: Все зависят от завершения Foundational
  - User stories могут идти параллельно (если несколько разработчиков)
  - Или последовательно по приоритету (P1 → P2 → P3)
- **Polish (Phase 7)**: Зависит от завершения всех желаемых user stories

### User Story Dependencies

- **User Story 1 (P1)**: Может начаться после Foundational — Нет зависимостей от других stories
- **User Story 4 (P2)**: Зависит от US1 (нужен работающий Rust endpoint для тестирования fallback)
- **User Story 2 (P2)**: Может начаться после Foundational — независима от других stories
- **User Story 3 (P3)**: Может начаться после Foundational — независима от других stories

### Within Each User Story

- Tests ДОЛЖНЫ быть написаны и FAIL до имплементации
- Models перед services
- Services перед endpoints
- Core implementation перед integration
- Story complete перед переходом к следующему приоритету

### Parallel Opportunities

- Все Setup задачи с [P] могут идти параллельно
- Все Foundational задачи с [P] могут идти параллельно (внутри Phase 2)
- После Foundational: US1, US2, US3 могут идти параллельно (US4 ждёт US1)
- Все тесты для одной story с [P] могут идти параллельно

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T015: "Contract test для POST /transcode в rust-transcoder/tests/contract_transcode_test.rs"
Task T016: "Unit test для ffmpeg command builder в rust-transcoder/tests/unit_ffmpeg_test.rs"

# After tests written (and failing), launch implementation:
Task T017: "Реализовать profiles.rs с TRANSCODING_PROFILES"
Task T018: "Реализовать ffmpeg.rs с subprocess ffmpeg вызовом"
# T019+ depend on T017, T018
```

---

## Parallel Example: Multiple User Stories

```bash
# After Foundational complete, launch in parallel:
# Developer A: User Story 1 (P1 - MVP)
# Developer B: User Story 2 (P2 - Filters)
# Developer C: User Story 3 (P3 - Metrics)

# Note: User Story 4 (Fallback) должна ждать завершения US1
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T014)
3. Complete Phase 3: User Story 1 (T015-T023)
4. **STOP and VALIDATE**: Тест POST /transcode независимо
5. Deploy/demo если готово

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP!)
3. Add User Story 4 (Fallback) → Test → Deploy (Production-ready!)
4. Add User Story 2 (Filters) → Test → Deploy
5. Add User Story 3 (Metrics) → Test → Deploy
6. Каждая story добавляет ценность без поломки предыдущих

### Parallel Team Strategy

С несколькими разработчиками:

1. Команда вместе завершает Setup + Foundational
2. После Foundational:
   - Developer A: User Story 1 (MVP)
   - Developer B: User Story 2 (Filters)
   - Developer C: User Story 3 (Metrics)
3. После US1 готова: Developer A → User Story 4 (Fallback)
4. Stories завершаются и интегрируются независимо

---

## Task Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Phase 1: Setup | T001-T006 (6) | T003, T004, T005 parallel |
| Phase 2: Foundational | T007-T014.1 (9) | T008, T009, T010, T012, T014 parallel |
| Phase 3: US1 (MVP) | T015-T023 (9) | T015, T016 parallel; T017, T018 parallel |
| Phase 4: US4 (Fallback) | T024-T032 (9) | T024, T025 parallel |
| Phase 5: US2 (Filters) | T033-T040 (8) | T033, T034 parallel |
| Phase 6: US3 (Metrics) | T041-T048 (8) | T041, T042 parallel |
| Phase 7: Polish | T049-T058 (10) | T049, T050, T052, T054, T056, T057 parallel |
| **Total** | **58 tasks** | |

### Tasks per User Story

| User Story | Priority | Tasks | Independent Test Criteria |
|------------|----------|-------|---------------------------|
| US1: Базовое транскодирование | P1 | 9 | POST /transcode → Opus stream |
| US4: Fallback | P2 | 9 | Stop Rust → Python fallback works |
| US2: Фильтры | P2 | 8 | speed=1.25 + eq_preset → correct output |
| US3: Метрики | P3 | 8 | GET /metrics → Prometheus format |

### Suggested MVP Scope

Для минимального рабочего продукта достаточно:
- Phase 1: Setup (6 tasks)
- Phase 2: Foundational (8 tasks)
- Phase 3: US1 (9 tasks)

**MVP Total: 23 tasks**

После MVP рекомендуется сразу добавить US4 (Fallback) для production reliability.

---

## Notes

- [P] tasks = разные файлы, нет зависимостей
- [Story] label связывает задачу с конкретной user story для трассировки
- Каждая user story должна быть независимо завершаема и тестируема
- Проверить что тесты fail до имплементации
- Commit после каждой задачи или логической группы
- Остановиться на любом checkpoint для валидации story
- Избегать: размытых задач, конфликтов в одном файле, cross-story зависимостей

