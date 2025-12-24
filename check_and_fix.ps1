# Check current backend env
Write-Host "=== Current backend GOOGLE_REDIRECT_URI ===" -ForegroundColor Cyan
docker exec telegram-backend-1 printenv GOOGLE_REDIRECT_URI

Write-Host "`n=== Recreating backend with new env ===" -ForegroundColor Cyan
docker compose up -d --force-recreate backend

Start-Sleep -Seconds 5

Write-Host "`n=== New backend GOOGLE_REDIRECT_URI ===" -ForegroundColor Cyan
docker exec telegram-backend-1 printenv GOOGLE_REDIRECT_URI

Write-Host "`n=== Building frontend ===" -ForegroundColor Cyan
Set-Location frontend
npm run build 2>&1 | Select-Object -Last 5
Set-Location ..

Write-Host "`n=== Restarting frontend ===" -ForegroundColor Cyan
docker compose restart frontend

Write-Host "`n=== Testing OAuth URL ===" -ForegroundColor Cyan
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/google" -MaximumRedirection 0 -ErrorAction SilentlyContinue
$location = $response.Headers.Location
if ($location -match "redirect_uri=([^&]+)") {
    $redirectUri = [System.Web.HttpUtility]::UrlDecode($matches[1])
    Write-Host "Redirect URI: $redirectUri" -ForegroundColor Green
}

Write-Host "`n=== DONE! ===" -ForegroundColor Green
Write-Host "Try: https://isographical-shawnta-sortably.ngrok-free.dev/" -ForegroundColor Yellow
