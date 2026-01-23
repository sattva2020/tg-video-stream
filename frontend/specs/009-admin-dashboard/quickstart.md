# Quickstart: Admin Dashboard

**Feature**: `009-admin-dashboard`

## Prerequisites

- Backend running: `python backend/run.py`
- Frontend running: `npm run dev` (in `frontend/`)
- Admin user created: `python backend/scripts/create_admin.py <your-email>`

## Running the Feature

1. **Login as Admin**:
   - Go to `http://localhost:5173/login`
   - Login with your admin credentials.
   - You should see the **Admin Dashboard** with "Overview", "Users", "Stream" tabs.

2. **Login as User**:
   - Open an Incognito window.
   - Register a new account.
   - Login.
   - You should see the **User Dashboard** (Profile only).

3. **Approve User**:
   - In Admin Dashboard, go to "Users" tab.
   - Find the new user (Status: `pending`).
   - Click "Approve".
   - Status should change to `approved`.

## Testing

### UI Tests (Playwright)

```bash
cd frontend
npx playwright test tests/playwright/admin-dashboard.spec.ts
```

### API Tests (pytest)

```bash
cd backend
pytest tests/test_admin_api.py
```
