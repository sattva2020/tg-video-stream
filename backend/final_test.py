#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, '.')

import os
from dotenv import load_dotenv
load_dotenv()

try:
    from src.database import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print(f"DB OK: {result.scalar()}")

        # Check alembic version
        try:
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            print(f"Alembic version: {result.scalar()}")
        except:
            print("No alembic_version table")

        # Check adaptive_stream_config table
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'adaptive_stream_config'
                )
            """))
            exists = result.scalar()
            print(f"Table exists: {exists}")

            if exists:
                result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config'))
                count = result.scalar()
                print(f"Rows: {count}")
        except Exception as e:
            print(f"Table check error: {e}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
