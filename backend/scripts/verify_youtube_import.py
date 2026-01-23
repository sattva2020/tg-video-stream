#!/usr/bin/env python3
"""
YouTube Import Verification Script

This script helps verify the database state after a YouTube playlist import.
It checks import jobs, playlists, playlist items, and activity logs.

Usage:
    python scripts/verify_youtube_import.py [--job-id JOB_ID] [--user-id USER_ID]

Options:
    --job-id JOB_ID    Specific import job ID to verify (default: latest)
    --user-id USER_ID  User ID to filter imports (default: latest from any user)
    --help             Show this help message

Examples:
    # Verify latest import
    python scripts/verify_youtube_import.py

    # Verify specific import job
    python scripts/verify_youtube_import.py --job-id 123e4567-e89b-12d3-a456-426614174000

    # Verify latest import for specific user
    python scripts/verify_youtube_import.py --user-id 123e4567-e89b-12d3-a456-426614174000
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.database import get_db_url


class ImportVerifier:
    """Verifies YouTube playlist import database state"""

    def __init__(self, session: Session):
        self.session = session

    def verify_import_job(self, job_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """Verify import job record"""
        print("\n" + "="*80)
        print("VERIFYING IMPORT JOB")
        print("="*80)

        query = "SELECT * FROM import_jobs WHERE platform = 'youtube'"

        if job_id:
            query += f" AND id = '{job_id}'"
        elif user_id:
            query += f" AND user_id = '{user_id}'"

        query += " ORDER BY created_at DESC LIMIT 1"

        result = self.session.execute(text(query)).fetchone()

        if not result:
            print("❌ No import job found")
            return None

        job = dict(result._mapping)

        print(f"\n📋 Import Job Details:")
        print(f"  ID:              {job['id']}")
        print(f"  Platform:        {job['platform']}")
        print(f"  Source URL:      {job['source_url'][:80]}..." if len(job['source_url']) > 80 else f"  Source URL:      {job['source_url']}")
        print(f"  Status:          {job['status']}")
        print(f"  Total Items:     {job['total_items']}")
        print(f"  Processed:       {job['processed_items']}")
        print(f"  Successful:      {job['successful_items']}")
        print(f"  Failed:          {job['failed_items']}")
        print(f"  Skipped:         {job['skipped_items']}")
        print(f"  Created At:      {job['created_at']}")
        print(f"  Completed At:    {job['completed_at']}")
        print(f"  User ID:         {job['user_id']}")
        print(f"  Channel ID:      {job.get('channel_id', 'N/A')}")

        # Validation checks
        print(f"\n✅ Validation Checks:")

        checks_passed = 0
        total_checks = 0

        # Check 1: Platform is correct
        total_checks += 1
        if job['platform'] == 'youtube':
            print("  ✓ Platform is 'youtube'")
            checks_passed += 1
        else:
            print(f"  ✗ Platform is '{job['platform']}', expected 'youtube'")

        # Check 2: Total items > 0
        total_checks += 1
        if job['total_items'] and job['total_items'] > 0:
            print(f"  ✓ Total items > 0 ({job['total_items']})")
            checks_passed += 1
        else:
            print(f"  ✗ Total items is 0 or null")

        # Check 3: Status is valid
        total_checks += 1
        valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'cancelled', 'paused']
        if job['status'] in valid_statuses:
            print(f"  ✓ Status is valid ('{job['status']}')")
            checks_passed += 1
        else:
            print(f"  ✗ Invalid status: '{job['status']}'")

        # Check 4: Math checks out
        total_checks += 1
        if job['total_items']:
            expected_processed = job['successful_items'] + job['failed_items'] + job['skipped_items']
            if job['processed_items'] == expected_processed:
                print(f"  ✓ Processed items match ({job['processed_items']} = {expected_processed})")
                checks_passed += 1
            else:
                print(f"  ✗ Processed items mismatch: {job['processed_items']} != {expected_processed}")

        # Check 5: If completed, completed_at is set
        total_checks += 1
        if job['status'] == 'completed':
            if job['completed_at']:
                print(f"  ✓ Completed at timestamp is set")
                checks_passed += 1
            else:
                print(f"  ✗ Status is 'completed' but completed_at is null")

        # Check 6: Created at is recent (within last hour)
        total_checks += 1
        if job['created_at']:
            time_diff = datetime.now() - job['created_at']
            if time_diff < timedelta(hours=1):
                print(f"  ✓ Created at is recent ({time_diff.seconds // 60} minutes ago)")
                checks_passed += 1
            else:
                print(f"  ⚠ Created at is old ({time_diff})")
        else:
            print(f"  ✗ Created at is null")

        print(f"\n📊 Checks Passed: {checks_passed}/{total_checks}")

        return job

    def verify_playlist(self, import_job_id: str) -> dict:
        """Verify playlist record created from import"""
        print("\n" + "="*80)
        print("VERIFYING PLAYLIST")
        print("="*80)

        query = """
            SELECT * FROM playlists
            WHERE is_imported = true AND import_job_id = :job_id
            ORDER BY created_at DESC LIMIT 1
        """

        result = self.session.execute(text(query), {"job_id": import_job_id}).fetchone()

        if not result:
            print("❌ No imported playlist found")
            return None

        playlist = dict(result._mapping)

        print(f"\n📋 Playlist Details:")
        print(f"  ID:              {playlist['id']}")
        print(f"  Name:            {playlist['name']}")
        print(f"  Content Type:    {playlist['content_type']}")
        print(f"  Is Imported:     {playlist['is_imported']}")
        print(f"  Import Job ID:   {playlist['import_job_id']}")
        print(f"  User ID:         {playlist['user_id']}")
        print(f"  Channel ID:      {playlist.get('channel_id', 'N/A')}")
        print(f"  Created At:      {playlist['created_at']}")

        print(f"\n✅ Validation Checks:")

        checks_passed = 0
        total_checks = 0

        # Check 1: Is imported flag
        total_checks += 1
        if playlist['is_imported']:
            print("  ✓ is_imported flag is true")
            checks_passed += 1
        else:
            print("  ✗ is_imported flag is false")

        # Check 2: Content type is youtube
        total_checks += 1
        if playlist['content_type'] == 'youtube':
            print("  ✓ Content type is 'youtube'")
            checks_passed += 1
        else:
            print(f"  ✗ Content type is '{playlist['content_type']}', expected 'youtube'")

        # Check 3: Import job ID matches
        total_checks += 1
        if playlist['import_job_id'] == import_job_id:
            print("  ✓ Import job ID matches")
            checks_passed += 1
        else:
            print(f"  ✗ Import job ID mismatch")

        # Check 4: Name is not empty
        total_checks += 1
        if playlist['name'] and len(playlist['name']) > 0:
            print(f"  ✓ Playlist name is set ('{playlist['name'][:50]}...')")
            checks_passed += 1
        else:
            print("  ✗ Playlist name is empty")

        print(f"\n📊 Checks Passed: {checks_passed}/{total_checks}")

        return playlist

    def verify_playlist_items(self, playlist_id: str, expected_count: int) -> list:
        """Verify playlist items created from import"""
        print("\n" + "="*80)
        print("VERIFYING PLAYLIST ITEMS")
        print("="*80)

        # Count query
        count_query = """
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN is_duplicate = false THEN 1 END) as unique_count,
                   COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicate_count
            FROM playlist_items
            WHERE playlist_id = :playlist_id
        """

        count_result = self.session.execute(text(count_query), {"playlist_id": playlist_id}).fetchone()
        stats = dict(count_result._mapping)

        print(f"\n📊 Item Statistics:")
        print(f"  Total Items:        {stats['total']}")
        print(f"  Unique Items:       {stats['unique_count']}")
        print(f"  Duplicate Items:    {stats['duplicate_count']}")

        # Sample items
        sample_query = """
            SELECT title, source_url, duration, position, is_duplicate
            FROM playlist_items
            WHERE playlist_id = :playlist_id
            ORDER BY position
            LIMIT 5
        """

        samples = self.session.execute(text(sample_query), {"playlist_id": playlist_id}).fetchall()

        print(f"\n📋 Sample Items (first 5):")
        for i, item in enumerate(samples, 1):
            item_dict = dict(item._mapping)
            duplicate_mark = " [DUPLICATE]" if item_dict['is_duplicate'] else ""
            print(f"  {i}. {item_dict['title'][:60]}...{duplicate_mark}")
            print(f"     URL: {item_dict['source_url'][:60]}...")
            print(f"     Duration: {item_dict['duration']}s, Position: {item_dict['position']}")

        print(f"\n✅ Validation Checks:")

        checks_passed = 0
        total_checks = 0

        # Check 1: Total items match expected
        total_checks += 1
        if stats['total'] == expected_count:
            print(f"  ✓ Total items match expected ({expected_count})")
            checks_passed += 1
        else:
            print(f"  ✗ Total items mismatch: {stats['total']} != {expected_count}")

        # Check 2: All items have titles
        total_checks += 1
        titles_query = "SELECT COUNT(*) FROM playlist_items WHERE playlist_id = :playlist_id AND title IS NOT NULL"
        titles_count = self.session.execute(text(titles_query), {"playlist_id": playlist_id}).scalar()
        if titles_count == stats['total']:
            print(f"  ✓ All items have titles")
            checks_passed += 1
        else:
            print(f"  ✗ Some items missing titles: {titles_count}/{stats['total']}")

        # Check 3: All items have source URLs
        total_checks += 1
        urls_query = "SELECT COUNT(*) FROM playlist_items WHERE playlist_id = :playlist_id AND source_url IS NOT NULL"
        urls_count = self.session.execute(text(urls_query), {"playlist_id": playlist_id}).scalar()
        if urls_count == stats['total']:
            print(f"  ✓ All items have source URLs")
            checks_passed += 1
        else:
            print(f"  ✗ Some items missing source URLs: {urls_count}/{stats['total']}")

        # Check 4: Positions are sequential
        total_checks += 1
        positions_query = "SELECT COUNT(DISTINCT position) FROM playlist_items WHERE playlist_id = :playlist_id"
        distinct_positions = self.session.execute(text(positions_query), {"playlist_id": playlist_id}).scalar()
        if distinct_positions == stats['total']:
            print(f"  ✓ Positions are sequential (1-{stats['total']})")
            checks_passed += 1
        else:
            print(f"  ✗ Positions not sequential: {distinct_positions} distinct for {stats['total']} items")

        # Check 5: No duplicate URLs (except marked duplicates)
        total_checks += 1
        duplicate_urls_query = """
            SELECT source_url, COUNT(*) as count
            FROM playlist_items
            WHERE playlist_id = :playlist_id
            GROUP BY source_url
            HAVING COUNT(*) > 1
        """
        duplicate_urls = self.session.execute(text(duplicate_urls_query), {"playlist_id": playlist_id}).fetchall()
        if len(duplicate_urls) == 0:
            print(f"  ✓ No duplicate URLs in playlist")
            checks_passed += 1
        else:
            print(f"  ⚠ Found {len(duplicate_urls)} duplicate URLs (may be intentional)")

        print(f"\n📊 Checks Passed: {checks_passed}/{total_checks}")

        return [dict(item._mapping) for item in samples]

    def verify_activity_logs(self, import_job_id: str) -> list:
        """Verify activity events were logged"""
        print("\n" + "="*80)
        print("VERIFYING ACTIVITY LOGS")
        print("="*80)

        query = """
            SELECT event_type, message, details, created_at
            FROM activity_events
            WHERE details->>'import_job_id' = :job_id
            ORDER BY created_at
        """

        results = self.session.execute(text(query), {"job_id": import_job_id}).fetchall()
        events = [dict(row._mapping) for row in results]

        if not events:
            print("❌ No activity events found")
            return []

        print(f"\n📋 Activity Events ({len(events)} found):")
        for event in events:
            print(f"\n  Event Type:  {event['event_type']}")
            print(f"  Message:     {event['message']}")
            print(f"  Created At:  {event['created_at']}")
            if event['details']:
                print(f"  Details:     {event['details']}")

        print(f"\n✅ Validation Checks:")

        checks_passed = 0
        total_checks = 0

        # Check 1: import_started event exists
        total_checks += 1
        if any(e['event_type'] == 'import_started' for e in events):
            print("  ✓ import_started event logged")
            checks_passed += 1
        else:
            print("  ✗ import_started event missing")

        # Check 2: import_completed event exists (if job completed)
        total_checks += 1
        if any(e['event_type'] == 'import_completed' for e in events):
            print("  ✓ import_completed event logged")
            checks_passed += 1
        else:
            print("  ⚠ import_completed event missing (job may still be running)")

        # Check 3: Events have proper details
        total_checks += 1
        if all(e['details'] for e in events):
            print("  ✓ All events have details")
            checks_passed += 1
        else:
            print("  ✗ Some events missing details")

        print(f"\n📊 Checks Passed: {checks_passed}/{total_checks}")

        return events

    def run_full_verification(self, job_id: Optional[str] = None, user_id: Optional[str] = None):
        """Run complete verification process"""
        print("\n" + "="*80)
        print("YOUTUBE PLAYLIST IMPORT VERIFICATION")
        print("="*80)
        print(f"\nStarted at: {datetime.now()}")

        # Step 1: Verify import job
        import_job = self.verify_import_job(job_id, user_id)

        if not import_job:
            print("\n❌ Cannot proceed: No import job found")
            return

        job_id = import_job['id']

        # Step 2: Verify playlist
        playlist = self.verify_playlist(job_id)

        if not playlist:
            print("\n⚠ Warning: No playlist found for import job")

        # Step 3: Verify playlist items
        if playlist:
            self.verify_playlist_items(playlist['id'], import_job['total_items'])

        # Step 4: Verify activity logs
        self.verify_activity_logs(job_id)

        # Final summary
        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        print(f"\nCompleted at: {datetime.now()}")
        print(f"\nImport Job ID: {job_id}")
        print(f"Status: {import_job['status']}")
        print(f"Total Items: {import_job['total_items']}")
        print(f"Successful: {import_job['successful_items']}")
        print(f"Failed: {import_job['failed_items']}")
        print(f"Skipped: {import_job['skipped_items']}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify YouTube playlist import database state",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--job-id', help='Specific import job ID to verify')
    parser.add_argument('--user-id', help='User ID to filter imports')
    parser.add_argument('--db-url', help='Database URL (default: from environment)')

    args = parser.parse_args()

    # Create database session
    db_url = args.db_url or get_db_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        verifier = ImportVerifier(session)
        verifier.run_full_verification(args.job_id, args.user_id)
    finally:
        session.close()


if __name__ == '__main__':
    main()
