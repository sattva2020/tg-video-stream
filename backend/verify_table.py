#!/usr/bin/env python3
"""Verify adaptive_stream_config table exists"""
import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config'))
        count = result.scalar()
        print(f'Table exists: {count is not None}')
        print(f'Row count: {count}')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
