#!/usr/bin/env python3
"""
Verification script for logging patterns with AyuGram.

This script verifies that log messages clearly indicate which streaming
backend (AyuGram or PyTgCalls) is being used.
"""

import re
import sys
from pathlib import Path


def check_logging_patterns(file_path: Path, backend_var: str) -> tuple[bool, list[str]]:
    """
    Check if file has proper logging patterns for backend detection.

    Args:
        file_path: Path to the Python file
        backend_var: Expected backend variable name (e.g., 'backend' or 'backend_name')

    Returns:
        (success, issues): Success status and list of issues found
    """
    issues = []
    content = file_path.read_text()
    lines = content.split('\n')

    # Check for backend variable logging
    backend_logging_found = False
    for i, line in enumerate(lines, 1):
        # Look for log statements that include backend info
        # Match patterns like:
        # - log.info(f"...{backend}...")
        # - log.info("... %s", backend)
        # - log.info(f"... {backend} ...")
        if re.search(r'log\.(info|warning|error|debug)', line):
            if backend_var in line:
                backend_logging_found = True

    if not backend_logging_found:
        issues.append(f"No logging statements found that include backend information ({backend_var})")

    # Check for backend initialization logging
    init_patterns = [
        r'backend.*initialized',
        r'streaming backend.*initialized',
        r'using.*backend.*for streaming',
        r'Using.*backend.*streaming',
        r'Created.*backend',
        r'backend.*created',
    ]

    init_logging_found = False
    for i, line in enumerate(lines, 1):
        for pattern in init_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                init_logging_found = True
                break

    if not init_logging_found:
        issues.append("No backend initialization logging found")

    # Check for undefined backend_type references (common bug)
    # Skip comments and dict keys
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip full-line comments
        if stripped.startswith('#'):
            continue

        if 'backend_type' in line:
            # Check if it's a dict key (e.g., "backend_type": or 'backend_type':)
            if re.search(r'["\']backend_type["\']\s*:', line):
                continue  # Dict key, OK
            # Check if it's in a comment at the end of the line
            if '#' in line:
                # Remove comment and check if backend_type is in the code part
                code_part = line.split('#')[0]
                if 'backend_type' not in code_part:
                    continue  # Only in comment, OK
            # Otherwise it's likely a bug
            if backend_var == 'backend':
                issues.append(f"Line {i}: Uses 'backend_type' variable which should be 'backend'")

    return len(issues) == 0, issues


def main():
    """Run verification checks."""
    streamer_dir = Path(__file__).parent.parent
    results = []

    # Check multi_channel_runner.py
    multi_channel_file = streamer_dir / "multi_channel_runner.py"
    if multi_channel_file.exists():
        success, issues = check_logging_patterns(multi_channel_file, 'backend')
        results.append(("multi_channel_runner.py", success, issues))
    else:
        results.append(("multi_channel_runner.py", False, ["File not found"]))

    # Check main.py
    main_file = streamer_dir / "main.py"
    if main_file.exists():
        success, issues = check_logging_patterns(main_file, 'backend_name')
        results.append(("main.py", success, issues))
    else:
        results.append(("main.py", False, ["File not found"]))

    # Print results
    print("=" * 70)
    print("Logging Patterns Verification Report")
    print("=" * 70)

    all_passed = True
    for filename, success, issues in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"\n{status} - {filename}")

        if issues:
            all_passed = False
            for issue in issues:
                print(f"  • {issue}")

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All checks passed!")
        return 0
    else:
        print("✗ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
