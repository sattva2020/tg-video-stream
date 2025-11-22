<#
Small PowerShell script to create a venv, install dev dependencies and set up pre-commit.
Run from repository root in PowerShell: .\scripts\setup-dev.ps1
#>
param ()

Write-Host "Setting up development environment (PowerShell)"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "python not found. Please install Python 3.11+ and try again."
    exit 1
}

$venv = ".venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}

& "$venv/Scripts/Activate.ps1"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt

if (Test-Path backend/requirements-dev.txt) {
    python -m pip install -r backend/requirements-dev.txt
}

pre-commit install
try { pre-commit run --all-files } catch {}

Write-Host "Dev env setup is complete.
Run `& $venv/Scripts/Activate.ps1` to activate the venv in PowerShell."
