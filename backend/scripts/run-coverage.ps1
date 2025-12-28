# Backend Coverage Runner (PowerShell version)
# Запускает тесты 8 приоритетных сервисов с coverage отчётом

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Banner
Write-ColorOutput Blue @"
╔═══════════════════════════════════════════════════════════╗
║         Backend Coverage - Priority Services             ║
║              Target: 98.75% Coverage                     ║
╚═══════════════════════════════════════════════════════════╝
"@

# Check if we're in backend directory
if (-not (Test-Path "pytest.ini")) {
    Write-ColorOutput Red "Error: Not in backend directory. Run this script from backend/"
    exit 1
}

# Check if venv is activated
if (-not $env:VIRTUAL_ENV) {
    Write-ColorOutput Yellow "Warning: Virtual environment not activated"
    Write-Output "Attempting to activate..."
    
    if (Test-Path "..\venv\Scripts\Activate.ps1") {
        & "..\venv\Scripts\Activate.ps1"
    } elseif (Test-Path "..\venv\bin\activate") {
        & "..\venv\bin\activate"
    } else {
        Write-ColorOutput Red "Error: Virtual environment not found"
        exit 1
    }
}

# Run tests
Write-ColorOutput Blue "Running tests for 8 priority services..."
Write-Output ""

python -m pytest `
  tests/test_playback_service.py `
  tests/test_auth_service.py `
  tests/test_session_service.py `
  tests/test_activity_service.py `
  tests/test_telegram_rate_limiter.py `
  tests/test_queue_service.py `
  tests/test_priority_queue_service.py `
  tests/test_channel_service.py `
  --cov=src.services.playback_service `
  --cov=src.services.auth_service `
  --cov=src.services.session_service `
  --cov=src.services.activity_service `
  --cov=src.services.telegram_rate_limiter `
  --cov=src.services.queue_service `
  --cov=src.services.priority_queue_service `
  --cov=src.services.channel_service `
  --cov-report=term-missing `
  --cov-report=html `
  --cov-report=json `
  --cov-branch `
  -v

if ($LASTEXITCODE -eq 0) {
    Write-Output ""
    Write-ColorOutput Green "✅ All tests passed!"
    
    # Parse coverage
    if (Test-Path "coverage.json") {
        Write-Output ""
        Write-ColorOutput Blue "📊 Coverage Summary:"
        python scripts\parse_coverage.py
    }
    
    # Open HTML report
    Write-Output ""
    Write-ColorOutput Blue "📄 HTML report generated: htmlcov/index.html"
    
    # Open in browser
    if (Test-Path "htmlcov\index.html") {
        Write-Output "Opening in browser..."
        Start-Process "htmlcov\index.html"
    }
    
} else {
    Write-Output ""
    Write-ColorOutput Red "❌ Tests failed"
    exit 1
}
