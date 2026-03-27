#!/bin/bash
# Wrapper script to apply migrations
cd "$(dirname "$0")"

# Try to find and use Python
PYTHON_PATH="/c/Users/Admin/AppData/Local/Programs/Python/Python312/python.exe"

if [ -f "$PYTHON_PATH" ]; then
    exec "$PYTHON_PATH" apply_migration.py
else
    echo "Python not found at $PYTHON_PATH"
    exit 1
fi
