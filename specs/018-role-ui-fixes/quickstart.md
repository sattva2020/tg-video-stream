# Quickstart: Role-Based UI/UX Fixes

**Feature**: 018-role-ui-fixes  
**Date**: 2025-12-02

---

## Быстрый старт разработки

### Шаг 1: Переключение на ветку

```bash
git checkout 018-role-ui-fixes
cd frontend
npm install
```

### Шаг 2: Запуск dev-сервера

```bash
npm run dev
```

Frontend доступен на http://localhost:5173

### Шаг 3: Тестовые аккаунты

| Роль | Email | Пароль |
|------|-------|--------|
| SUPERADMIN | admin@sattva.local | *(из .env)* |
| ADMIN | moderator+admin@test.local | test123 |
| MODERATOR | moderator@test.local | test123 |
| OPERATOR | operator@test.local | test123 |
| USER | user@test.local | test123 |

**Note**: Создать тестовые аккаунты через sqladmin если не существуют.

---

## Порядок реализации (по приоритету)

### Sprint 1: P0 Fixes (Critical)

1. **Создать `utils/roleHelpers.ts`**
   - Функции `isAdminLike()`, `canControlStream()`
   - Константы `ADMIN_LIKE_ROLES`, `STREAM_CONTROL_ROLES`

2. **Исправить `DashboardPage.tsx`**
   - Заменить условие на `isAdminLike(user?.role)`
   - Добавить проверку MODERATOR

3. **Исправить `DesktopNav.tsx` и `MobileNav.tsx`**
   - Добавить проверку SUPERADMIN в фильтр
   - Добавить атрибут `moderatorAllowed` к NavItem

4. **Изменить роут /admin в `App.tsx`**
   - Редирект на /dashboard вместо старого Dashboard

### Sprint 2: P1-P2 Features

5. **Удалить `pages/admin/Dashboard.tsx`**
   - Убрать импорт из App.tsx
   - Удалить файл

6. **Создать `OperatorDashboard.tsx`**
   - Переиспользовать StreamStatusCard
   - Добавить QuickActions (только Stream control)

7. **Обновить `DashboardPage.tsx`**
   - Добавить условие для OPERATOR

### Sprint 3: P3 Improvements

8. **Улучшить `UserDashboard.tsx`**
   - Добавить контент в Welcome Card
   - Добавить быстрые действия

---

## Проверка изменений

### Чеклист тестирования

```
[ ] SUPERADMIN видит AdminDashboardV2
[ ] SUPERADMIN видит все админ-пункты в навигации
[ ] ADMIN видит AdminDashboardV2
[ ] ADMIN видит все админ-пункты в навигации
[ ] MODERATOR видит AdminDashboardV2
[ ] MODERATOR НЕ видит вкладку Users
[ ] OPERATOR видит OperatorDashboard
[ ] OPERATOR может запустить/остановить стрим
[ ] USER видит UserDashboard
[ ] /admin редиректит на /dashboard
[ ] MobileNav показывает те же пункты, что и DesktopNav
[ ] Light/Dark тема переключается без артефактов
```

### Команды тестирования

```bash
# Unit тесты
npm run test

# E2E тесты
npm run test:e2e

# Lint
npm run lint
```

### Happy Path by Role

| Роль | Действия | Ожидаемый результат |
|------|----------|---------------------|
| SUPERADMIN | Login → DesktopNav | Видит AdminDashboardV2, все adminOnly пункты, Users таб активен |
| ADMIN | Login → DesktopNav → MobileNav | Одинаковый список ссылок; Users таб активен |
| MODERATOR | Login → Dashboard → QuickActions | Видит AdminDashboardV2 без Users, QuickActions: Stream/Restart/Playlist |
| OPERATOR | Login → Dashboard → Stream controls | Отображается OperatorDashboard, доступны Play/Stop/Restart, нет Users |
| USER | Login → Dashboard | Welcome Card с советами, 3 быстрых действия |

### Device & Theme Checklist

1. Переключить тему (иконка солнце/луна) и убедиться, что AdminDashboardV2/OperatorDashboard/UserDashboard используют CSS переменные без цветовых артефактов.
2. Проверить DesktopNav при ширине ≥1024px и MobileNav при ширине <1024px — состав пунктов должен совпадать.
3. На мобильном открыть/закрыть дровер клавиатурой (`Tab`, `Enter`).
4. Включить/выключить WebSocket (переключить сеть) и убедиться, что баннер «Подключение потеряно» появляется у операторов/модераторов.

---

## Структура файлов после реализации

```
frontend/src/
├── types/
│   ├── user.ts              # UserRole enum (существует)
│   ├── navigation.ts        # NavItem interface (NEW)
│   └── permissions.ts       # RolePermissions (NEW)
├── utils/
│   ├── roleHelpers.ts       # isAdminLike(), etc. (NEW)
│   └── navigationHelpers.ts # filterNavItems() (NEW)
├── components/
│   ├── dashboard/
│   │   ├── AdminDashboardV2.tsx    # (существует)
│   │   ├── OperatorDashboard.tsx   # (NEW)
│   │   └── UserDashboard.tsx       # (изменён)
│   └── layout/
│       ├── DesktopNav.tsx   # (изменён)
│       └── MobileNav.tsx    # (изменён)
├── pages/
│   ├── DashboardPage.tsx    # (изменён)
│   └── admin/
│       └── Dashboard.tsx    # УДАЛЁН
└── App.tsx                  # (изменён - роут /admin)
```

---

## Полезные ссылки

- [UI/UX Аудит](../../docs/UI_UX_AUDIT_ROLES.md)
- [Спецификация](./spec.md)
- [Data Model](./data-model.md)
- [Research](./research.md)
