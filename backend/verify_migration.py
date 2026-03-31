#!/usr/bin/env python3
"""Verify migration file syntax"""
import ast
import sys

try:
    with open('alembic/versions/o2p3q4r5s6t7_advanced_playlist_features.py', 'r') as f:
        code = f.read()
    ast.parse(code)
    print("✓ Migration file syntax is valid")
    sys.exit(0)
except SyntaxError as e:
    print(f"✗ Syntax error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
