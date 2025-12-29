@echo off
REM Start local development environment
echo Starting Telegram Streamer Local Development...
echo.

echo [1/3] Starting PostgreSQL...
docker start telegram-postgres >nul 2>&1 || docker run -d --name telegram-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=telegram_db -p 54320:5432 postgres:15-alpine
echo PostgreSQL started on port 54320

echo.
echo [2/3] Starting Redis...
docker start telegram-redis-1 >nul 2>&1
echo Redis started on port 6379

echo.
echo [3/3] Starting Backend API...
cd backend
set DATABASE_URL=postgresql://postgres:postgres@localhost:54320/telegram_db
start "Backend API" cmd /k "..\venv\Scripts\python.exe run.py --host 0.0.0.0 --port 8000"

echo.
echo [4/4] Starting Frontend...
cd ..\frontend
start "Frontend Dev" cmd /k "npm run dev"

echo.
echo ====================================
echo All services started!
echo ====================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Health:   http://localhost:8000/api/health
echo ====================================
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:3000
