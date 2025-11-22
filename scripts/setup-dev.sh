#!/usr/bin/env bash
set -euo pipefail

echo "Setting up development environment"

if ! command -v python >/dev/null 2>&1; then
  echo "python not found, please install Python 3.11+ and try again" >&2
  exit 2
fi

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  python -m venv "$VENV_DIR"
fi

echo "Activating virtual environment"
source "$VENV_DIR/Scripts/activate" || source "$VENV_DIR/bin/activate"

echo "Upgrading pip and setuptools"
python -m pip install --upgrade pip setuptools wheel

echo "Installing top-level dev dependencies"
python -m pip install -r requirements-dev.txt

if [ -f backend/requirements-dev.txt ]; then
  echo "Installing backend dev dependencies"
  python -m pip install -r backend/requirements-dev.txt
fi

echo "Installing pre-commit hooks"
pre-commit install || true

echo "Running pre-commit on all files once (may modify files)"
pre-commit run --all-files || true

echo "Dev environment setup complete. Activate your venv with: source $VENV_DIR/Scripts/activate (Windows) or source $VENV_DIR/bin/activate (UNIX)"
