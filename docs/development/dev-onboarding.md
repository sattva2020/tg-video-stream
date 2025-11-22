# Dev onboarding (automated)

This document explains how to quickly set up a Python development environment for this project.

Prerequisites:
- Python 3.11+ installed
- Git

Automated script (Unix):

```bash
./scripts/setup-dev.sh
```

Automated script (PowerShell):

```powershell
.\scripts\setup-dev.ps1
```

What the script does:
- Creates a `.venv` (if not already present)
- Activates the venv and upgrades `pip`
- Installs root `requirements-dev.txt` and `backend/requirements-dev.txt` if present
- Installs `pre-commit` and sets up hooks (via `pre-commit install`)
- Runs `pre-commit run --all-files` once (optional) to format and fix issues

Why this script?
- It reduces one-time setup friction for new developers and CI
- Ensures `pre-commit` hooks are active locally to match CI checks

If you'd like to keep Windows-only onboarding, run the PowerShell script. If you prefer a Dockerized development setup, see `docker-compose.yml` and `README.md`.
