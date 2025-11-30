# telegram Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-22

## Active Technologies
- Python 3.11+ (Backend), Node 20+ (Frontend) + FastAPI, SQLAlchemy, Alembic, React, Vite (006-user-roles-rbac)
- PostgreSQL (006-user-roles-rbac)
- Python 3.11 (backend) / Node 20+ + React 18 + TypeScript (frontend) + FastAPI, SQLAlchemy, Alembic, PostgreSQL (backend); Vite, React, TypeScript, Playwright (frontend) (007-user-approval)
- PostgreSQL (users table) (007-user-approval)
- TypeScript 5.x, React 18 + TailwindCSS, Framer Motion, React Three Fiber, i18next, React Hook Form, Zod (008-auth-page-design)
- N/A (Frontend state only) (008-auth-page-design)
- TypeScript 5.4 + React 18 + Vite 5 (frontend), CSS custom properties для темизации. + TailwindCSS, React Three Fiber (3D фон), Aceternity UI, Magic UI, Hero UI, Zustand (state), i18next для текста. (008-auth-page-design)
- N/A — используем существующие API `/api/auth/*`. (008-auth-page-design)
- Python 3.12+ (Backend/Streamer), Node 20+ (Frontend) + FastAPI, SQLAlchemy, Pyrogram, PyTgCalls, React, Vite, TailwindCSS (009-complete-admin-ops)
- PostgreSQL (Backend), Redis (Metrics/Status), File System (Playlist) (009-complete-admin-ops)
- Python 3.12 (Backend/Streamer), Node 20+ (Frontend) (011-advanced-audio)
- PostgreSQL (Backend) for playlist persistence. (011-advanced-audio)
- Python 3.11+, Node 20+, TypeScript 5.x + FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.x, React 18, Vite 5, TailwindCSS (012-project-improvements)
- PostgreSQL 15, Redis 7 (012-project-improvements)
- Python 3.11+ (backend), TypeScript 5.x (frontend) + FastAPI, SQLAlchemy, React 18, Vite, TailwindCSS (013-telegram-login)
- PostgreSQL 15+ (новые поля: telegram_id, telegram_username) (013-telegram-login)

- TypeScript 5.x + React 18 (Vite toolchain, Node 18 LTS) + Tailwind CSS, React Three Fiber + Drei, i18next, Framer Motion (existing), Vite build system (001-modern-home-design)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

npm test; npm run lint

## Code Style

TypeScript 5.x + React 18 (Vite toolchain, Node 18 LTS): Follow standard conventions

## Recent Changes
- 013-telegram-login: Added Python 3.11+ (backend), TypeScript 5.x (frontend) + FastAPI, SQLAlchemy, React 18, Vite, TailwindCSS
- 012-project-improvements: Added Python 3.11+, Node 20+, TypeScript 5.x + FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.x, React 18, Vite 5, TailwindCSS
- 011-advanced-audio: Added Python 3.12 (Backend/Streamer), Node 20+ (Frontend)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
