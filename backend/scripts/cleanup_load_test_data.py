#!/usr/bin/env python3
"""
Cleanup Load Test Data

Удаляет тестовые данные, созданные нагрузочным тестированием.

Usage:
    python scripts/cleanup_load_test_data.py
    python scripts/cleanup_load_test_data.py --dry-run
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings


def cleanup_test_data(db_session: Session, dry_run: bool = False) -> dict:
    """Удаление тестовых данных."""
    result = {
        'users_deleted': 0,
        'streams_deleted': 0,
        'recovery_logs_deleted': 0
    }

    try:
        # Start transaction
        if not dry_run:
            db_session.begin()

        # Get test admin user
        test_user_query = text("SELECT id FROM users WHERE email = 'load_test_admin@test.com'")
        test_user_result = db_session.execute(test_user_query).fetchone()

        if not test_user_result:
            print("ℹ️  Тестовые данные не найдены")
            return result

        user_id = test_user_result[0]

        # Count recovery logs to be deleted
        recovery_logs_count_query = text("""
            SELECT COUNT(*) FROM recovery_logs
            WHERE stream_id IN (SELECT id FROM streams WHERE owner_id = :user_id)
        """)
        recovery_logs_count = db_session.execute(
            recovery_logs_count_query,
            {'user_id': user_id}
        ).scalar()
        result['recovery_logs_deleted'] = recovery_logs_count or 0

        # Count streams to be deleted
        streams_count_query = text("SELECT COUNT(*) FROM streams WHERE owner_id = :user_id")
        streams_count = db_session.execute(streams_count_query, {'user_id': user_id}).scalar()
        result['streams_deleted'] = streams_count or 0

        result['users_deleted'] = 1

        if dry_run:
            print("🔍 DRY RUN - данные не будут удалены:")
            print(f"  Пользователей: {result['users_deleted']}")
            print(f"  Потоков: {result['streams_deleted']}")
            print(f"  Логов восстановления: {result['recovery_logs_deleted']}")
            return result

        # Delete recovery logs (cascaded from streams)
        delete_recovery_logs_query = text("""
            DELETE FROM recovery_logs
            WHERE stream_id IN (SELECT id FROM streams WHERE owner_id = :user_id)
        """)
        db_session.execute(delete_recovery_logs_query, {'user_id': user_id})

        # Delete streams
        delete_streams_query = text("DELETE FROM streams WHERE owner_id = :user_id")
        db_session.execute(delete_streams_query, {'user_id': user_id})

        # Delete test user
        delete_user_query = text("DELETE FROM users WHERE id = :user_id")
        db_session.execute(delete_user_query, {'user_id': user_id})

        # Commit transaction
        db_session.commit()

        print("✅ Тестовые данные успешно удалены:")
        print(f"  Пользователей: {result['users_deleted']}")
        print(f"  Потоков: {result['streams_deleted']}")
        print(f"  Логов восстановления: {result['recovery_logs_deleted']}")

    except Exception as e:
        db_session.rollback()
        print(f"❌ Ошибка при удалении: {e}")
        raise

    return result


def main():
    parser = argparse.ArgumentParser(description='Удаление тестовых данных нагрузочного тестирования')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Показать что будет удалено, но не удалять'
    )

    args = parser.parse_args()

    # Create database connection
    database_url = str(settings.DATABASE_URL).replace('+aiomysql', '+pymysql')
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = SessionLocal()

    try:
        if args.dry_run:
            print("="*60)
            print("DRY RUN MODE")
            print("="*60)

        cleanup_test_data(db_session, dry_run=args.dry_run)

    finally:
        db_session.close()
        engine.dispose()


if __name__ == '__main__':
    main()
