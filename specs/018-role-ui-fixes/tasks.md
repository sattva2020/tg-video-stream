# Tasks: Role-Based UI/UX Fixes

**Feature**: 018-role-ui-fixes  
**Input**: Design documents from `/specs/018-role-ui-fixes/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Не запрошены явно, но добавлены unit-тесты для критичной логики (roleHelpers).

**Organization**: Задачи сгруппированы по User Stories для независимой реализации.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно выполнять параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой User Story относится задача (US1, US2, US3, US4, US5)
- Пути файлов указаны явно

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Создание типов и утилит, общих для всех User Stories

- [X] T001 [P] Create NavItem interface in frontend/src/types/navigation.ts
- [X] T002 [P] Create RolePermissions types in frontend/src/types/permissions.ts
- [X] T003 [P] Create roleHelpers.ts with isAdminLike(), canControlStream(), getDashboardComponent() in frontend/src/utils/roleHelpers.ts
- [X] T004 [P] Create navigationHelpers.ts with filterNavItems() in frontend/src/utils/navigationHelpers.ts
- [X] T005 [P] Create unit tests for roleHelpers in frontend/tests/unit/roleHelpers.test.ts

**Checkpoint**: Базовые типы и утилиты готовы. Можно начинать User Stories.

---

## Phase 2: User Story 1 — Модератор получает доступ к админ-панели (Priority: P0) 🎯 MVP

**Goal**: MODERATOR видит AdminDashboardV2 вместо UserDashboard при входе в систему

**Independent Test**: Войти как MODERATOR → увидеть AdminDashboardV2 → вкладка Users скрыта/неактивна

### Implementation for User Story 1

- [X] T006 [US1] Import isAdminLike from roleHelpers in frontend/src/pages/DashboardPage.tsx
- [X] T007 [US1] Update dashboard selection logic to use isAdminLike() in frontend/src/pages/DashboardPage.tsx
- [X] T008 [US1] Add role prop to AdminDashboardV2 for conditional tab rendering in frontend/src/components/dashboard/AdminDashboardV2.tsx
- [X] T009 [US1] Hide Users tab for MODERATOR in AdminDashboardV2 tabs section in frontend/src/components/dashboard/AdminDashboardV2.tsx
- [X] T010 [US1] Filter QuickActions to hide user management for MODERATOR in frontend/src/components/dashboard/AdminDashboardV2.tsx

**Checkpoint**: MODERATOR видит AdminDashboardV2 без вкладки Users. US1 завершена.

---

## Phase 3: User Story 2 — Суперадмин видит полную навигацию (Priority: P0)

**Goal**: SUPERADMIN видит все adminOnly пункты меню (сейчас проверяется только ADMIN)

**Independent Test**: Войти как SUPERADMIN → все 4+ админ-пункта меню видны в DesktopNav и MobileNav

### Implementation for User Story 2

- [X] T011 [P] [US2] Import filterNavItems from navigationHelpers in frontend/src/components/layout/DesktopNav.tsx
- [X] T012 [P] [US2] Import filterNavItems from navigationHelpers in frontend/src/components/layout/MobileNav.tsx
- [X] T013 [US2] Replace inline filter with filterNavItems() in DesktopNav.tsx
- [X] T014 [US2] Replace inline filter with filterNavItems() in MobileNav.tsx
- [X] T015 [US2] Add moderatorAllowed attribute to navItems for Monitoring route in frontend/src/components/layout/DesktopNav.tsx
- [X] T016 [US2] Add moderatorAllowed attribute to navItems for Monitoring route in frontend/src/components/layout/MobileNav.tsx

**Checkpoint**: SUPERADMIN и MODERATOR видят корректные пункты навигации. US2 завершена.

---

## Phase 4: User Story 3 — Корректная маршрутизация /admin (Priority: P1)

**Goal**: /admin редиректит на /dashboard, старый Dashboard.tsx удалён

**Independent Test**: Открыть /admin → редирект на /dashboard → AdminDashboardV2 отображается

### Implementation for User Story 3

- [X] T017 [US3] Import Navigate from react-router-dom in frontend/src/App.tsx
- [X] T018 [US3] Replace AdminDashboard route with Navigate to /dashboard in frontend/src/App.tsx
- [X] T019 [US3] Remove AdminDashboard lazy import from frontend/src/App.tsx
- [X] T020 [US3] Delete old Dashboard component file frontend/src/pages/admin/Dashboard.tsx

**Checkpoint**: /admin редиректит, старый компонент удалён. US3 завершена.

---

## Phase 5: User Story 4 — Оператор видит панель управления стримами (Priority: P2)

**Goal**: OPERATOR видит OperatorDashboard с контролем стримов

**Independent Test**: Войти как OPERATOR → увидеть панель с кнопками Play/Stop/Restart

### Implementation for User Story 4

- [X] T021 [P] [US4] Create OperatorDashboard.tsx component in frontend/src/components/dashboard/OperatorDashboard.tsx
- [X] T022 [US4] Import StreamStatusCard from AdminDashboardV2 in OperatorDashboard.tsx
- [X] T023 [US4] Create StreamControlActions component with Play/Stop/Restart buttons in OperatorDashboard.tsx
- [X] T024 [US4] Add QuickActions subset (stream controls only) in OperatorDashboard.tsx
- [X] T025 [US4] Update DashboardPage.tsx to render OperatorDashboard for OPERATOR role
- [X] T026 [US4] Add i18n strings for OperatorDashboard in frontend/src/i18n/locales/

**Checkpoint**: OPERATOR видит свою панель с контролом стримов. US4 завершена.

---

## Phase 6: User Story 5 — UserDashboard показывает полезный контент (Priority: P3)

**Goal**: Улучшение UX для обычных пользователей

**Independent Test**: Войти как USER → увидеть контент в Welcome Card, 3+ быстрых действия

### Implementation for User Story 5

- [X] T027 [P] [US5] Create WelcomeCardContent component with account status, tips in frontend/src/components/dashboard/WelcomeCardContent.tsx
- [X] T028 [US5] Integrate WelcomeCardContent into UserDashboard Welcome Card in frontend/src/components/dashboard/UserDashboard.tsx
- [X] T029 [US5] Add quick action links (Settings, Help) to UserDashboard in frontend/src/components/dashboard/UserDashboard.tsx
- [X] T030 [US5] Add i18n strings for new UserDashboard content in frontend/src/i18n/locales/
- [X] T031 [US5] Style WelcomeCardContent with Hero UI and Tailwind in frontend/src/components/dashboard/WelcomeCardContent.tsx

**Checkpoint**: UserDashboard информативен и полезен. US5 завершена.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Финализация и очистка

- [X] T032 [P] Update TypeScript exports in frontend/src/types/index.ts (add navigation.ts, permissions.ts)
- [X] T033 [P] Update utils exports in frontend/src/utils/index.ts (add roleHelpers.ts, navigationHelpers.ts)
- [X] T034 Run quickstart.md validation — test all 5 roles
- [X] T035 Code review: verify all role conditions use helper functions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Нет зависимостей — можно начинать сразу
- **Phase 2-6 (User Stories)**: Все зависят от Phase 1 completion
- **Phase 7 (Polish)**: Зависит от завершения нужных User Stories

### User Story Dependencies

| User Story | Зависит от | Может выполняться параллельно с |
|------------|------------|--------------------------------|
| US1 (MODERATOR) | Phase 1 | US2, US3 |
| US2 (SUPERADMIN nav) | Phase 1 | US1, US3 |
| US3 (/admin route) | Phase 1 | US1, US2 |
| US4 (OPERATOR) | Phase 1 + желательно US1 | US5 |
| US5 (UserDashboard) | Phase 1 | US4 |

### Within Each User Story

1. Imports before logic changes
2. Core logic before UI updates
3. i18n strings after component creation

---

## Parallel Opportunities

### Phase 1 — All tasks parallel:

```bash
T001, T002, T003, T004, T005 # Все файлы разные, можно параллельно
```

### User Story 2 — Imports parallel:

```bash
T011, T012 # DesktopNav и MobileNav — разные файлы
```

### User Story 4 + 5 — Can run in parallel:

```bash
# Team member A: T021-T026 (OperatorDashboard)
# Team member B: T027-T031 (UserDashboard improvements)
```

---

## Implementation Strategy

### MVP First (P0 Critical Bugs)

1. ✅ Complete Phase 1: Setup (T001-T005)
2. ✅ Complete Phase 2: US1 — MODERATOR fix (T006-T010)
3. ✅ Complete Phase 3: US2 — SUPERADMIN nav fix (T011-T016)
4. **STOP and VALIDATE**: Test SUPERADMIN, ADMIN, MODERATOR roles
5. Deploy if ready

### Incremental Delivery

1. **MVP**: Phase 1 + US1 + US2 = Critical bugs fixed
2. **v1.1**: + US3 = Clean routing, no legacy code
3. **v1.2**: + US4 = OPERATOR fully supported
4. **v1.3**: + US5 = User engagement improved

---

## Task Summary

| Phase | Tasks | Priority | Effort |
|-------|-------|----------|--------|
| Setup | T001-T005 | Required | ~1h |
| US1: MODERATOR | T006-T010 | P0 | ~1h |
| US2: SUPERADMIN nav | T011-T016 | P0 | ~1h |
| US3: /admin route | T017-T020 | P1 | ~30m |
| US4: OPERATOR | T021-T026 | P2 | ~2h |
| US5: UserDashboard | T027-T031 | P3 | ~1.5h |
| Polish | T032-T035 | Required | ~30m |

**Total**: 35 tasks, ~7-8 часов работы

---

## Notes

- [P] = параллельные задачи (разные файлы, нет зависимостей)
- [USx] = привязка к User Story для трассировки
- Коммит после каждой завершённой задачи или группы
- P0 баги должны быть исправлены первыми
- Избегать: конфликтов в одном файле, неявных зависимостей между историями
