# Implementation Plan: Role-Based UI/UX Fixes

**Branch**: `018-role-ui-fixes` | **Date**: 2025-12-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-role-ui-fixes/spec.md`

---

## Summary

Исправление критических багов в логике определения ролей пользователей на фронтенде. MODERATOR и SUPERADMIN не получают корректный доступ к административным функциям из-за неполных проверок ролей. Требуется:
- Исправить условия в DashboardPage, DesktopNav, MobileNav
- Добавить роут-редирект для /admin
- Создать OperatorDashboard для роли OPERATOR
- Улучшить UserDashboard контентом

---

## Technical Context

**Language/Version**: TypeScript 5.x, React 18.x  
**Primary Dependencies**: @heroui/react, framer-motion, react-router-dom, i18next  
**Storage**: N/A (frontend-only changes)  
**Testing**: Vitest, Playwright (E2E)  
**Target Platform**: Web (Desktop + Mobile responsive)  
**Project Type**: Web application (frontend + backend)  
**Performance Goals**: N/A (UI bugfixes, no performance requirements)  
**Constraints**: Обратная совместимость с существующими сессиями  
**Scale/Scope**: 5 ролей пользователей, ~10 компонентов затронуты

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| No new libraries | ✅ PASS | Используем существующие зависимости |
| Reuse existing patterns | ✅ PASS | Расширение NavItem interface |
| Test coverage | ⏳ PENDING | Unit тесты для roleHelpers |
| i18n support | ✅ PASS | Новые строки добавляются в локали |
| Accessibility | ✅ PASS | Используем Hero UI с a11y |

---

## Project Structure

### Documentation (this feature)

```text
specs/018-role-ui-fixes/
├── spec.md              # Feature specification ✅
├── plan.md              # This file ✅
├── research.md          # Phase 0 output ✅
├── data-model.md        # Phase 1 output ✅
├── quickstart.md        # Phase 1 output ✅
├── contracts/           # Phase 1 output ✅
│   └── api-contracts.md
├── checklists/
│   └── requirements.md  # Quality checklist ✅
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── types/
│   │   ├── user.ts              # UserRole enum (exists)
│   │   ├── navigation.ts        # NavItem interface (NEW)
│   │   └── permissions.ts       # RolePermissions (NEW)
│   ├── utils/
│   │   ├── roleHelpers.ts       # isAdminLike(), etc. (NEW)
│   │   └── navigationHelpers.ts # filterNavItems() (NEW)
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── AdminDashboardV2.tsx    # (exists)
│   │   │   ├── OperatorDashboard.tsx   # (NEW)
│   │   │   └── UserDashboard.tsx       # (modify)
│   │   └── layout/
│   │       ├── DesktopNav.tsx   # (modify)
│   │       └── MobileNav.tsx    # (modify)
│   ├── pages/
│   │   ├── DashboardPage.tsx    # (modify)
│   │   └── admin/
│   │       └── Dashboard.tsx    # DELETE
│   └── App.tsx                  # (modify - route)
└── tests/
    └── unit/
        └── roleHelpers.test.ts  # (NEW)
```

**Structure Decision**: Web application (Option 2) — изменения только в frontend/.

---

## Complexity Tracking

> **No violations detected**

Используем существующие паттерны и библиотеки. Новых архитектурных решений не требуется.

---

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

- [x] Проанализированы текущие роли в `types/user.ts`
- [x] Изучена логика DashboardPage.tsx
- [x] Изучена логика DesktopNav/MobileNav
- [x] Определено решение для каждой проблемы
- [x] Документация: `research.md`

### Phase 1: Design ✅ COMPLETE

- [x] Расширен NavItem interface
- [x] Создан RolePermissions типы
- [x] Спроектированы helper-функции
- [x] Определена логика фильтрации навигации
- [x] Документация: `data-model.md`, `contracts/`, `quickstart.md`

### Phase 2: Tasks (Next: /speckit.tasks)

Ожидает генерации через `/speckit.tasks` command.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Регрессия AdminDashboardV2 | Low | High | Unit тесты для roleHelpers |
| sqladmin конфликт с /admin | Low | Medium | Frontend /admin — редирект |
| Незатестированные edge cases | Medium | Medium | E2E тесты для каждой роли |
| Breaking change для SUPERADMIN | Low | High | Тестирование перед merge |

---

## Next Steps

1. Выполнить `/speckit.tasks` для генерации задач
2. Создать feature branch (уже создан: 018-role-ui-fixes)
3. Реализовать Sprint 1 (P0 критические баги)
4. Тестирование всех 5 ролей
5. Code review и merge

---

## References

- [UI/UX Аудит](../../docs/UI_UX_AUDIT_ROLES.md)
- [Feature Spec](./spec.md)
- [Research](./research.md)
- [Data Model](./data-model.md)
- [Quickstart](./quickstart.md)
