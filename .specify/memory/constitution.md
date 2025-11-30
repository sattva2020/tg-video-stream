<!--
Sync Impact Report
- Version change: none → 1.0.0
- Modified principles:
  • I. Спецификация — единственный источник правды
  • II. Структура репозитория под защитой
  • III. Тесты и наблюдаемость до кода
  • IV. Документация и локализация как часть фичи
  • V. Секреты и окружения под контролем
- Added sections: Delivery Constraints & Technology Guardrails; Development Workflow & Quality Gates
- Removed sections: отсутствуют
- Templates requiring updates:
  • .specify/templates/plan-template.md ✅
  • .specify/templates/spec-template.md ✅
  • .specify/templates/tasks-template.md ✅
- Follow-up TODOs: нет
-->

# Telegram 24/7 Video Streamer Constitution

## Core Principles

### I. Спецификация — единственный источник правды

Каждая работа начинается со спецификации и сопровождается планом, research, data-model,
contracts, quickstart и tasks. Все документы пишутся на русском, содержат измеримые
критерии успеха и независимые пользовательские истории. Любые правки кода или
инфраструктуры, не имеющие отражения в соответствующих arтефактах, блокируются на
ревью. Feature branches обязаны ссылаться на ID спецификации.

### II. Структура репозитория под защитой

Корень хранит только критические файлы: код в `backend/`, `frontend/`, `streamer/`,
утилиты в `scripts/`, документацию в `docs/`, артефакты фич — в `specs/[###-feature]/`.
Временные файлы и журналы переносятся в `.internal/` (в `.gitignore`). Тесты располагаются
исключительно в `tests/` (и подпапках), окружение описывается через `template.env`,
настройка пайплайнов и конфигов выносится в профильные каталоги.

### III. Тесты и наблюдаемость до кода

Пишем тесты и диагностические крючки до реализации. Backend покрывается pytest, frontend —
Playwright/Vitest, стример — smoke/интеграционными скриптами в `tests/`. Каждый PR
предоставляет инструкции по запуску тестов и настраивает структурированное логирование
(stdout + JSON). Без красных тестов новая реализация не начинается.

### IV. Документация и локализация как часть фичи

Документация в `docs/` и `ai-instructions/` обновляется в той же ветке, что и код. Все
технические тексты ведутся на русском. После изменений запускаются `npm run docs:validate`
и `npm run docs:report`, результаты фиксируются. Появление новой зависимости, сервиса или
конфигурации без отражения в документации запрещено.

### V. Секреты и окружения под контролем

Секреты генерируются только через template-based процесс: `template.env → .env` с
обновлением плейсхолдеров и добавлением новых переменных сначала в шаблон, затем в фактический
файл. Нельзя коммитить `.env`, jwt, session strings или systemd юниты с секретами. Любые
скрипты авторизации (Pyrogram, Telethon) документируются и проверяются на минимально
необходимые права.

## Delivery Constraints & Technology Guardrails

- Backend: Python 3.11+, FastAPI, SQLAlchemy/Alembic, PostgreSQL, uvicorn, pytest.
- Frontend: Node 20+, Vite + React 18 + TypeScript, TailwindCSS, React Three Fiber,
  i18next, Playwright, https://github.com/Jpisnice/shadcn-ui-mcp-server. Все UI компоненты локализуемые и доступные (WCAG AA).
- Streaming: Pyrogram + PyTgCalls + FFmpeg + yt-dlp. Только systemd-процессы или Docker
  сервисы с перезапуском `always`.
- CI/CD: GitHub Actions (или эквивалент) запускает lint + tests + docs validate. Deploy
  скрипты (`scripts/deploy_*.sh`) не изменяются без сопровождающих rollback-инструкций.
- Performance: стример удерживает 720p при 2 vCPU / 4 GB RAM, backend отвечает <200 мс p95,
  frontend загружается <2 с на 4G. Отклонения фиксируются отдельными задачами.

## Development Workflow & Quality Gates

1. **Инициирование**: пользовательский запрос оформляется через `/speckit.spec`. Спецификация
   проходит ревью на полноту пользовательских историй, edge cases, успех.
2. **Планирование**: `/speckit.plan` заполняет plan/research/data-model/contracts/quickstart и
   фиксирует Constitution Check (пункты I–V). Без пройденного гейта разработка запрещена.
3. **Задачи**: `/speckit.tasks` создает tasks.md, группируя работу по user stories и отмечая,
   какие тесты/доки требуются.
4. **Реализация**: код + тесты + документация обновляются параллельно. Все временные файлы —
   в `.internal/`. Новые конфиги — в `config/` или профильных директориях.
5. **Валидация**: перед PR выполняются `npm run docs:validate`, профильные тесты (`pytest`,
   `npm run test`, `npx playwright test`, smoke-скрипты). Логи запуска сохраняются в
   `tests/smoke/logs` или `.internal/` (приватно).
6. **Релиз**: deploy-скрипты обновляются только при наличии rollback-плана и ссылок на tasks.

## Governance

- Конституция превосходит любые локальные практики. Любое отступление требует документа
  "Constitution Deviation" в `specs/[###-feature]/` и утверждения ответственным.
- Версионирование: semantic versioning (MAJOR несовместимые изменения, MINOR — новые
  принципы/секций, PATCH — уточнения). Правки фиксируются в Sync Impact Report (см. комментарий
  выше) и в changelog ветки.
- Амандменты: PR с изменениями в этой конституции обязан перечислить обновляемые принципы,
  затронутые шаблоны и инструкции. После merge дата `Last Amended` обновляется, а команда
  уведомляется в release notes.
- Соблюдение: каждая проверка plan/tasks и каждый code review подтверждает прохождение гейтов
  I–V. Несоответствия открывают bug/tech debt задачу в `OUTSTANDING_TASKS_REPORT.md`.

**Version**: 1.0.0 | **Ratified**: 2025-11-22 | **Last Amended**: 2025-11-22
