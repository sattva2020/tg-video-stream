#!/usr/bin/env python3
"""
Verification Script for AyuGram Python SDK Example Scripts

This script runs all example scripts to verify end-to-end functionality:
1. Runs basic_usage.py - verifies success
2. Runs session_management.py - verifies session operations
3. Runs voice_call.py - verifies call operations

All examples run in demo mode by default (no server required).

Usage:
    python verify_examples.py

Exit Codes:
    0: All verifications passed
    1: One or more verifications failed
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("verify_examples")

# Example scripts to verify
EXAMPLE_SCRIPTS = [
    "examples/basic_usage.py",
    "examples/session_management.py",
    "examples/voice_call.py",
]

# Verification timeout for each script (seconds)
SCRIPT_TIMEOUT = 60


class ExampleVerification:
    """Results of example script verification."""

    def __init__(self, script_name: str):
        self.script_name = script_name
        self.success = False
        self.output = ""
        self.error_output = ""
        self.exit_code = None
        self.duration = 0.0

    def __str__(self):
        status = "✓ PASS" if self.success else "✗ FAIL"
        return f"{status} | {self.script_name} | {self.duration:.2f}s | exit={self.exit_code}"


async def run_example_script(script_path: str, timeout: int = SCRIPT_TIMEOUT) -> ExampleVerification:
    """
    Run an example script and capture output.

    Args:
        script_path: Path to the example script (relative to ayugram-python/)
        timeout: Maximum time to wait for script completion (seconds)

    Returns:
        ExampleVerification with results
    """
    verification = ExampleVerification(script_path)
    full_path = Path(__file__).parent / script_path

    if not full_path.exists():
        verification.error_output = f"Script not found: {full_path}"
        logger.error(f"✗ Script not found: {script_path}")
        return verification

    logger.info(f"Running example script: {script_path}")

    start_time = time.time()

    try:
        # Run the script using subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(full_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent
        )

        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            verification.output = stdout.decode('utf-8', errors='replace')
            verification.error_output = stderr.decode('utf-8', errors='replace')
            verification.exit_code = process.returncode
            verification.duration = time.time() - start_time
            verification.success = process.returncode == 0

            if verification.success:
                logger.info(f"✓ {script_path} completed successfully ({verification.duration:.2f}s)")
            else:
                logger.error(f"✗ {script_path} failed with exit code {process.returncode}")
                if verification.error_output:
                    logger.error(f"Error output:\n{verification.error_output[:500]}")

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            verification.duration = time.time() - start_time
            verification.error_output = f"Script timed out after {timeout}s"
            logger.error(f"✗ {script_path} timed out after {timeout}s")

    except Exception as e:
        verification.duration = time.time() - start_time
        verification.error_output = str(e)
        logger.error(f"✗ {script_path} raised exception: {e}")

    return verification


async def verify_all_examples() -> list[ExampleVerification]:
    """
    Run all example scripts and verify results.

    Returns:
        List of ExampleVerification results
    """
    results = []

    for script in EXAMPLE_SCRIPTS:
        verification = await run_example_script(script)
        results.append(verification)

        # Small delay between scripts
        await asyncio.sleep(1)

    return results


def print_summary(results: list[ExampleVerification]):
    """Print verification summary."""
    logger.info("\n" + "=" * 80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed

    for result in results:
        logger.info(str(result))

    logger.info("-" * 80)
    logger.info(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    logger.info("=" * 80)

    if failed == 0:
        logger.info("✓ All example scripts verified successfully!")
    else:
        logger.warning(f"✗ {failed} example script(s) failed verification")


async def main():
    """Main verification function."""
    logger.info("=" * 80)
    logger.info("AyuGram Python SDK - Example Script Verification")
    logger.info("=" * 80)
    logger.info("This script will:")
    logger.info("  1. Run all example scripts in demo mode")
    logger.info("  2. Verify output and exit codes")
    logger.info("  3. Report verification results")
    logger.info("=" * 80 + "\n")

    # Run all example scripts
    logger.info("Running example scripts in demo mode...\n")
    results = await verify_all_examples()

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    if all(r.success for r in results):
        logger.info("\n✓ All verifications passed!")
        return 0
    else:
        logger.error("\n✗ Some verifications failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠ Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
