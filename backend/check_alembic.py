#!/usr/bin/env python3
"""Check alembic version"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from src.database import engine
from sqlalchemy import text

with open('alembic_check.txt', 'w') as f:
    try:
        with engine.connect() as conn:
            # Check alembic version
            try:
                result = conn.execute(text('SELECT version_num FROM alembic_version'))
                version = result.scalar()
                f.write(f'Alembic version: {version}\n')
            except Exception as e:
                f.write(f'No alembic_version table: {e}\n')

            # Check if adaptive_stream_config table exists
            try:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'adaptive_stream_config'
                    )
                """))
                exists = result.scalar()
                f.write(f'adaptive_stream_config table exists: {exists}\n')

                if exists:
                    result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config'))
                    count = result.scalar()
                    f.write(f'Row count: {count}\n')

            except Exception as e:
                f.write(f'Error checking table: {e}\n')

        f.write('Check complete\n')
    except Exception as e:
        f.write(f'Database error: {e}\n')
