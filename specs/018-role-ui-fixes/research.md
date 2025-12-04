# Research: Role-Based UI/UX Fixes

**Feature**: 018-role-ui-fixes  
**Date**: 2025-12-02  
**Status**: Complete

---

## Research Tasks

### 1. Текущая архитектура ролей

**Вопрос**: Как определены роли в системе?

**Исследование**:
- `frontend/src/types/user.ts` — enum `UserRole` с 5 значениями:
  - `USER = 'user'`
  - `ADMIN = 'admin'`
  - `SUPERADMIN = 'superadmin'`
  - `MODERATOR = 'moderator'`
  - `OPERATOR = 'operator'`

**Решение**: Роли уже определены, структура готова. Проблема в логике проверки.

---

### 2. Логика отображения Dashboard

**Вопрос**: Как выбирается дашборд по роли?

**Исследование** (`frontend/src/pages/DashboardPage.tsx`):
```tsx
{(user?.role === UserRole.ADMIN || user?.role === UserRole.SUPERADMIN) 
  ? <AdminDashboardV2 /> 
  : <UserDashboard />}
```

**Проблема**: MODERATOR и OPERATOR не проверяются, показывается UserDashboard.

**Решение**:
- Создать helper-функцию `hasAdminAccess(role)` или `isAdminLike(role)`
- Добавить MODERATOR в условие для AdminDashboardV2
- Для OPERATOR создать отдельный дашборд или расширить UserDashboard

---

### 3. Логика навигации

**Вопрос**: Как фильтруются пункты меню?

**Исследование** (`DesktopNav.tsx:56`, `MobileNav.tsx:68`):
```tsx
const filteredNavItems = navItems.filter(
  item => !item.adminOnly || user?.role === UserRole.ADMIN
);
```

**Проблема**: Проверяется ТОЛЬКО `UserRole.ADMIN`, игнорируются:
- SUPERADMIN (должен видеть ВСЁ)
- MODERATOR (должен видеть часть)
- OPERATOR (нужно определить)

**Решение**:
```tsx
const ADMIN_ROLES = [UserRole.ADMIN, UserRole.SUPERADMIN];
const MODERATOR_ROLES = [...ADMIN_ROLES, UserRole.MODERATOR];

const filteredNavItems = navItems.filter(item => {
  if (!item.adminOnly) return true;
  if (item.moderatorAllowed) return MODERATOR_ROLES.includes(user?.role);
  return ADMIN_ROLES.includes(user?.role);
});
```

---

### 4. Маршрутизация /admin

**Вопрос**: Куда ведёт /admin и какой компонент используется?

**Исследование** (`frontend/src/App.tsx`):
```tsx
const AdminDashboard = lazy(() => import('./pages/admin/Dashboard'));
// ...
<Route path="/admin" element={<AdminDashboard />} />
```

**Проблема**: `/admin` ведёт на `pages/admin/Dashboard.tsx` (OLD), а не на `AdminDashboardV2`.

**Решение**:
- Вариант A: Перенаправить /admin на /dashboard для админ-ролей
- Вариант B: Заменить импорт на AdminDashboardV2
- Вариант C: Удалить роут /admin полностью

**Выбор**: Вариант A — редирект /admin → /dashboard для простоты.

---

### 5. Компонент OperatorDashboard

**Вопрос**: Какой UI нужен для OPERATOR?

**Исследование** (из аудита):
- Права оператора: Запуск/стоп стрима, очередь, просмотр метрик
- НЕ права: управление пользователями, настройки, плейлист

**Решение**:
- Создать `OperatorDashboard.tsx` — упрощённый дашборд
- Использовать компоненты: `StreamControlPanel`, `QueuePreview`, `StatusCard`
- Импортировать из AdminDashboardV2: `StreamStatusCard`, `QuickActions` (фильтрованные)

---

### 6. UserDashboard улучшения

**Вопрос**: Что добавить в Welcome Card?

**Исследование** (текущее состояние):
- Пустой CardBody
- Только 1 быстрое действие (Менеджер каналов)

**Решение**:
- Добавить статус аккаунта (верификация email, Telegram linking)
- Добавить tips/onboarding советы
- Добавить history последних треков (если API поддерживает)
- Добавить быстрые действия: Настройки, Помощь

---

## Best Practices

### React + TypeScript

1. **Type guards для ролей**: Использовать discriminated unions или type guards
2. **Централизованная проверка ролей**: Один файл `utils/permissions.ts`
3. **Мемоизация**: `useMemo` для filteredNavItems
4. **Lazy loading**: Продолжать использовать для дашбордов

### Hero UI + Tailwind

1. **Консистентные варианты**: Card, Button с одинаковыми стилями
2. **Tailwind breakpoints**: Уже настроены правильно
3. **Dark mode**: CSS variables уже работают

---

## Зависимости

| Зависимость | Статус | Примечание |
|-------------|--------|------------|
| Hero UI | ✅ Установлен | Основные компоненты |
| Framer Motion | ✅ Установлен | Анимации |
| react-router-dom | ✅ Установлен | Роутинг, Navigate |
| i18n | ✅ Настроен | Локализация |

---

## Риски

1. **Обратная совместимость**: Изменение поведения для существующих SUPERADMIN пользователей
   - Митигация: Тестирование всех ролей перед деплоем

2. **sqladmin конфликт**: /admin может конфликтовать с sqladmin
   - Митигация: sqladmin на бэкенде, frontend /admin — редирект

3. **Регрессия AdminDashboardV2**: Изменения могут сломать рабочий функционал
   - Митигация: Unit тесты для role-checking логики

---

## Итоги

Все NEEDS CLARIFICATION разрешены. Готов к Phase 1 (Design).
