# Feature Specification: План улучшения проекта 24/7 TV Telegram

**Feature Branch**: `012-project-improvements`  
**Created**: 29.11.2025  
**Status**: Draft  
**Input**: User description: "на основании аудита docs/PROJECT_AUDIT_REPORT.md разработать план улучшения проекта"

> ⚖️ Конституция: все текстовые блоки заполняем на русском. Каждая пользовательская история
> должна быть независимой, иметь измеримые критерии успеха и ссылаться на будущие тесты и
> документацию, иначе `/speckit.plan` не пройдет гейт.

## Clarifications

### Session 2025-11-29

- Q: Какой целевой хост используется для CD deployment (staging/production)? → A: VPS сервер 37.53.91.144 (существующий из SSH-конфигурации)
- Q: Какой целевой показатель MTTR для мониторинга? → A: MTTR ≤ 15 минут (абсолютный показатель)
- Q: Как выполнять User Stories — последовательно или параллельно? → A: Параллельно внутри приоритета (P1 → P2 → P3, задачи одного приоритета параллельно)
- Q: Как измерять "Performance degradation ≤5%" в SC-001? → A: Baseline = среднее время ответа `/health` endpoint из последних 1000 запросов до начала изменений. Измерение: k6 load test с 50 concurrent users, 60 секунд. Формула: `(new_avg - baseline_avg) / baseline_avg * 100 ≤ 5%`. Сохранить baseline в `.internal/performance-baseline.json` перед началом работ.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Устранение критических уязвимостей безопасности (Priority: P1)

Как **DevOps-инженер**, я хочу устранить критические уязвимости инфраструктуры (Docker socket mount, дефолтные credentials, отсутствие сетевой изоляции), чтобы защитить production-среду от потенциальных атак и утечки данных.

**Why this priority**: Безопасность — высший приоритет. Текущая конфигурация позволяет атакующему, получившему доступ к backend-контейнеру, управлять всеми Docker-контейнерами на хосте. Дефолтные credentials PostgreSQL — вектор атаки #1.

**Independent Test**: Можно полностью протестировать независимо — запустить сканер безопасности Trivy/Snyk, проверить отсутствие socket mount, подтвердить использование secrets для credentials.

**Acceptance Scenarios**:

1. **Given** docker-compose.yml развёрнут, **When** проверяю backend service, **Then** отсутствует volume `/var/run/docker.sock`
2. **Given** production environment запущен, **When** проверяю credentials PostgreSQL, **Then** они загружены из Docker secrets или переменных окружения (не hardcoded)
3. **Given** все сервисы запущены, **When** анализирую сетевую топологию, **Then** backend и db находятся в изолированной internal network, frontend — в отдельной сети

---

### User Story 2 - Модернизация deprecated кода (Priority: P1)

Как **Backend-разработчик**, я хочу обновить deprecated код SQLAlchemy и Pydantic до актуальных версий, чтобы избежать проблем совместимости при обновлении зависимостей и устранить warnings.

**Why this priority**: Deprecated код SQLAlchemy 1.x (`declarative_base()`) и Pydantic v1 (`class Config`) вызывает DeprecationWarnings и будет удалён в следующих major версиях. Это блокирует безопасные обновления зависимостей.

**Independent Test**: Можно протестировать независимо — запустить тесты с `-W error::DeprecationWarning`, все должны пройти без предупреждений.

**Acceptance Scenarios**:

1. **Given** backend запущен, **When** выполняю `pytest -W error::DeprecationWarning`, **Then** все тесты проходят без ошибок
2. **Given** исходный код models/, **When** проверяю Base class, **Then** используется `DeclarativeBase` из `sqlalchemy.orm`
3. **Given** Pydantic schemas, **When** проверяю конфигурацию, **Then** используется `model_config = ConfigDict(...)` вместо `class Config`

---

### User Story 3 - Добавление Health Checks в Docker (Priority: P2)

Как **SRE-инженер**, я хочу добавить health checks для всех сервисов в docker-compose, чтобы автоматически обнаруживать неработающие контейнеры и обеспечить корректный порядок запуска.

**Why this priority**: Без health checks Docker не знает реальное состояние сервисов. Это приводит к race conditions при старте (backend стартует раньше готовности PostgreSQL) и затрудняет мониторинг.

**Independent Test**: Можно протестировать независимо — запустить `docker compose up`, дождаться healthy статуса всех сервисов, затем остановить PostgreSQL и убедиться, что backend переходит в unhealthy.

**Acceptance Scenarios**:

1. **Given** docker-compose.yml, **When** запускаю `docker compose up -d`, **Then** все сервисы достигают статуса `healthy` в течение 2 минут
2. **Given** backend контейнер запущен, **When** выполняю `docker inspect backend`, **Then** вижу настроенный healthcheck с endpoint `/health`
3. **Given** PostgreSQL остановлен, **When** жду 30 секунд, **Then** backend показывает статус `unhealthy`

---

### User Story 4 - Внедрение CD Pipeline (Priority: P2)

Как **DevOps-инженер**, я хочу автоматизировать deployment через CD pipeline (GitHub Actions) на VPS сервер 37.53.91.144, чтобы избежать ручных ошибок при деплое и ускорить доставку изменений в production.

**Why this priority**: Текущий CI проверяет код, но деплой выполняется вручную. Это источник ошибок и задержек. Автоматический CD — стандарт индустрии.

**Independent Test**: Можно протестировать независимо — создать тестовый тег `v0.0.1-test`, убедиться что workflow запускается и выполняет deploy на VPS (или dry-run).

**Acceptance Scenarios**:

1. **Given** пуш в main ветку с прошедшими тестами, **When** workflow завершён, **Then** VPS 37.53.91.144 обновлён до последней версии
2. **Given** создан release tag `v*.*.*`, **When** workflow завершён, **Then** production environment обновлён (с approval gate)
3. **Given** deploy workflow, **When** анализирую логи, **Then** вижу rollback-план в случае ошибки

---

### User Story 5 - Настройка мониторинга и алертов (Priority: P2)

Как **SRE-инженер**, я хочу настроить Grafana dashboards и Alertmanager для ключевых метрик, чтобы проактивно обнаруживать проблемы до того, как они повлияют на пользователей.

**Why this priority**: Streamer уже экспортирует Prometheus метрики, но нет визуализации и алертинга. Без этого проблемы обнаруживаются только когда пользователи жалуются.

**Independent Test**: Можно протестировать независимо — открыть Grafana, убедиться что dashboards показывают данные, симулировать высокую нагрузку и проверить срабатывание alert.

**Acceptance Scenarios**:

1. **Given** Grafana развёрнута, **When** открываю dashboard "Streamer Overview", **Then** вижу метрики stream_uptime, buffer_size, error_rate
2. **Given** error_rate превышает 5% за 5 минут, **When** Alertmanager обрабатывает alert, **Then** уведомление отправлено в настроенный канал (Telegram/Slack)
3. **Given** production environment, **When** открываю Prometheus, **Then** targets показывают UP статус для всех сервисов

---

### User Story 6 - Рефакторинг schedule.py (Priority: P3)

Как **Backend-разработчик**, я хочу разбить `schedule.py` (998 строк) на модули `slots.py`, `templates.py`, `playlists.py`, чтобы улучшить читаемость, тестируемость и возможность параллельной работы.

**Why this priority**: Большой файл затрудняет навигацию, увеличивает merge conflicts и усложняет code review. Однако функциональность работает — это улучшение качества кода, а не исправление багов.

**Independent Test**: Можно протестировать независимо — после рефакторинга все существующие тесты schedule API должны проходить без изменений.

**Acceptance Scenarios**:

1. **Given** backend/src/api/, **When** проверяю структуру, **Then** существуют файлы `slots.py`, `templates.py`, `playlists.py` вместо монолитного `schedule.py`
2. **Given** рефакторинг завершён, **When** запускаю `pytest tests/api/test_schedule*.py`, **Then** все тесты проходят
3. **Given** новая структура, **When** каждый модуль, **Then** не превышает 300 строк

---

### User Story 7 - Добавление Storybook для UI компонентов (Priority: P3)

Как **Frontend-разработчик**, я хочу добавить Storybook для документации UI компонентов, чтобы иметь интерактивную витрину компонентов для дизайнеров и разработчиков.

**Why this priority**: Облегчает onboarding новых разработчиков, позволяет тестировать компоненты изолированно, служит живой документацией design system.

**Independent Test**: Можно протестировать независимо — запустить `npm run storybook`, убедиться что все компоненты из `components/ui/` отображаются корректно.

**Acceptance Scenarios**:

1. **Given** frontend/, **When** запускаю `npm run storybook`, **Then** Storybook открывается на порту 6006 без ошибок
2. **Given** Storybook запущен, **When** открываю категорию "UI Components", **Then** вижу stories для Button, Input, Modal, Card
3. **Given** компонент Button, **When** открываю его story, **Then** вижу варианты: primary, secondary, disabled, loading

---

### User Story 8 - Настройка Code Coverage (Priority: P3)

Как **QA-инженер**, я хочу настроить code coverage для backend и frontend с минимальным порогом 70%, чтобы отслеживать качество тестирования и предотвращать регрессии.

**Why this priority**: Текущие 233 теста — хороший показатель, но без coverage reports неизвестно, какие части кода не покрыты. Это улучшение процесса QA.

**Independent Test**: Можно протестировать независимо — запустить `pytest --cov` и `vitest --coverage`, убедиться что отчёты генерируются.

**Acceptance Scenarios**:

1. **Given** backend тесты, **When** запускаю `pytest --cov=src`, **Then** вижу HTML coverage report в `htmlcov/`
2. **Given** frontend тесты, **When** запускаю `npm run test:coverage`, **Then** вижу coverage report с breakdown по файлам
3. **Given** CI pipeline, **When** coverage падает ниже 70%, **Then** build fails с сообщением о недостаточном покрытии

---

### Edge Cases

- Что происходит при откате миграции после рефакторинга моделей SQLAlchemy?
- Как система обрабатывает ситуацию, когда Grafana/Prometheus недоступны?
- Что если CD pipeline запускается параллельно для двух разных коммитов?
- Как Storybook обрабатывает компоненты с внешними зависимостями (API calls)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Система ДОЛЖНА запускать все Docker-сервисы без монтирования Docker socket в контейнеры
- **FR-002**: Система ДОЛЖНА использовать Docker secrets или environment variables для всех credentials (никаких hardcoded значений)
- **FR-003**: Система ДОЛЖНА изолировать backend и database в отдельную internal Docker network
- **FR-004**: Backend ДОЛЖЕН использовать `DeclarativeBase` из SQLAlchemy 2.0+ вместо deprecated `declarative_base()`
- **FR-005**: Pydantic модели ДОЛЖНЫ использовать `model_config = ConfigDict(...)` вместо `class Config`
- **FR-006**: Каждый Docker-сервис ДОЛЖЕН иметь healthcheck с endpoint проверки
- **FR-007**: CI/CD pipeline ДОЛЖЕН включать автоматический deployment на staging при merge в main
- **FR-008**: CI/CD pipeline ДОЛЖЕН поддерживать production deployment с approval gate для release tags
- **FR-009**: Grafana ДОЛЖНА показывать dashboards с ключевыми метриками streamer
- **FR-010**: Alertmanager ДОЛЖЕН отправлять уведомления при превышении порогов ошибок
- **FR-011**: Модуль `schedule.py` ДОЛЖЕН быть разбит на отдельные файлы (каждый <300 строк)
- **FR-012**: Storybook ДОЛЖЕН документировать все компоненты из `components/ui/`
- **FR-013**: CI pipeline ДОЛЖЕН проверять code coverage и fail при <70%

### Key Entities

- **Docker Network**: Изолированные сети для разделения frontend/backend трафика
- **Health Endpoint**: `/health` endpoint возвращающий статус сервиса и его зависимостей
- **Grafana Dashboard**: JSON-конфигурация панелей мониторинга
- **Alert Rule**: Prometheus alerting rule с условиями срабатывания и receivers
- **Coverage Report**: Артефакт CI с метриками покрытия кода тестами

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Security сканер (Trivy) не обнаруживает HIGH/CRITICAL уязвимостей в Docker конфигурации
- **SC-002**: Все 233+ тестов проходят без DeprecationWarning при запуске с `-W error::DeprecationWarning`
- **SC-003**: Время от merge в main до deployment на staging не превышает 15 минут
- **SC-004**: Dashboard "Streamer Overview" показывает актуальные данные с latency < 30 секунд
- **SC-005**: MTTR (Mean Time To Recovery) при инцидентах не превышает 15 минут благодаря алертам
- **SC-006**: Максимальный размер любого Python-файла в `backend/src/api/` не превышает 300 строк
- **SC-007**: 100% компонентов из `frontend/src/components/ui/` имеют Storybook stories
- **SC-008**: Backend code coverage ≥ 70%, Frontend code coverage ≥ 60%
- **SC-009**: CI/CD pipeline успешно выполняется в 95% случаев (без flaky tests)
