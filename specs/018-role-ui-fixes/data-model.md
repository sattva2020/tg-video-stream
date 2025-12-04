# Data Model: Role-Based UI/UX Fixes

**Feature**: 018-role-ui-fixes  
**Date**: 2025-12-02  
**Status**: Complete

---

## Entities

### UserRole (Existing)

```typescript
// frontend/src/types/user.ts
export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin',
  MODERATOR = 'moderator',
  OPERATOR = 'operator',
}
```

**No changes required** — роли уже определены.

---

### NavItem (Extended)

```typescript
// frontend/src/types/navigation.ts (NEW)
export interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
  moderatorAllowed?: boolean;  // NEW: если true, модератор видит этот пункт
  // operatorAllowed removed — OPERATOR получает отдельный OperatorDashboard, навигация не требуется для MVP
}
```

---

### RolePermissions (NEW)

```typescript
// frontend/src/types/permissions.ts (NEW)
export interface RolePermissions {
  canViewAdminDashboard: boolean;
  canManageUsers: boolean;
  canManagePlaylist: boolean;
  canControlStream: boolean;
  canViewMonitoring: boolean;
  canAccessSqlAdmin: boolean;
}

export const ROLE_PERMISSIONS: Record<UserRole, RolePermissions> = {
  [UserRole.SUPERADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: true,
  },
  [UserRole.ADMIN]: {
    canViewAdminDashboard: true,
    canManageUsers: true,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.MODERATOR]: {
    canViewAdminDashboard: true,
    canManageUsers: false,
    canManagePlaylist: true,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.OPERATOR]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: true,
    canViewMonitoring: true,
    canAccessSqlAdmin: false,
  },
  [UserRole.USER]: {
    canViewAdminDashboard: false,
    canManageUsers: false,
    canManagePlaylist: false,
    canControlStream: false,
    canViewMonitoring: false,
    canAccessSqlAdmin: false,
  },
};
```

---

## Role Hierarchy

```
SUPERADMIN
    │
    ├── ADMIN
    │      │
    │      └── MODERATOR
    │             │
    │             └── OPERATOR
    │
    └── USER (отдельная ветка, не иерархия)
```

---

## Dashboard Selection Logic

```typescript
// frontend/src/utils/roleHelpers.ts (NEW)

export const ADMIN_LIKE_ROLES = [
  UserRole.SUPERADMIN,
  UserRole.ADMIN,
  UserRole.MODERATOR,
];

export const STREAM_CONTROL_ROLES = [
  ...ADMIN_LIKE_ROLES,
  UserRole.OPERATOR,
];

export function isAdminLike(role: UserRole | undefined): boolean {
  return role ? ADMIN_LIKE_ROLES.includes(role) : false;
}

export function canControlStream(role: UserRole | undefined): boolean {
  return role ? STREAM_CONTROL_ROLES.includes(role) : false;
}

export function getDashboardComponent(role: UserRole | undefined): DashboardType {
  if (!role) return 'UserDashboard';
  
  if (ADMIN_LIKE_ROLES.includes(role)) return 'AdminDashboardV2';
  if (role === UserRole.OPERATOR) return 'OperatorDashboard';
  return 'UserDashboard';
}
```

---

## Navigation Filter Logic

```typescript
// frontend/src/utils/navigationHelpers.ts (NEW)

export function filterNavItems(
  items: NavItem[], 
  userRole: UserRole | undefined
): NavItem[] {
  return items.filter(item => {
    // Публичные пункты — всегда видны
    if (!item.adminOnly) return true;
    
    // Проверка роли для админ-пунктов
    const role = userRole || UserRole.USER;
    
    // SUPERADMIN и ADMIN видят все админ-пункты
    if ([UserRole.SUPERADMIN, UserRole.ADMIN].includes(role)) {
      return true;
    }
    
    // MODERATOR видит пункты с moderatorAllowed
    if (role === UserRole.MODERATOR && item.moderatorAllowed) {
      return true;
    }
    
    // OPERATOR не видит adminOnly пункты — получает отдельный OperatorDashboard
    
    return false;
  });
}
```

- **DesktopNav / MobileNav** импортируют `filterNavItems()` и передают один и тот же массив `navItems`, поэтому список ссылок гарантированно идентичен на любых устройствах.

### Navigation Inventory

| Path | Label key | Icon | adminOnly | moderatorAllowed | Roles |
|------|-----------|------|-----------|------------------|-------|
| `/dashboard` | `nav.dashboard` | Home | ❌ | — | Все |
| `/channels` | `nav.channels` | Tv | ❌ | — | Все |
| `/playlist` | `nav.playlist` | ListMusic | ❌ | — | Все |
| `/schedule` | `nav.schedule` | CalendarDays | ❌ | — | Все |
| `/admin` | `nav.admin` | Settings | ✅ | ❌ | ADMIN, SUPERADMIN |
| `/admin/pending` | `nav.pendingUsers` | Users | ✅ | ❌ | ADMIN, SUPERADMIN |
| `/admin/monitoring` | `nav.monitoring` | Activity | ✅ | ✅ | ADMIN, SUPERADMIN, MODERATOR |
| `/settings` | `nav.settings` | Settings | ❌ | — | Все |

### Quick Actions Matrix

| Role | Visible Quick Actions |
|------|----------------------|
| SUPERADMIN | stream-toggle, restart, users, playlist, settings |
| ADMIN | stream-toggle, restart, users, playlist, settings |
| MODERATOR | stream-toggle, restart, playlist |
| OPERATOR | stream-toggle, restart |
| USER | channels, settings, help |

### Fallback Behaviour

- Если `user` отсутствует, `DashboardPage` сначала показывает Skeleton, затем вызывает `getDashboardComponent(undefined)` → `UserDashboard`.
- Неизвестные значения `role` (например, `"guest"`) также приводят к `UserDashboard`. Событие логируется.
- При смене роли backend выставляет `role_changed`, фронтенд очищает сессию и предлагает перелогин.

---

## State Transitions

### Смена роли пользователя

```
[Current Session] → [Role Changed in DB] → [User Logs Out] → [User Logs In] → [New Role Applied]
```

**Note**: Роль НЕ меняется во время активной сессии (текущее поведение).

---

## Validation Rules

1. **Role не может быть NULL**: Fallback на `UserRole.USER`
2. **Unknown role**: Fallback на `UserRole.USER`
3. **adminOnly + no role**: Скрыть пункт меню
4. **Operator without stream access**: Показать OperatorDashboard даже если стрим недоступен

---

## Relationships

```
User ──(has)──> UserRole ──(grants)──> RolePermissions
                   │
                   └──(filters)──> NavItem[]
                   │
                   └──(selects)──> Dashboard
```
