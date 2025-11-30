Write-Host "Starting SATTVA Development Environment..." -ForegroundColor Cyan

# Start Backend
Write-Host "Launching Backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; py -m uvicorn src.main:app --reload --port 8000" -WindowStyle Normal

# Start Frontend
Write-Host "Launching Frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal

Write-Host "All services launched!" -ForegroundColor Cyan
