#!/bin/bash
cd "$(dirname "$0")"
PYTHON_PATH="/c/Users/Admin/AppData/Local/Programs/Python/Python312/python.exe"
exec "$PYTHON_PATH" test_import.py 2>&1
