# Release Gate Checklist: Auth Page Design

**Purpose**: Проверить полноту и качество требований (FR/SC/EC + backend контракт) перед релизом фичи авторизации.
**Created**: 2025-11-24
**Feature**: `specs/008-auth-page-design/spec.md`

**Note**: Чеклист сгенерирован `/speckit.checklist` и покрывает UI, backend-контракты и нефункциональные требования (перфоманс, доступность, TTI/Lighthouse).

## Requirement Completeness

- [x] CHK001 Указаны требования к фону/шрифтам/формам (spec §FR-001..FR-003) и им соответствуют задачи T012–T014. 
- [x] CHK002 Dual-theme описана в spec §US4/FR-006/FR-007 + plan summary; Phase 6 задач хватает (T028–T033).
- [x] CHK003 FR-008 + контракт auth-ui.yaml + задачи T007/T023a/T026 фиксируют API и pytest.
- [x] CHK004 Edge cases EC-001..004 расписаны, задачи T017a/T019/T020/T032/T032 покрывают их.


- [x] CHK005 Spec/plan используют конкретные шрифты/цвета (LandingSans/Serif, ink/parchment) без субъективных оценок.
- [x] CHK006 SC-005 задаёт <200 мс и сохранение в localStorage, а Tasks T028/T030/T032 описывают методику замера.
- [x] CHK007 SC-004 и T017/T017a фиксируют ширины 320/280px и отсутствие горизонтального скролла.
## Requirement Clarity
- [x] CHK008 Контракт AuthError определяет обязательные `code` и `hint`, а также допускает либо `message` (локализованный текст), либо `message_key` (ключ локализации) — это согласовано с планом и задачами.

## Requirement Consistency

- [x] CHK009 Spec FR-006/FR-007 и Tasks Phase 6 теперь согласованы (ThemeToggle только в US4).
- [x] CHK010 US2/SC-003 + Tasks Phase 4 (T017–T021) и Lighthouse цели в Plan §Technical Context синхронизированы.
- [x] CHK011 FR-008/US3 описывают `code`/`hint` и опционально `message` или `message_key`, согласуясь с контрактом/задачами T023a/T026.

## Acceptance Criteria Quality

- [x] CHK012 SC-001 проверяется Playwright тестом T010 и докой T016 со скриншотами.
- [x] CHK013 SC-002/003 опираются на Lighthouse (T002/T034) и TTI оптимизацию (T019) — инструменты описаны.
- [x] CHK014 US4 acceptance описывает auto/persist toggle, а T028/T031/T032 проверяют хранение + sync HeroPanel.

## Scenario Coverage

- [x] CHK015 Каждая US (1–4) имеет собственные Тесты (Playwright/Vitest) в Tasks Phases 3–6.
- [x] CHK016 US3 + контракт описывают 403/409, Tasks T023/T023a/T024/T025 покрывают UI и backend.
- [x] CHK017 EC-001/002 в spec и T019/T020 обеспечивают fallback/TTI <2с.

## Edge Case Coverage

- [x] CHK018 T017a + T032 проверяют sub-320 layout и конфликт тем с подсказкой.
- [x] CHK019 5xx не входят в объём фичи (SC и FR ограничены 403/409), фиксируем это в заметке: `Нефункциональные 5xx обрабатываются глобально и не входят в scope 008`.


- [x] CHK020 SC-002/003 + Tasks T002/T034 описывают Lighthouse/TTI пороги и сохранение отчётов.
- [x] CHK021 EC-002 + Plan summary фиксируют ленивую загрузку 3D и требования к TTI, дополнительных ограничений не требуется, отмечено.
## Non-Functional Requirements
 - [x] CHK022 T003/T034 и плановый гейт III обязывают хранить логи в `.internal/frontend-logs/` (публичные артефакты — `frontend/logs/` только по согласованию).

## Dependencies & Assumptions

- [x] CHK023 План §Technical Context и T001 перечисляют все новые пакеты и их назначение.
- [x] CHK024 Spec FR-008 и Tasks T023/T023a подразумевают использование реальных статус/role/seed; assumption отражён в data-model (User.status/role).
- [x] CHK025 План (принцип IV) и задачи T016/T021/T027/T033/T035 требуют обновлять docs/quickstart при изменениях.

## Ambiguities & Conflicts

- [x] CHK026 Обновлённые разделы зависимостей в plan/tasks теперь совпадают (US2/US4 стартуют после US1).
- [x] CHK027 Data-model описывает fallback (исп. email), поэтому SC-006 остаётся выполнимой; отметить проверочным кейсом в документации.
- [x] CHK028 В рамках scope допускаются только `pending/rejected/conflict/server`; rate limit/5xx ведёт к generic `server`, что задокументировано.

## Notes

- Отмечайте выполненные пункты `[x]` и добавляйте комментарии с ссылками на PR/коммиты.
- При выявлении пробелов создавайте задачи в `tasks.md`/`OUTSTANDING_TASKS_REPORT.md` с конкретными действиями.
