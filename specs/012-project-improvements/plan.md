# Implementation Plan: План улучшения проекта 24/7 TV Telegram

**Branch**: `012-project-improvements` | **Date**: 29.11.2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-project-improvements/spec.md`

## Summary

План устранения критических уязвимостей безопасности, модернизации deprecated кода и внедрения
production-grade инфраструктуры для 24/7 Telegram Video Streamer.

**Ключевые направления**:
1. **P1 Security & Modernization**: Удаление Docker socket mount, изоляция сетей, миграция на SQLAlchemy 2.0 DeclarativeBase и Pydantic v2 ConfigDict
2. **P2 Infrastructure**: Docker health checks, CD pipeline на VPS 37.53.91.144, Grafana/Alertmanager мониторинг с MTTR ≤ 15 мин
3. **P3 Quality**: Рефакторинг schedule.py (997→<300 строк/модуль), Storybook для UI, coverage ≥70%

**Технический подход**: Параллельная работа над задачами внутри приоритета. P1 → P2 → P3.

## Technical Context

**Language/Version**: Python 3.11+, Node 20+, TypeScript 5.x  
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.x, React 18, Vite 5, TailwindCSS  
**Storage**: PostgreSQL 15, Redis 7  
**Testing**: pytest (backend), Vitest (unit), Playwright (E2E), smoke scripts  
**Target Platform**: VPS Linux (Ubuntu 22.04), Docker 24+  
**Project Type**: Web application (backend + frontend + streamer)  
**Performance Goals**: Backend <200ms p95, Frontend <2s load (4G), Streamer 720p@2vCPU/4GB  
**Constraints**: MTTR ≤15 min, CI/CD <15 min merge-to-deploy, Coverage ≥70%  
**Scale/Scope**: Single VPS deployment, 24/7 uptime requirement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** ✅ — спецификация на русском с 8 независимыми user stories,
   измеримыми критериями успеха (SC-001..SC-009), ссылками на `docs/PROJECT_AUDIT_REPORT.md`.
   Clarifications документированы (VPS target, MTTR, execution order).

2. **Структура репозитория соблюдена (Принцип II)** ✅ — все артефакты создаются в
   `specs/012-project-improvements/`, временные файлы для тестирования будут в `.internal/`,
   новые тесты планируются в `tests/`. Мониторинг конфиги — в `config/monitoring/`.

3. **Тесты и наблюдаемость спланированы (Принцип III)** ✅ — конкретные задачи:
   - pytest с `-W error::DeprecationWarning` (US-2)
   - Security scan Trivy (US-1)
   - Health endpoint tests (US-3)
   - CD dry-run smoke tests (US-4)
   - Coverage reports pytest-cov, vitest --coverage (US-8)

4. **Документация и локализация покрыты (Принцип IV)** ✅ — план включает обновления:
   - `docs/development/` — CD pipeline инструкции
   - `docs/architecture/` — сетевая изоляция диаграмма
   - Storybook как живая документация UI (US-7)
   - `npm run docs:validate` выполняется после каждого изменения

5. **Секреты и окружения учтены (Принцип V)** ✅ — план предусматривает:
   - Миграция credentials PostgreSQL в Docker secrets
   - Добавление GRAFANA_ADMIN_PASSWORD, ALERTMANAGER_WEBHOOK в `template.env`
   - SSH deploy key для CD в GitHub Secrets (не в репо)

## Project Structure

### Documentation (this feature)

```text
specs/012-project-improvements/
├── plan.md              # This file
├── research.md          # Phase 0: Docker security, SQLAlchemy 2.0, Grafana best practices
├── data-model.md        # Phase 1: Health endpoint schema, Alert rules schema
├── quickstart.md        # Phase 1: Quick start guide для новых разработчиков
├── contracts/           # Phase 1: OpenAPI health endpoints, Prometheus metrics spec
│   ├── health-api.yaml
│   └── metrics-spec.md
└── tasks.md             # Phase 2: Grouped tasks by User Story
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── schedule.py      # → РЕФАКТОРИНГ: разбить на slots.py, templates.py, playlists.py
│   │   ├── health.py        # НОВЫЙ: /health endpoint
│   │   └── ...
│   ├── models/
│   │   └── base.py          # ИЗМЕНЕНИЕ: DeclarativeBase вместо declarative_base()
│   ├── database.py          # ИЗМЕНЕНИЕ: миграция на SQLAlchemy 2.0
│   └── ...
└── tests/
    ├── api/
    │   └── test_health.py   # НОВЫЙ: health endpoint tests
    └── ...

frontend/
├── src/
│   ├── components/
│   │   └── ui/              # TARGET: Storybook stories для всех компонентов
│   └── ...
├── .storybook/              # НОВЫЙ: Storybook конфигурация
└── tests/

config/                      # НОВЫЙ каталог
├── monitoring/
│   ├── prometheus.yml
│   ├── alertmanager.yml
│   └── grafana/
│       └── dashboards/
│           └── streamer-overview.json
└── docker/
    └── networks.yml         # Docker network definitions

.github/
└── workflows/
    ├── ci.yml               # СУЩЕСТВУЮЩИЙ
    ├── cd.yml               # НОВЫЙ: CD pipeline
    └── ...
```

**Structure Decision**: Web application (Option 2) с существующей структурой backend/ + frontend/ + streamer/.
Новые конфигурации мониторинга размещаются в `config/monitoring/` согласно Принципу II.

## Complexity Tracking

> Все принципы Constitution Check пройдены. Нарушений нет.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

---

## Phase 0: Research

### Research Tasks

| ID | Topic | Status | Output |
|----|-------|--------|--------|
| R-001 | Docker socket security alternatives | ✅ DONE | research.md#docker-socket |
| R-002 | Docker network isolation patterns | ✅ DONE | research.md#network-isolation |
| R-003 | SQLAlchemy 2.0 migration guide | ✅ DONE | research.md#sqlalchemy-migration |
| R-004 | Pydantic v2 ConfigDict migration | ✅ DONE | research.md#pydantic-migration |
| R-005 | Docker health check best practices | ✅ DONE | research.md#health-checks |
| R-006 | GitHub Actions CD to VPS patterns | ✅ DONE | research.md#cd-pipeline |
| R-007 | Grafana + Prometheus + Alertmanager setup | ✅ DONE | research.md#monitoring-stack |
| R-008 | Python file refactoring patterns | ✅ DONE | research.md#refactoring |
| R-009 | Storybook 7+ React setup | ✅ DONE | research.md#storybook |
| R-010 | pytest-cov + vitest coverage integration | ✅ DONE | research.md#coverage |

---

## Phase 1: Design & Contracts

### Entities (data-model.md)

| Entity | Source | Fields |
|--------|--------|--------|
| HealthResponse | US-3 | status, version, uptime, dependencies[] |
| DependencyHealth | US-3 | name, status, latency_ms, message? |
| AlertRule | US-5 | name, condition, severity, receivers[] |
| CoverageReport | US-8 | total_lines, covered_lines, percentage, by_file[] |

### Contracts (contracts/)

| Contract | Format | User Story |
|----------|--------|------------|
| health-api.yaml | OpenAPI 3.1 | US-3 |
| metrics-spec.md | Prometheus metrics | US-5 |
| cd-workflow.yml | GitHub Actions | US-4 |

### Agent Context Update

После завершения Phase 1:
```bash
./.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot
```

---

## Next Steps

Phase 0 и Phase 1 завершены. Сгенерированные артефакты:

- ✅ `plan.md` — Implementation plan с Constitution Check
- ✅ `research.md` — Исследование всех технических решений
- ✅ `data-model.md` — Схемы данных для новых entities
- ✅ `contracts/health-api.yaml` — OpenAPI спецификация health endpoints
- ✅ `contracts/metrics-spec.md` — Prometheus metrics спецификация
- ✅ `quickstart.md` — Руководство быстрого старта
- ✅ Agent context обновлён через `update-agent-context.ps1`

**Следующий шаг**: Запустить `/speckit.tasks` для генерации `tasks.md`
