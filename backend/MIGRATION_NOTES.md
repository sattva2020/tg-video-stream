# Database Migration Application Notes

## Subtask 3-2: Apply Database Migrations

### Migration File Created
- **File**: `alembic/versions/009_adaptive_stream_config.py`
- **Revision**: `009_adaptive_stream_config`
- **Revises**: `22_phase3_stream_quality_history`
- **Created**: 2026-01-23 (Subtask 3-1)

### Migration Application Scripts
The following scripts have been created to apply the migration:

1. **apply_migration.py** - Python script that uses Alembic to run migrations
2. **apply_migration.sh** - Bash wrapper for the Python script
3. **migrate_and_verify.py** - Combined migration and verification script
4. **verify_table.py** - Verification script to check table existence

### How to Apply the Migration

#### Option 1: Using the provided script (recommended)
```bash
cd backend
bash apply_migration.sh
```

#### Option 2: Using Python directly
```bash
cd backend
python apply_migration.py
```

#### Option 3: Using Alembic directly
```bash
cd backend
alembic upgrade head
```

### Verification
After applying the migration, verify the table exists:

```bash
cd backend
python -c "from src.database import engine; from sqlalchemy import text; with engine.connect() as conn: result = conn.execute(text('SELECT COUNT(*) FROM adaptive_stream_config')); print('Table exists:', result.scalar() is not None)"
```

Expected output: `Table exists: True`

### Environment Requirements
- Python 3.11+ installed
- PostgreSQL database running
- `.env` file with `DATABASE_URL` configured
- All dependencies installed (alembic, sqlalchemy, psycopg2, etc.)

### Migration Details
The migration creates the `adaptive_stream_config` table with the following columns:
- `id` (BigInteger, Primary Key)
- `stream_id` (UUID, Foreign Key to streams.id)
- `enabled` (Boolean, default: true)
- `default_quality` (String, default: 'high')
- `min_quality` (String, default: 'low')
- `max_quality` (String, default: 'ultra')
- Bandwidth thresholds for low/medium/high/ultra quality
- Adaptation settings (interval, smoothing factor, consecutive measurements)
- Device rules and quality profiles (JSONB)
- Monitoring and logging toggles
- Statistics tracking (JSONB)
- Created/updated timestamps

### Notes
- Migration script is ready and has been tested for syntax correctness
- Actual execution requires proper database connectivity
- The migration follows existing patterns from the codebase
- All constraints, indexes, and foreign keys are properly defined
