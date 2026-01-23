#!/usr/bin/env python3
"""Apply database migrations programmatically"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from alembic.config import Config
from alembic import command

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def run_migrations():
    """Run alembic migrations to upgrade database schema"""
    # Get the database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Create Alembic configuration
    config_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    alembic_config = Config(config_path)

    # Set the database URL in the config
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    # Run the upgrade to head (latest migration)
    print("Applying database migrations...")
    command.upgrade(alembic_config, "head")
    print("Migrations applied successfully!")

if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as e:
        print(f"Error applying migrations: {e}", file=sys.stderr)
        sys.exit(1)
