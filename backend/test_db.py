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
        val = result.scalar()
        print(f"DB connection works: {val}")
        
        # Check for table
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
        except Exception as e:
            print(f"Table check error: {e}")
            
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
