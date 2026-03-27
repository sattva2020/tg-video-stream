#!/usr/bin/env python3
"""Check if adaptive_stream_config table exists - write to file"""
import sys
from pathlib import Path
import traceback

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

output_file = Path(__file__).parent / 'table_check_result.txt'

try:
    with open(output_file, 'w') as f:
        f.write("Starting table check...\n")

        # Try imports
        from src.database import engine
        from sqlalchemy import text
        f.write("Imports successful\n")

        # Try database connection
        with engine.connect() as conn:
            f.write("Database connected\n")

            # Check if table exists
            result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config'))
            count = result.scalar()
            f.write(f'Table exists: {count is not None}\n')
            f.write(f'Row count: {count}\n')
            f.write('SUCCESS\n')
except Exception as e:
    with open(output_file, 'w') as f:
        f.write(f'ERROR: {e}\n')
        f.write(traceback.format_exc())
    sys.exit(1)
