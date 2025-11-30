# Quickstart / Tests — User Approval feature

Steps to run locally (backend + frontend) and execute tests for this feature.

Prerequisites:
- Python 3.11
- Node 20+
- Docker + docker-compose (optional)
- PostgreSQL running (or use test DB in CI)

Backend dev (from repo root):

```bash
# create venv, install deps
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements-dev.txt

# create a test database and point DATABASE_URL accordingly in .env (use template.env)
cd backend
alembic upgrade head  # apply migrations including user status column

# run tests
pytest tests/test_user_approval.py
```

Frontend dev (from repo root):

```bash
cd frontend
npm install
npx playwright test tests/e2e/approval.spec.ts -b chromium
```

Notes:
- Make sure `backend` server is running for frontend e2e tests or configure test mocks accordingly.
- Tests must be added in both `backend/tests/` and `frontend/tests/e2e/` before implementing functional code.

Worker / Notifications (dev):

If you want to run background workers locally for testing notifications using Celery + Redis:

```bash
# start Redis (example using docker)
docker run -p 6379:6379 -d redis:7

# start the worker from repo root
cd backend
export CELERY_BROKER_URL=redis://localhost:6379/0
celery -A src.celery_app.celery_app worker --loglevel=info
```

Environment variables for admin notifications (add to `template.env`):

- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, ADMIN_NOTIFICATION_EMAILS
- TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_IDS
