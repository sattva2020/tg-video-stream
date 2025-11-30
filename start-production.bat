@echo off
title Telegram Broadcast - Production Server

echo ========================================
echo  Starting Production Servers
echo  Domain: flowbooster.xyz
echo ========================================

:: Kill old processes
echo Stopping old processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

:: Start Backend in new window
echo Starting Backend on port 8000...
start "Backend API" cmd /k "E:\My\Sattva\telegram\venv\Scripts\python.exe E:\My\Sattva\telegram\backend\run.py --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

:: Start Frontend in new window
echo Starting Frontend on port 80...
start "Frontend" cmd /k "cd /d E:\My\Sattva\telegram\frontend && npm run dev -- --port 80 --host 0.0.0.0"

echo.
echo ========================================
echo  Servers started!
echo ========================================
echo  Frontend: http://flowbooster.xyz
echo  Backend:  http://flowbooster.xyz:8000
echo  API Docs: http://flowbooster.xyz:8000/docs
echo ========================================
echo.
echo Press any key to exit this window...
pause >nul
