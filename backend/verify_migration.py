#!/usr/bin/env python3
"""
Verification script for Feature 021 - Multi-platform migration
Run this to verify the migration was applied successfully.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import inspect, text
from src.database import engine


def verify_migration():
    """Verify that all new tables exist."""
    print("Verifying Feature 021 migration...")

    expected_tables = [
        'streaming_platforms',
        'broadcast_destinations',
        'social_media_posts',
        'chat_messages'
    ]

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        print(f"\nExisting tables: {len(existing_tables)}")
        print(f"Expected tables: {len(expected_tables)}")

        all_found = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"✓ {table} - found")

                # Check columns
                columns = [col['name'] for col in inspector.get_columns(table)]
                print(f"  Columns: {', '.join(columns)}")
            else:
                print(f"✗ {table} - NOT FOUND")
                all_found = False

        if all_found:
            print("\n✓ Migration applied successfully!")
            return 0
        else:
            print("\n✗ Migration incomplete - some tables are missing")
            return 1


if __name__ == "__main__":
    sys.exit(verify_migration())
