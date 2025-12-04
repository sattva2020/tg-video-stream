# API Contracts: Role-Based UI/UX Fixes

**Feature**: 018-role-ui-fixes  
**Date**: 2025-12-02

---

## Overview

Данная фича **не требует изменений API**. Все изменения происходят на уровне frontend.

Существующий API уже возвращает роль пользователя в JWT токене и в `/api/auth/me`.

---

## Existing Contracts (No Changes)

### GET /api/auth/me

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "moderator",
  "status": "active",
  "telegram_id": 123456789,
  "telegram_username": "johndoe"
}
```

**role** field values: `"user"`, `"admin"`, `"superadmin"`, `"moderator"`, `"operator"`

---

## Frontend Contracts (Internal)

### Dashboard Selection Contract

```typescript
// Input: UserRole
// Output: React.ComponentType

interface DashboardContract {
  role: UserRole;
  component: 'AdminDashboardV2' | 'OperatorDashboard' | 'UserDashboard';
}

const DashboardMapping: DashboardContract[] = [
  { role: UserRole.SUPERADMIN, component: 'AdminDashboardV2' },
  { role: UserRole.ADMIN, component: 'AdminDashboardV2' },
  { role: UserRole.MODERATOR, component: 'AdminDashboardV2' },
  { role: UserRole.OPERATOR, component: 'OperatorDashboard' },
  { role: UserRole.USER, component: 'UserDashboard' },
];
```

### Navigation Filter Contract

```typescript
// Input: NavItem[], UserRole
// Output: NavItem[]

interface NavFilterContract {
  input: {
    items: NavItem[];
    role: UserRole;
  };
  output: NavItem[];
  rules: [
    'PUBLIC items always included',
    'ADMIN and SUPERADMIN see all adminOnly items',
    'MODERATOR sees adminOnly items with moderatorAllowed=true',
    'OPERATOR does not see adminOnly items (использует отдельный дашборд)',
    'USER sees only PUBLIC items',
  ];
}
```

### Stream Control Endpoints (Existing API)

| Method & Path | Roles | Description |
|---------------|-------|-------------|
| `POST /api/admin/stream/start` | SUPERADMIN, ADMIN, MODERATOR, OPERATOR | Запускает трансляцию. Возвращает `{ status: 'running' }` при успехе. |
| `POST /api/admin/stream/stop` | SUPERADMIN, ADMIN, MODERATOR, OPERATOR | Останавливает трансляцию. Возвращает `{ status: 'stopped' }`. |
| `POST /api/admin/stream/restart` | SUPERADMIN, ADMIN, MODERATOR, OPERATOR | Перезапускает сервис вещания. Возвращает `{ status: 'running', restarted: true }`. |

**Error Contract**: Все три эндпоинта возвращают `409 Conflict` при конфликте статуса и `403 Forbidden` при недостаточных правах. Frontend обязан отображать toast с ключами `admin.streamStartError`, `admin.streamStopError`, `admin.streamRestartError`.

**Timeout Requirement**: Ответ должен приходить < 3 секунд (SC-003). После 3 секунд frontend показывает спиннер и сообщение «Ожидание ответа сервера…».

---

## Notes

- sqladmin использует отдельную сессию и не входит в скоуп этой фичи
- Backend role enforcement уже реализован через middleware
- Frontend только отображает UI на основе роли из токена
