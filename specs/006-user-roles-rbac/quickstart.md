# Quickstart: User Roles (RBAC)

## Prerequisites

- Backend running
- Database accessible

## 1. Apply Migrations

```bash
cd backend
alembic upgrade head
```

## 2. Create Admin User

1. Register a new user via the frontend or API.
2. Run the promotion script:

```bash
# Windows (PowerShell)
cd backend
$env:PYTHONPATH="src"
python ../scripts/create_admin.py --email admin@example.com

# Linux/Bash
cd backend
PYTHONPATH=src python ../scripts/create_admin.py --email admin@example.com
```

## 3. Verify Access

1. Login as the promoted user.
2. Check that you can access admin features.
3. Login as a regular user.
4. Check that admin features are hidden/inaccessible.
