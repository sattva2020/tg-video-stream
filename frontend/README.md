# tg-video-stream

Development helper scripts
--------------------------

There are helper scripts to run the frontend reliably in dev:

- `npm run dev` — default Vite dev server (localhost:3000)
- `npm run dev:host` — run Vite and bind to 0.0.0.0 (helps in some environments)
- `npm run dev:keep` — run a keep-alive wrapper which automatically restarts Vite if it exits unexpectedly and writes logs to `.internal/frontend-logs/` (or `frontend/logs/` for public artifacts by agreement)

Logs directory is ignored by git (see root `.gitignore`).

If you'd like, I can also add a VS Code Dev Container config so the environment runs the same for all developers.
