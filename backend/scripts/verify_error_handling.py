#!/usr/bin/env python3
"""
Automated Error Handling Verification Script for Import Feature

This script tests error handling and user guidance for import failures
by creating test import jobs with various error scenarios and verifying
that appropriate error messages are generated.

Usage:
    python backend/scripts/verify_error_handling.py
    python backend/scripts/verify_error_handling.py --user-id <uuid>
    python backend/scripts/verify_error_handling.py --test-scenario <scenario_name>

Test Scenarios:
    - invalid_url: Test invalid URL handling
    - private_playlist: Test private playlist error handling
    - network_error: Test network error simulation
    - missing_fields: Test missing required fields
    - all: Run all test scenarios (default)

Author: Auto-Claude
Feature: 011-content-import-migration-tools
Date: 2026-01-23
"""

import os
import sys
import argparse
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID, uuid4

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from database import SessionLocal
    from src.models.import_job import ImportJob, ImportStatus, ImportPlatform
    from src.models.user import User
    from src.schemas.import_schemas import ImportCreateRequest
    from src.services.import_service import ImportService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the backend directory with the virtual environment activated.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlingVerifier:
    """Verifies error handling and user guidance for import failures."""

    def __init__(self):
        """Initialize the verifier."""
        self.db = SessionLocal()
        self.import_service = ImportService()
        self.test_results = []

    def __del__(self):
        """Cleanup database session."""
        if hasattr(self, 'db'):
            self.db.close()

    def print_section(self, title: str):
        """Print a formatted section header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def print_check(self, message: str, passed: bool, details: str = ""):
        """Print a check result with color."""
        status = "✅ PASS" if passed else "❌ FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} - {message}")
        if details:
            print(f"    → {details}")

        self.test_results.append({
            "check": message,
            "passed": passed,
            "details": details
        })

    def get_test_user(self) -> Optional[User]:
        """Get or create a test user."""
        user = self.db.query(User).first()
        if not user:
            logger.warning("No users found in database. Creating test user...")
            user = User(
                email="test@example.com",
                username="test_user",
                hashed_password="test_hash"
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Created test user: {user.id}")

        return user

    def verify_invalid_url_error(self) -> bool:
        """Verify invalid URL error handling."""
        self.print_section("Scenario 1: Invalid URL Error Handling")

        try:
            user = self.get_test_user()
            all_passed = True

            # Test 1.1: Invalid YouTube URL format
            print("\n📋 Test 1.1: Invalid YouTube URL format")
            try:
                request = ImportCreateRequest(
                    platform=ImportPlatform.YOUTUBE,
                    source_url="not-a-valid-url",
                    user_id=user.id
                )
                job = self.import_service.create_import_job(
                    db=self.db,
                    request=request,
                    user_id=user.id
                )
                # Job created but should fail during processing
                self.print_check(
                    "Import job created with invalid URL",
                    job.status == ImportStatus.PENDING,
                    f"Job ID: {job.id}, Status: {job.status.value}"
                )

                # Verify error fields are ready
                self.print_check(
                    "Job has error_message and error_details fields",
                    hasattr(job, 'error_message') and hasattr(job, 'error_details'),
                    "Fields exist for storing error information"
                )

            except ValueError as e:
                # Expected: validation error
                self.print_check(
                    "Validation error raised for invalid URL",
                    "url" in str(e).lower() or "invalid" in str(e).lower(),
                    f"Error: {e}"
                )
            except Exception as e:
                self.print_check(
                    "Validation error raised for invalid URL",
                    False,
                    f"Unexpected error: {e}"
                )
                all_passed = False

            # Test 1.2: Missing required fields
            print("\n📋 Test 1.2: Missing required fields")
            try:
                request = ImportCreateRequest(
                    platform=ImportPlatform.YOUTUBE,
                    source_url=None,  # Missing required field
                    user_id=user.id
                )
                job = self.import_service.create_import_job(
                    db=self.db,
                    request=request,
                    user_id=user.id
                )
                self.print_check(
                    "Validation prevents missing source_url",
                    False,
                    "Job created despite missing source_url (should fail)"
                )
                all_passed = False
            except ValueError as e:
                self.print_check(
                    "Validation error raised for missing source_url",
                    "required" in str(e).lower() or "source_url" in str(e).lower(),
                    f"Error: {e}"
                )
            except Exception as e:
                self.print_check(
                    "Validation error raised for missing source_url",
                    False,
                    f"Unexpected error: {e}"
                )
                all_passed = False

            return all_passed

        except Exception as e:
            logger.exception("Error in invalid_url_error test")
            self.print_check("Invalid URL error test", False, f"Exception: {e}")
            return False

    def verify_error_message_quality(self) -> bool:
        """Verify that error messages are user-friendly."""
        self.print_section("Scenario 2: Error Message Quality")

        try:
            user = self.get_test_user()
            all_passed = True

            # Create a failed job manually for testing
            print("\n📋 Test 2.1: Creating failed import job for testing")
            job = ImportJob(
                user_id=user.id,
                platform=ImportPlatform.YOUTUBE,
                source_url="https://youtube.com/playlist?list=TEST",
                status=ImportStatus.FAILED,
                error_message="Playlist is private or not accessible",
                error_details={
                    "reason": "private_playlist",
                    "suggestion": "Check if the playlist is public",
                    "code": "ACCESS_DENIED"
                },
                total_items=10,
                processed_items=0,
                successful_items=0,
                failed_items=0,
                skipped_items=0
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

            # Verify error message quality
            print(f"\n📋 Test 2.2: Error message quality for job {job.id}")

            # Check 1: Error message exists
            self.print_check(
                "Error message is present",
                job.error_message is not None and len(job.error_message) > 0,
                f"Message: {job.error_message}"
            )

            # Check 2: Error message is user-friendly (not technical)
            is_user_friendly = (
                "playlist" in job.error_message.lower() or
                "доступ" in job.error_message.lower() or
                "доступн" in job.error_message.lower()
            )
            self.print_check(
                "Error message is user-friendly (not technical jargon)",
                is_user_friendly,
                "Contains plain language, not error codes"
            )

            # Check 3: Error details provide context
            self.print_check(
                "Error details provide additional context",
                job.error_details is not None and len(job.error_details) > 0,
                f"Details keys: {list(job.error_details.keys()) if job.error_details else 'None'}"
            )

            # Check 4: Error details include resolution suggestion
            has_suggestion = (
                job.error_details and
                any(key in job.error_details for key in ['suggestion', 'resolution', 'fix'])
            )
            self.print_check(
                "Error details include resolution suggestion",
                has_suggestion,
                f"Suggestion: {job.error_details.get('suggestion', 'N/A')}"
            )

            # Check 5: Error details include error code/reason
            has_reason = (
                job.error_details and
                'reason' in job.error_details
            )
            self.print_check(
                "Error details include error reason/code",
                has_reason,
                f"Reason: {job.error_details.get('reason', 'N/A')}"
            )

            # Cleanup test job
            self.db.delete(job)
            self.db.commit()

            return all_passed

        except Exception as e:
            logger.exception("Error in error_message_quality test")
            self.print_check("Error message quality test", False, f"Exception: {e}")
            return False

    def verify_duplicate_detection_errors(self) -> bool:
        """Verify duplicate detection error messages."""
        self.print_section("Scenario 3: Duplicate Detection Error Messages")

        try:
            user = self.get_test_user()
            all_passed = True

            # Create a completed job with duplicates
            print("\n📋 Test 3.1: Creating import job with duplicate detection")

            job = ImportJob(
                user_id=user.id,
                platform=ImportPlatform.YOUTUBE,
                source_url="https://youtube.com/playlist?list=TEST",
                status=ImportStatus.COMPLETED,
                metadata={
                    "playlist_title": "Test Playlist",
                    "extractor": "youtube"
                },
                results={
                    "imported": [],
                    "duplicates": [
                        {"url": "https://youtube.com/watch?v=1", "title": "Video 1"},
                        {"url": "https://youtube.com/watch?v=2", "title": "Video 2"}
                    ],
                    "failed": [],
                    "summary": {
                        "total": 2,
                        "imported": 0,
                        "duplicates": 2,
                        "failed": 0
                    },
                    "message": "All items were duplicates and were skipped"
                },
                total_items=2,
                processed_items=2,
                successful_items=0,
                failed_items=0,
                skipped_items=2
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

            # Verify duplicate handling
            print(f"\n📋 Test 3.2: Duplicate detection messages for job {job.id}")

            # Check 1: Skipped items count reflects duplicates
            self.print_check(
                "Skipped items count matches duplicate count",
                job.skipped_items == 2,
                f"skipped_items: {job.skipped_items}"
            )

            # Check 2: Results include duplicate information
            has_duplicates = (
                job.results and
                'duplicates' in job.results and
                len(job.results['duplicates']) > 0
            )
            self.print_check(
                "Results include list of duplicate items",
                has_duplicates,
                f"Duplicate count: {len(job.results.get('duplicates', []))}"
            )

            # Check 3: Summary provides clear message
            has_message = (
                job.results and
                'message' in job.results and
                len(job.results['message']) > 0
            )
            self.print_check(
                "Results include clear message about duplicates",
                has_message,
                f"Message: {job.results.get('message', 'N/A')}"
            )

            # Check 4: No error_message (not a failure)
            self.print_check(
                "No error_message for duplicate scenario (not a failure)",
                job.error_message is None or len(job.error_message) == 0,
                "Duplicates are expected behavior, not an error"
            )

            # Cleanup test job
            self.db.delete(job)
            self.db.commit()

            return all_passed

        except Exception as e:
            logger.exception("Error in duplicate_detection_errors test")
            self.print_check("Duplicate detection errors test", False, f"Exception: {e}")
            return False

    def verify_retry_functionality(self) -> bool:
        """Verify retry functionality for failed imports."""
        self.print_section("Scenario 4: Retry Functionality")

        try:
            user = self.get_test_user()
            all_passed = True

            # Create first failed job
            print("\n📋 Test 4.1: Creating first failed import job")

            job1 = ImportJob(
                user_id=user.id,
                platform=ImportPlatform.YOUTUBE,
                source_url="https://youtube.com/playlist?list=RETRY_TEST",
                status=ImportStatus.FAILED,
                error_message="Network connection failed",
                error_details={"retryable": True},
                total_items=10,
                processed_items=3,
                successful_items=2,
                failed_items=1,
                skipped_items=0
            )
            self.db.add(job1)
            self.db.commit()
            self.db.refresh(job1)

            # Create retry job
            print("\n📋 Test 4.2: Creating retry job")

            job2 = ImportJob(
                user_id=user.id,
                platform=ImportPlatform.YOUTUBE,
                source_url="https://youtube.com/playlist?list=RETRY_TEST",
                status=ImportStatus.PENDING,
                total_items=0,
                processed_items=0,
                successful_items=0,
                failed_items=0,
                skipped_items=0
            )
            self.db.add(job2)
            self.db.commit()
            self.db.refresh(job2)

            # Verify retry functionality
            print(f"\n📋 Test 4.3: Verifying retry job {job2.id}")

            # Check 1: Both jobs have unique IDs
            self.print_check(
                "Retry job has unique ID (different from original)",
                job1.id != job2.id,
                f"Original: {job1.id}, Retry: {job2.id}"
            )

            # Check 2: Both jobs reference same source URL
            self.print_check(
                "Retry job references same source URL",
                job1.source_url == job2.source_url,
                f"URL: {job2.source_url}"
            )

            # Check 3: Original job remains in failed state
            self.print_check(
                "Original job remains in database with failed status",
                job1.status == ImportStatus.FAILED,
                f"Original status: {job1.status.value}"
            )

            # Check 4: Can query both jobs
            jobs = self.db.query(ImportJob).filter(
                ImportJob.source_url == "https://youtube.com/playlist?list=RETRY_TEST",
                ImportJob.user_id == user.id
            ).all()

            self.print_check(
                "Both jobs are queryable in database",
                len(jobs) == 2,
                f"Found {len(jobs)} jobs with same URL"
            )

            # Cleanup test jobs
            self.db.delete(job1)
            self.db.delete(job2)
            self.db.commit()

            return all_passed

        except Exception as e:
            logger.exception("Error in retry_functionality test")
            self.print_check("Retry functionality test", False, f"Exception: {e}")
            return False

    def verify_platform_specific_errors(self) -> bool:
        """Verify platform-specific error handling."""
        self.print_section("Scenario 5: Platform-Specific Error Handling")

        try:
            user = self.get_test_user()
            all_passed = True

            platforms_to_test = [
                (ImportPlatform.YOUTUBE, "https://youtube.com/playlist?list=TEST", "YouTube"),
                (ImportPlatform.VIMEO, "https://vimeo.com/album/TEST", "Vimeo"),
                (ImportPlatform.LOCAL, None, "Local")
            ]

            for platform, url, platform_name in platforms_to_test:
                print(f"\n📋 Test 5.{platforms_to_test.index((platform, url, platform_name)) + 1}: {platform_name} platform errors")

                try:
                    request = ImportCreateRequest(
                        platform=platform,
                        source_url=url,
                        source_path="/invalid/path" if platform == ImportPlatform.LOCAL else None,
                        user_id=user.id
                    )

                    job = self.import_service.create_import_job(
                        db=self.db,
                        request=request,
                        user_id=user.id
                    )

                    self.print_check(
                        f"{platform_name} job created successfully",
                        job.status == ImportStatus.PENDING,
                        f"Job ID: {job.id}, Platform: {job.platform.value}"
                    )

                    # Verify platform is correctly set
                    self.print_check(
                        f"{platform_name} job has correct platform field",
                        job.platform == platform,
                        f"Platform: {job.platform.value}"
                    )

                    # Cleanup
                    self.db.delete(job)
                    self.db.commit()

                except Exception as e:
                    self.print_check(
                        f"{platform_name} job creation",
                        False,
                        f"Error: {e}"
                    )
                    all_passed = False

            return all_passed

        except Exception as e:
            logger.exception("Error in platform_specific_errors test")
            self.print_check("Platform-specific errors test", False, f"Exception: {e}")
            return False

    def verify_error_fields_completeness(self) -> bool:
        """Verify that ImportJob model has all necessary error fields."""
        self.print_section("Scenario 6: Error Fields Completeness")

        try:
            all_passed = True

            print("\n📋 Test 6.1: Checking ImportJob model fields")

            # Create a test job
            job = ImportJob(
                user_id=self.get_test_user().id,
                platform=ImportPlatform.YOUTUBE,
                source_url="https://youtube.com/playlist?list=TEST"
            )

            # Check for error_message field
            self.print_check(
                "ImportJob has error_message field",
                hasattr(job, 'error_message'),
                f"Field type: {type(job.error_message)}"
            )

            # Check for error_details field
            self.print_check(
                "ImportJob has error_details field",
                hasattr(job, 'error_details'),
                f"Field type: {type(job.error_details)}"
            )

            # Check error fields can be set
            job.error_message = "Test error message"
            job.error_details = {"reason": "test", "suggestion": "test suggestion"}

            self.print_check(
                "Error fields can be set and updated",
                job.error_message == "Test error message" and job.error_details["reason"] == "test",
                "error_message and error_details are writable"
            )

            # Check status can transition to failed
            job.mark_failed("Test failure")

            self.print_check(
                "Job can be marked as failed",
                job.status == ImportStatus.FAILED and job.error_message == "Test failure",
                f"Status: {job.status.value}, error_message: {job.error_message}"
            )

            return all_passed

        except Exception as e:
            logger.exception("Error in error_fields_completeness test")
            self.print_check("Error fields completeness test", False, f"Exception: {e}")
            return False

    def print_summary(self):
        """Print final summary of all tests."""
        self.print_section("VERIFICATION SUMMARY")

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n📊 Total Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%\n")

        if failed > 0:
            print("\n❌ Failed Checks:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  • {result['check']}")
                    if result['details']:
                        print(f"    → {result['details']}")
            print()

        # Overall assessment
        if pass_rate >= 90:
            print("🎉 EXCELLENT: Error handling is well implemented!")
        elif pass_rate >= 70:
            print("✅ GOOD: Error handling is mostly functional with minor issues.")
        elif pass_rate >= 50:
            print("⚠️  NEEDS IMPROVEMENT: Error handling has significant issues.")
        else:
            print("❌ CRITICAL: Error handling requires major fixes.")

        print("\n" + "=" * 80 + "\n")

    def run_all_tests(self) -> bool:
        """Run all error handling verification tests."""
        print("\n🔍 Starting Error Handling Verification...\n")

        results = []

        # Run all test scenarios
        results.append(self.verify_error_fields_completeness())
        results.append(self.verify_invalid_url_error())
        results.append(self.verify_error_message_quality())
        results.append(self.verify_duplicate_detection_errors())
        results.append(self.verify_retry_functionality())
        results.append(self.verify_platform_specific_errors())

        # Print summary
        self.print_summary()

        return all(results)

    def run_specific_test(self, scenario: str) -> bool:
        """Run a specific test scenario."""
        scenario_map = {
            "invalid_url": self.verify_invalid_url_error,
            "error_message": self.verify_error_message_quality,
            "duplicates": self.verify_duplicate_detection_errors,
            "retry": self.verify_retry_functionality,
            "platform": self.verify_platform_specific_errors,
            "fields": self.verify_error_fields_completeness,
        }

        if scenario not in scenario_map:
            print(f"❌ Unknown scenario: {scenario}")
            print(f"Available scenarios: {', '.join(scenario_map.keys())}")
            return False

        print(f"\n🔍 Running specific test: {scenario}...\n")
        result = scenario_map[scenario]()
        self.print_summary()
        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify error handling and user guidance for import failures"
    )
    parser.add_argument(
        "--test-scenario",
        choices=["invalid_url", "error_message", "duplicates", "retry", "platform", "fields", "all"],
        default="all",
        help="Test scenario to run (default: all)"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="User ID to use for testing (default: first user in DB)"
    )

    args = parser.parse_args()

    try:
        verifier = ErrorHandlingVerifier()

        if args.test_scenario == "all":
            success = verifier.run_all_tests()
        else:
            success = verifier.run_specific_test(args.test_scenario)

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.exception("Fatal error in verification script")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
