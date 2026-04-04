"""Script to run Alembic migration programmatically."""
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alembic.config import Config
from alembic import command

def run_migration():
    """Run the database migration to create new tables."""
    # Get the directory where this script is located
    here = os.path.dirname(__file__)

    # Create Alembic configuration
    alembic_cfg = Config(os.path.join(here, "alembic.ini"))

    # Set the script location
    alembic_cfg.set_main_option("script_location", os.path.join(here, "alembic"))

    try:
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        print("Migration completed successfully")
        return 0
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_migration())
