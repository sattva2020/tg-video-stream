#!/usr/bin/env python3
"""Apply migrations and verify in one script"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from alembic.config import Config
from alembic import command

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Create a log file
log_file = Path(__file__).parent / 'migration_log.txt'

def log(message):
    """Write message to both stdout and log file"""
    print(message)
    with open(log_file, 'a') as f:
        f.write(message + '\n')

try:
    log("=== Starting Migration Process ===")

    # Get the database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        log("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    log(f"Database URL: {database_url[:30]}...")

    # Create Alembic configuration
    config_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    alembic_config = Config(config_path)

    # Set the database URL in the config
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    # Run the upgrade to head (latest migration)
    log("Applying database migrations...")
    command.upgrade(alembic_config, "head")
    log("Migrations applied successfully!")

    # Now verify the table exists
    log("\n=== Verifying Table Creation ===")
    from src.database import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config'))
        count = result.scalar()
        log(f"Table exists: {count is not None}")
        log(f"Row count: {count}")
        log(f"Verification: {'SUCCESS' if count is not None else 'FAILED'}")

    log("\n=== Migration Complete ===")

except Exception as e:
    log(f"\nERROR: {e}")
    import traceback
    log(traceback.format_exc())
    sys.exit(1)
